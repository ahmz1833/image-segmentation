# Malware Classification Based on Image Segmentation

Reproducible PyTorch implementation of Wanhu Nie's 2024 paper, **[Malware Classification Based on Image Segmentation](paper/paper.pdf)** ([arXiv:2406.03831](https://arxiv.org/abs/2406.03831)). The project converts raw executable binary streams into grayscale images, separates binary sections into multi-channel image tensors, fine-tunes VGG16 and ResNet50, and produces Kaggle-compatible probability predictions.

The framework supports both **Windows PE binaries** (Microsoft Malware Classification Challenge / BIG 2015) and **Embedded ELF binaries** (Zephyr RTOS ARM embedded malware). Dataset-dependent metadata (classes, sections, channels, architectures) is cleanly decoupled into JSON configuration files.

> **Scope.** This is a static-analysis pipeline: it parses binary sections without execution. Datasets are untrusted research material; keep them outside the repository and handle them in an isolated environment.

---

## Method at a glance

Malware bytes are interpreted as grayscale pixel intensities. Malware from the same family often retains recognizable textures and section-level patterns, even when its overall layout shifts. Binary sections are mapped into image channels.

| Scheme | Representation | Intended Information |
|---|---|---|
| **S1** | Original bytes; width selected from Nataraj et al.'s file-size table | Conventional adaptive-width baseline |
| **S2** | Original bytes; width is approximately the square root of file size | Variable-width baseline |
| **S3** | Original bytes at a fixed width of 1,024 | Fixed-width texture and layout |
| **S4 (Split)** | Each selected binary section is compacted into a separate channel | Section texture without whole-file spatial layout |
| **S5 (Mask)** | One full-size channel per section; non-section pixels are zeroed | Spatial layout preserved at the cost of sparse channels |

S1–S3 are replicated across three channels for standard backbone compatibility. S4 and S5 section combinations become multi-channel inputs.
- **VGG16**: Restricted to 3-channel configurations.
- **ResNet50**: Supports 3-, 4-, and 5-channel configurations.
- All channels are standardized to **224 × 224** prior to ImageNet normalization.

![S1-S5 representations for one Ramnit sample](docs/assets/segmentation-schemes.png)

---

## Supported Datasets & Configuration System

Dataset metadata is decoupled into configuration files under `src/malware_segmentation/configs/`:

### 1. Microsoft BIG 2015 (`src/malware_segmentation/configs/big2015.json`)
- **Format**: Windows PE (`.bytes` and `.asm`)
- **Classes (9)**: Ramnit, Lollipop, Kelihos_ver3, Vundo, Simda, Tracur, Kelihos_ver1, Obfuscator.ACY, Gatak (10,868 train / 10,873 test)
- **Sections**: `.text`, `.rdata`, `.data`, `.rsrc`

### 2. ARM Zephyr RTOS Embedded Malware (`src/malware_segmentation/configs/arm_zephyr.json`)
- **Format**: Linux ELF (`firmware.elf`)
- **Classes (5)**: `backdoor_like`, `byovd_like`, `geofencing_like`, `logic_bomb_like`, `rootkit_like` (25,970 malware samples across 5 families, excluding `benign`)
- **Sections**: `text` (code), `rodata` (constants), `data` (initialized data, aliased from `datas`), `rom_start` (ARM Cortex-M vector table), `initlevel`, `device_area`, `sw_isr_table`, `device_api_area`, `device_states`

### 3. ARM Zephyr Optimized (`src/malware_segmentation/configs/arm_zephyr_optimized.json`) - *Recommended / Production*
- **Format**: Linux ELF (`firmware.elf`)
- **Classes (6)**: `benign`, `backdoor_like`, `byovd_like`, `geofencing_like`, `logic_bomb_like`, `rootkit_like` (27,571 samples)
- **Inverse-Frequency Balanced Sampling**: `"weighted_sampling": true` via PyTorch `WeightedRandomSampler`
- **Cosine Annealing LR**: `"scheduler_type": "cosine"` (`CosineAnnealingLR(T_max=epochs, eta_min=1e-5)`)
- **Label Smoothing Regularization**: `"label_smoothing": 0.05` to prevent overconfidence
- **Training Epochs**: `"epochs": 30`
- **rodata-Centric Multi-Scale Channels**: Combines global macro structure (`S3_1024`), narrow layout (`S1`), and payload-rich firmware sections (`.rodata`, `.data`, `.initlevel`, `device_area`).
- **Benchmark Performance**: **79.87% 6-Class Accuracy** / **91.32% Merged Driver Accuracy** (ResNet50 S3), measured over the full dataset. On the held-out 20% split alone the same run scores **65.26%** accuracy, **0.6084** macro-F1 and **78.44%** merged accuracy. See the evaluation-protocol note below.

### 4. ARM Zephyr Optimized with PPM (`src/malware_segmentation/configs/arm_zephyr_optimized_ppm.json`) - *Ablation Study*
- Everything in `arm_zephyr_optimized` PLUS:
- **Pyramid Pooling Module (PPM)**: `"use_ppm": true` (Multi-scale spatial pooling across $1\times 1, 2\times 2, 3\times 3, 6\times 6$ bins)
- **On-The-Fly Texture Filter Permutations**: Includes `S3_raw_lbp_gabor` (Raw + LBP + Gabor), `S5_imgs1024_rodata_lbp`, `S5_imgs1024_rodata_gabor`, and 4-channel hybrid `S5_imgs1024_rodata_lbp_gabor_4_channels` computed in memory with **zero dataset changes**.
- *Note: this configuration is kept for the ablation record only. The PPM head as implemented here collapses accuracy to 14-25% and also fails to fit the training set, so it is an optimization/implementation failure rather than evidence against pyramid pooling itself. Use `arm_zephyr_optimized` for production.*

To inspect supported channel configurations for any dataset:
```bash
# BIG 2015 (default)
malware-seg configs vgg16
malware-seg configs resnet50

# ARM Zephyr ELF (Optimized Production)
malware-seg configs vgg16 --dataset arm_zephyr_optimized
malware-seg configs resnet50 --dataset arm_zephyr_optimized
```

---

## Installation

Requirements:
- Linux or macOS with Python 3.10+
- 7-Zip (`p7zip-full` on Ubuntu) for BIG 2015 `.7z` archives
- `zstd` and `tar` for ARM ELF archives
- NVIDIA GPU recommended for training

```bash
git clone https://github.com/ahmz1833/image-segmentation.git
cd image-segmentation

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

malware-seg --version
malware-seg --help
```

---

## Workflow: ARM Zephyr ELF Dataset

### 1. Extract ARM Samples from Archive
The raw dataset archive (`final.tar.zst`) contains multiple architectures. Extract only the ARM samples using the provided streaming extractor:

```bash
chmod +x scripts/extract_arm.sh
./scripts/extract_arm.sh /path/to/final.tar.zst ./data/arm-only
```
This directly extracts all 27,571 ARM binaries across the 6 classes without unpacking the rest of the archive.

### 2. Preprocess into NPZ Arrays
Convert the extracted ELF binaries into S1–S5 image arrays. Using `--resize 224` shrinks the dataset from 127 GB raw binaries down to **~5.0 GB** (~185 KB per sample):

```bash
malware-seg preprocess \
  --data-dir ./data/arm-only \
  --dataset arm_zephyr \
  --resize 224 \
  --workers 12
```

### 3. Visualize Processed Samples
Render visual inspections of the generated channels for each class:

```bash
malware-seg visualize \
  --data-dir ./data/arm-only \
  --samples-per-class 5
```
Output images are saved to `./data/arm-only/artifacts/visualizations/`.

---

## Running on Kaggle (4 Concurrent Instances)

To train models in parallel across 4 Kaggle GPU accounts or notebooks:

1. Package the preprocessed `.npz` files:
   ```bash
   zip -0 -r arm_malware_npz.zip ./data/arm-only/Processed_Dataset
   ```
2. Create a private dataset on Kaggle (e.g. `arm-malware-npz`) and upload `arm_malware_npz.zip`. Share it with your accounts.
3. Build the self-contained notebook from the template (which packages the latest codebase into base64):
   ```bash
   python scripts/build_kaggle_notebook.py
   ```
   *(Note: `kaggle_train.ipynb` is gitignored to keep the repository clean. The template is maintained in `kaggle_train.template.ipynb`.)*
4. In Kaggle, import the generated `kaggle_train.ipynb` notebook, attach the dataset via **+ Add Input**, enable **GPU Accelerator (T4 x2 or P100)** and **Internet: On**.

Each instance executes an assigned experiment preset:

| Instance | Goal | CLI Command |
|---|---|---|
| **Instance 1** | **Baselines (Raw Byte Layouts)**<br>• VGG16 & ResNet50<br>• Configs: `S1`, `S2`, `S3` | `malware-seg kaggle -i 1 --dataset arm_zephyr -e 20 -b 32` |
| **Instance 2** | **3-Channel Section Separations (VGG16)**<br>• VGG16 only<br>• `S4_text_rodata_data`, `S5_text_rodata_data`, `S5_imgs1024_text_data`, `S5_imgs1024_text_rodata` | `malware-seg kaggle -i 2 --dataset arm_zephyr -e 20 -b 32` |
| **Instance 3** | **3-Channel Section Separations (ResNet50)**<br>• ResNet50 only<br>• `S4_text_rodata_data`, `S5_text_rodata_data`, `S5_imgs1024_text_data`, `S5_imgs1024_text_rodata` | `malware-seg kaggle -i 3 --dataset arm_zephyr -e 20 -b 32` |
| **Instance 4** | **Multi-Channel (4 & 5 Channels - ResNet50)**<br>• ResNet50 only<br>• `S4 4-ch (raw)`, `S4 4-ch (rom_start)`, `S5 4-ch`, `S5 5-ch` | `malware-seg kaggle -i 4 --dataset arm_zephyr -e 20 -b 32` |

### Dataset & Optimization Options:
- **`--dataset arm_zephyr_optimized`** (*Recommended / Production*): 6 classes (including `benign`, 27,571 samples), standard global average pooling, weighted sampling, cosine annealing LR scheduling, label smoothing (0.05), and supports all rodata and multi-scale channels.
- **`--dataset arm_zephyr_optimized_ppm`** (*Ablation Study*): 6 classes with Pyramid Pooling Module (**PPM**) enabled after the CNN backbone, and support for on-the-fly texture permutations (`S3_raw_lbp_gabor`, `S5_imgs1024_rodata_lbp`, etc.).
- **`--dataset arm_zephyr_weighted`**: 6 classes (including `benign`) with inverse-frequency weighted random sampling.
- **`--dataset arm_zephyr`**: 5 pure malware families (`backdoor_like`, `byovd_like`, `geofencing_like`, `logic_bomb_like`, `rootkit_like`). `benign` samples are filtered out on load without modifying files.
- **`--ppm` / `--no-ppm`**: CLI flag to force enable or disable Pyramid Pooling Module (PPM) after the CNN backbone.
- **`--weighted-sampling` / `--no-weighted-sampling`**: CLI flag to force enable or disable weighted random sampling independently of the dataset config default.
- **`--label-smoothing <float>`**: Override label smoothing epsilon for CrossEntropyLoss (e.g. `0.05`, default `0.0` or config default).
- **`--scheduler {cosine,exponential,none}`**: Override learning rate scheduler (`cosine`, `exponential`, `none`).

Alternatively, you can run directly via the shorthand runner script:
```bash
# Run production-optimized training on Kaggle Instance 1:
python kaggle_runner.py -i 1 --dataset arm_zephyr_optimized

# Or run the PPM ablation study on Instance 1:
python kaggle_runner.py -i 1 --dataset arm_zephyr_optimized_ppm
```

---

## Workflow: BIG 2015 PE Dataset (Paper Reproduction)

### Download and Preprocess
```bash
DATA_DIR=~/.cache/kaggle/BIG2015/main
malware-seg download --data-dir "$DATA_DIR"
malware-seg preprocess train --data-dir "$DATA_DIR"
malware-seg preprocess test  --data-dir "$DATA_DIR"
malware-seg visualize --data-dir "$DATA_DIR" --samples-per-class 10
```

### Reproduce Full Paper Experiments
```bash
malware-seg run-all \
  --data-dir "$DATA_DIR" \
  --device cuda
```

Paper training hyper-parameters (Table 4 of Nie et al.):
| Model | Epochs | Effective Batch | Initial LR | Scheduler | Weight Decay | Momentum |
|---|---:|---:|---:|---|---:|---:|
| VGG16 | 20 | 8 | 0.001 | None | 0.0005 | 0.9 |
| ResNet50 | 15 | 64 | 0.01 | Exponential decay ($\gamma=0.9$) | 0.006 | 0.9 |

## ARM Zephyr Embedded Benchmark Results & Visualizations

We conducted an extensive empirical study on **27,571 ARM Zephyr RTOS ELF firmware binaries** across 6 classes (`benign` + 5 malware families: `backdoor_like`, `byovd_like`, `geofencing_like`, `logic_bomb_like`, `rootkit_like`) evaluating 58 models across four iterative phases:

### 1. Top Performing Configurations (Phase 3 Optimized)

| Model | Representation / Channels | 6-Class Acc | Macro-F1 | MCC | Merged Acc (Benign+BYOVD Driver Baseline) | Latency | FPS |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **ResNet50** | **S3 (Raw 1024-width)** | **79.87%** | **0.7509** | **0.7691** | **91.32%** | 1.86 ms | 537.6 |
| **ResNet50** | **S5 (`imgs-1024` + `.rodata` + `.data`)** | **78.70%** | **0.7386** | **0.7558** | **90.36%** | 1.72 ms | 581.4 |
| **ResNet50** | **S5 4-Channel (`imgs-1024` + `.rodata` + `.data` + `.initlevel`)** | **78.43%** | **0.7388** | **0.7500** | **89.57%** | 1.86 ms | 537.6 |
| **ResNet50** | **S5 4-Channel (`imgs-1024` + `.text` + `.rodata` + `.data`)** | **77.88%** | **0.7346** | **0.7388** | **88.51%** | 1.97 ms | 507.6 |
| **ResNet50** | **S5 5-Channel (`imgs-1024` + `.text` + `.rodata` + `.data` + `.rom_start`)** | **77.22%** | **0.7273** | **0.7321** | **88.17%** | 2.39 ms | 418.4 |
| **VGG16** | **S5 (`imgs-1024` + `.rodata` + `.data`)** | **75.30%** | **0.7141** | **0.7068** | **85.42%** | 3.15 ms | 317.5 |

### 2. Best Model Diagnostics (ResNet50 S3: 79.87% / 91.32%)

| Training & Validation Loss/Accuracy Curves | Normalized & Raw Confusion Matrix |
|:---:|:---:|
| ![ResNet50 S3 Training Curves](docs/assets/arm-resnet50-s3-curves.png) | ![ResNet50 S3 Confusion Matrix](docs/assets/arm-resnet50-s3-confusion.png) |

![ResNet50 S3 Per-Class Performance Breakdown](docs/assets/arm-resnet50-s3-metrics.png)

### 3. Key Research Insights
- **The BYOVD Phenomenon**: Bring Your Own Vulnerable Driver (`byovd_like`) samples are physically legitimate peripheral drivers with subtle CVEs. In static analysis, their ELF layouts mirror `benign` firmware (66.8% cross-prediction, but <1% misclassification to other families). Grouping them into a vulnerable/benign driver baseline yields **91.32% Accuracy** and **0.9127 Macro-F1**.
- **The Discriminative Power of `.rodata`**: In embedded RTOS binaries, `.text` code is 80%+ shared kernel logic, whereas strings and constants in `.rodata` contain critical malware indicators. Section configurations pairing global layout (`imgs-1024`) with `.rodata` and initialized `.data` achieved **78.70% accuracy**.
- **Pyramid Pooling Module (PPM) Ablation**: Adding the PPM head collapsed accuracy to 14-25% across every configuration. Training accuracy also stalls below 25%, so this is a failure to fit rather than a failure to generalize. Two implementation causes are visible in `models.py`: each pyramid branch ends in another `AdaptiveAvgPool2d(1)`, which averages away the very multi-scale spatial information a PPM is meant to preserve (PSPNet instead upsamples and concatenates spatially); and the head adds ~4.19M randomly initialized convolution parameters trained at lr=0.01 with weight decay 6e-3 on top of a pretrained backbone. Global Average Pooling remains the right default here.

### 4. Technical Reports & Detailed Benchmarks
- **[Optimized 6-Class Benchmark](docs/results_arm_zephyr_optimized.md)**: Full 21-model metrics table, confusion matrices, and per-class reports.
- **[Phase 2 Pure Malware Benchmark (5 Classes)](docs/results_arm_zephyr.md)**: 18-model benchmark excluding benign binaries.
- **[BIG 2015 PE Benchmark](docs/results.md)**: Microsoft BIG 2015 paper reproduction results.

---

## BIG 2015 Results & Benchmark Comparison

The best paper result is ResNet50/S3 with 0.0265 log loss. In the paper-epoch reproduction, the best Public score is 0.02341 and the best Private score is 0.03185, both from mixed S5 ResNet50 configurations.

See **[full results, comparisons, and training diagnostics](docs/results.md)**.

---

## Output Layout

All runtime outputs are organized under the selected `--data-dir`:

```text
DATA_DIR/
├── processed/
│   ├── train/<class>/<sample>.npz
│   ├── train/manifest.json
│   ├── test/<sample>.npz
│   └── test/manifest.json
└── artifacts/
    ├── visualizations/class_<name>/<sample>.png
    ├── models/<model>/
    │   ├── model_comparison.{csv,png}
    │   └── <configuration>/
    │       ├── model.pt, metrics.json, history.csv
    │       ├── classification_report.csv, training_predictions.csv
    │       └── training_curves.png, confusion_matrices.png, per_class_metrics.png
    └── submissions/<model>/
        ├── prediction_comparison.{csv,png}
        └── <configuration>/
            ├── submission.csv, predictions.csv, summary.json
            └── class_distribution.png, prediction_uncertainty.png, probability_profiles.png
```

---

## Citation

```bibtex
@article{nie2024malware,
  title={Malware Classification Based on Image Segmentation},
  author={Nie, Wanhu},
  journal={arXiv preprint arXiv:2406.03831},
  year={2024}
}
```
