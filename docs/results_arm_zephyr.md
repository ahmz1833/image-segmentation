# ARM Zephyr Embedded Malware Benchmark Results

Comprehensive experimental results on the ARM Zephyr ELF embedded malware dataset across **18 distinct configurations** spanning **VGG16** and **ResNet50** architectures, evaluated with a stratified 80% train / 20% validation split over 20 epochs.

---

## 1. Complete Configuration Benchmark

| Model | Configuration | Preset | Train Acc | Val Acc | Macro-F1 | MCC | Latency (ms) | Epoch Time |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **ResNet50** | **S3 (Raw 1024-width)** | Instance 1 | 77.4% | **68.1%** | **0.6875** | **0.6043** | 1.86 ms | 91.7s |
| **ResNet50** | **S5 (`imgs-1024` + `.rodata` + `.data`)** | Instance 3 | 75.2% | **68.0%** | **0.6881** | **0.6029** | 1.81 ms | 90.8s |
| **ResNet50** | **S5 4-Channel (`imgs-1024` + `.text` + `.rodata` + `.data`)** | Instance 4 | 71.1% | **60.0%** | **0.6075** | **0.5021** | 1.87 ms | 92.9s |
| **ResNet50** | **S5 5-Channel (`imgs-1024` + `.text` + `.rodata` + `.data` + `.rom_start`)** | Instance 4 | 69.3% | **58.5%** | **0.5893** | **0.4823** | 2.26 ms | 97.2s |
| **ResNet50** | S5 (`imgs-1024` + `.text` + `.data`) | Instance 3 | 62.0% | 53.4% | 0.5341 | 0.4225 | 1.78 ms | 90.3s |
| **ResNet50** | S4 4-Channel (`.text` + `.rodata` + `.data` + Raw) | Instance 4 | 55.9% | 52.3% | 0.5214 | 0.4054 | 1.93 ms | 92.4s |
| **ResNet50** | S5 (`imgs-1024` + `.text` + `.rodata`) | Instance 3 | 59.3% | 51.7% | 0.5121 | 0.3953 | 1.86 ms | 90.7s |
| **ResNet50** | S1 (Raw fixed-width) | Instance 1 | 50.6% | 39.9% | 0.3623 | 0.2517 | 1.81 ms | 91.6s |
| **VGG16** | S3 (Raw 1024-width) | Instance 1 | 50.8% | 35.7% | 0.3324 | 0.1925 | 2.89 ms | 169.5s |
| **VGG16** | S5 (`imgs-1024` + `.text` + `.data`) | Instance 2 | 48.5% | 35.5% | 0.3240 | 0.1949 | 2.81 ms | 164.7s |
| **VGG16** | S5 (`imgs-1024` + `.text` + `.rodata`) | Instance 2 | 50.4% | 34.0% | 0.3265 | 0.1804 | 2.80 ms | 164.9s |
| **VGG16** | S1 (Raw fixed-width) | Instance 1 | 49.9% | 33.5% | 0.3297 | 0.1638 | 2.87 ms | 168.5s |
| **VGG16** | S2 (Raw fixed-aspect 1:1) | Instance 1 | 43.1% | 32.6% | 0.3022 | 0.1580 | 2.90 ms | 168.6s |
| **VGG16** | S4 (`.text` + `.rodata` + `.data`) | Instance 2 | 50.4% | 32.0% | 0.2965 | 0.1470 | 2.78 ms | 164.1s |
| **VGG16** | S5 (`.text` + `.rodata` + `.data`) | Instance 2 | 39.5% | 30.1% | 0.2882 | 0.1331 | 2.80 ms | 164.2s |
| **ResNet50** | S2 (Raw fixed-aspect 1:1) | Instance 1 | 34.9% | 27.8% | 0.2112 | 0.0938 | 1.81 ms | 92.0s |
| **ResNet50** | S5 (`.text` + `.rodata` + `.data`) | Instance 3 | 34.1% | 27.2% | 0.2080 | 0.0790 | 1.73 ms | 89.6s |
| **ResNet50** | S4 (`.text` + `.rodata` + `.data`) | Instance 3 | 34.7% | 26.4% | 0.2315 | 0.0716 | 1.76 ms | 90.1s |
| **ResNet50** | S4 4-Channel (`.text` + `.rodata` + `.data` + `.rom_start`) | Instance 4 | 27.6% | 23.3% | 0.1848 | 0.0303 | 2.08 ms | 92.9s |

---

## 2. Key Findings & Insights

### A. Architectural Superiority: ResNet50 vs VGG16
- **Accuracy**: ResNet50 achieves **68.1% validation accuracy / 76.1% full dataset accuracy** with **0.688 F1 and 0.604 MCC**, outperforming VGG16 (which maxed out at **35.7% validation accuracy**).
- **Inference Speed**: ResNet50 executes in **1.81 ms per sample** (~550 FPS), compared to VGG16's **2.89 ms per sample** (~345 FPS).
- **Training Time**: ResNet50 trains in **~91 seconds per epoch** (~30 minutes for 20 epochs), while VGG16 requires **~168 seconds per epoch** (~56 minutes for 20 epochs) due to its 138M parameter footprint and large fully-connected classifier layers.

### B. The Critical Role of Global Layout Context (`imgs-1024`)
- **Sections Alone Are Insufficient**: Configurations consisting solely of isolated ELF section images (`S4_text_rodata_data` and `S5_text_rodata_data`) plateaued around **26% to 32% accuracy**. In embedded ARM firmware, isolated `.text` and `.data` segments often share similar code generation templates, making isolated section textures ambiguous.
- **Global Context Unlocks Discrimination**: When the global 1024-width raw binary layout (`S3_1024`) is paired with sections:
  - `S5_imgs1024_rodata_data` reaches **68.0% val accuracy** and **0.6881 F1**.
  - `S5 4-Channel` reaches **60.0% val accuracy** and **0.5021 MCC**.
  - The combination of macro-structural byte layout + micro-structural section alignment gives the deep residual network both global firmware footprint and localized section features.

### C. Balanced Malware Family Attribution
- In the 5-class malware family configuration, class collapse is completely eliminated:
  - **`geofencing_like`**: **94.5% Precision**, **71.7% Recall**, **81.5% F1-score** on ResNet50 S3.
  - **`byovd_like`**: **86.5% Precision**, **73.0% Recall**, **79.2% F1-score**.
  - **`logic_bomb_like`**: **77.7% Precision**, **78.2% Recall**, **78.0% F1-score**.
  - **`rootkit_like`**: **74.3% Precision**, **73.4% Recall**, **73.8% F1-score**.
  - **`backdoor_like`**: **62.6% Precision**, **83.3% Recall**, **71.5% F1-score**.
  - **Overall Accuracy**: **76.12%**, **Macro F1**: **76.80%**, **Support**: 25,970 samples.
