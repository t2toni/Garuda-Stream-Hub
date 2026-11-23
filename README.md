# Garuda Stream Hub 🎮⚡

<p align="center">
  <img src="assets/screenshots/dashboard_ui.jpg" alt="Garuda Stream Hub UI Dashboard" width="900" style="border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);">
</p>

<p align="center">
  <a href="https://github.com/aswin18antony-code/Garuda-Stream-Hub/actions"><img src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-brightgreen?style=for-the-badge&logo=githubactions" alt="CI"></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-blue?style=for-the-badge&logo=linux&logoColor=white" alt="Platform"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/C%2B%2B-17%20Native%20Engine-orange?style=for-the-badge&logo=cplusplus" alt="C++"></a>
  <a href="#"><img src="https://img.shields.io/badge/UI-PyQt6%20Tokyo%20Night-purple?style=for-the-badge&logo=qt" alt="PyQt6"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"></a>
</p>

---

## 📌 Overview

**Garuda Stream Hub** is a studio-grade, one-tap ultra-low latency mobile streaming and recording utility engineered for competitive gaming capture on **Garuda / Arch Linux** and **Windows**.

It seamlessly unites high-performance native **C++ subroutines (pybind11)**, an asynchronous multi-threaded **PyQt6 GUI**, **PipeWire / PulseAudio** digital audio isolation ("The Mic Bug Fixer"), **Qualcomm Snapdragon hardware H.265 (HEVC)** video mirroring, neural **AI noise suppression (RNNoise)**, and automated **OBS Studio scene injection** into a single master execution button.

---

## 🏆 Why Garuda Stream Hub is the Best Solution

Traditional mobile game streaming setups are notoriously frustrating, expensive, or plagued by audio glitches and static. Here is how **Garuda Stream Hub** outperforms all traditional approaches:

| Feature / Solution | ❌ Hardware Capture Cards (Elgato / AverMedia) | ❌ Generic Mirroring Tools (Vysor / Basic scrcpy) | ❌ 3.5mm Aux Splitter / Mixers | ⚡ Garuda Stream Hub (Our App) |
| :--- | :--- | :--- | :--- | :--- |
| **Hardware Cost** | \$150 – \$250+ | Free – \$40/yr subscription | \$25 – \$60 in cables/ground isolators | **$0 (100% Free & Open Source)** |
| **Cable Clutter** | Bulky HDMI splitters, power adapters, capture boxes | USB only (often video-only without clean audio) | 3 to 4 auxiliary cables, ground loop buzz | **Single USB Cable or 100% Wireless (Wi-Fi 6)** |
| **The "In-Game Mic Bug"** | Teammates cannot hear you, or game sound is cut | In-game teammate voice chat cannot be isolated | Audio ground loop static, preamp hiss | **Fixed digitally: Teammates + Game sound isolated** |
| **Desktop Audio Bleed** | Discord/Spotify bleeds into stream | Desktop sounds leak into recording | Leaks all system audio | **Zero Bleed: Discord & Spotify kept private** |
| **Studio Multi-Track MP4** | Requires complex external software routing | No multi-track output | No multi-track separation | **Built-in 3-track sync: Master + Game + Mic** |
| **AI Noise Denoising** | None (requires external GoXLR / Elgato Wave) | None | Terrible background fan/breathing noise | **Built-in RNNoise neural network & air filters** |
| **System Overhead** | High CPU decoding load | High jitter / frame drops | Analog audio degradation | **Native C++17 sub-process acceleration** |

### Key Advantages:
1. **Solves the Infamous "In-Game Mic Bug"**: On mobile competitive games, turning on the in-game microphone cuts screen audio or mutes teammates for the stream. Garuda Stream Hub routes audio digitally over USB/Wi-Fi via an isolated PipeWire virtual sink, keeping teammate voice chat alive and crystal-clear.
2. **Zero Desktop Audio Leakage**: Listen to Discord calls, Spotify playlists, or YouTube guides on your PC without any of that audio leaking into your stream or gameplay recording.
3. **Pure Digital Audio Quality**: No analog ground-loop hum, static buzzing, or audio crackle. Transmits pristine 48 kHz digital PCM audio.
4. **Studio Multi-Track Recording Out-of-the-Box**: Creates production-ready MP4 files with independent audio tracks so you can edit your voice separately from in-game sound in Premiere Pro or DaVinci Resolve.

---

## ⚙️ Technical Specifications

### 📺 Video Streaming Engine
- **Supported Video Codecs**: H.265 (HEVC), H.264 (AVC), AV1
- **Hardware Encoder Acceleration**: Qualcomm Snapdragon `c2.qti.hevc.encoder`, MediaTek, and Samsung Exynos hardware acceleration
- **Bitrate Range**: 4 Mbps to 32 Mbps (Default: 16 Mbps ultra-crisp profile)
- **Target Framerates**: 60 FPS / 120 FPS high-refresh rate synchronization
- **Transmission Latency**: Sub-15ms video buffer with dynamic adaptive jitter control
- **Display Output**: Borderless accelerated window + optional V4L2 virtual camera (`/dev/video10`)

### 🔊 Audio Pipeline & Multiplexing
- **Audio Codec**: Uncompressed 48 kHz 16-bit raw PCM (zero robotic compression artifacts) / Opus 48 kHz
- **Audio Buffer**: 50ms anti-glitch jitter buffer (eliminates buffer under-runs and stuttering)
- **Virtual Audio Infrastructure**: Dedicated PipeWire `BGMI_Audio_Sink` virtual cable
- **Headphone Loopback**: ~15ms real-time hardware sync to physical headphones/speakers
- **AI Neural Voice Denoising**: RNNoise deep learning recurrent neural network (`librnnoise_ladspa.so`)
- **Acoustic Filter Complex**:
  - High-pass filter at 125 Hz (cuts heavy breath pops and laptop fan turbulence)
  - Low-pass filter at 11,500 Hz (cuts high-frequency electrical hiss and coil whistle)
  - Musical downward noise gate with -91 dB floor suppression

### 🎬 Studio Multi-Track Recording Engine
- **Container Format**: MP4 with `+faststart` MOOV atom optimization for instant video editing
- **Video Encoder**: x264 CRF 21, `veryfast` preset, YUV420p color space
- **Audio Encoder**: AAC 192 kbps per stream
- **Synchronized Audio Tracks**:
  - **Track 1 (Default Master Mix)**: Game Audio + Teammate Voice Call + Player Mic balanced in stereo
  - **Track 2 (Game & Friends Audio)**: Clean isolated game sound and teammate voice chat
  - **Track 3 (My Microphone)**: AI-denoised, isolated microphone track for professional post-production

### ⚡ Native C++ Telemetry Sentinel (`stream_native`)
- **Language Standard**: C++17 integrated via pybind11
- **Latency Monitoring**: Non-blocking asynchronous socket ping sentinel (sub-millisecond accuracy)
- **Jitter Estimation**: Real-time RFC 3550 variance calculations with sliding-window telemetry
- **System Profiling**: Direct Linux `/proc` filesystem reader for zero-overhead CPU and memory tracking
- **Cross-Platform Fallback**: Pure Python socket and telemetry fallback for environments without a C++ compiler

### 💻 Supported Operating Systems
- **Linux**: Garuda Linux, Arch Linux, Ubuntu 20.04+, Debian 11+, Fedora 36+ (Kernel 5.15+)
- **Windows**: Windows 10 (64-bit) / Windows 11 (64-bit)

---

## 📖 Step-by-Step User Guide (How to Use)

### Step 1: Prepare Your Device
1. On your phone, enable **Developer Options**:
   - Go to **Settings > About Phone** and tap **Build Number** 7 times.
2. In **Developer Options**, turn on:
   - **USB Debugging**: Enabled
   - **USB Debugging (Security settings)**: Enabled (if prompted)

### Step 2: Connect Your Device
- **Wired Connection (Recommended for Lowest Latency)**:
  - Plug your phone into your PC via a USB 3.0/3.2 cable.
- **Wireless Connection (Wi-Fi 6 / 5 GHz)**:
  - Connect your phone and PC to the same 5 GHz Wi-Fi network. The app automatically promotes connected USB devices to TCP:5555 Wi-Fi mode.

### Step 3: Launch Garuda Stream Hub
- **On Linux**:
  ```bash
  ./run.sh
  ```
  *(Or execute the standalone binary: `./dist/garuda-stream-hub`)*
- **On Windows**:
  - Double-click `garuda-stream-hub.exe` or run `python src/main.py`.

### Step 4: 1-Tap Pipeline Initialization
1. Click the glowing neon **`[ INITIALIZE STREAM PIPELINE ]`** master button.
2. The orchestrator will automatically execute all 5 pipeline phases in seconds:
   - `Step 1`: Validates dependencies (`adb`, `scrcpy`, `pipewire`/`wasapi`, `ffmpeg`).
   - `Step 2`: Discovers and pairs with your device, injecting speed optimizations.
   - `Step 3`: Creates the isolated virtual audio sink and routes game sound to your headphones.
   - `Step 4`: Launches Qualcomm Snapdragon H.265 hardware video casting with sub-15ms buffer.
   - `Step 5`: Elevates system priority to prevent frame drops during intense gaming moments.

### Step 5: (Optional) 1-Click Studio Recording
- Click **`[ 🔴 START RECORDING ]`** in the bottom recording bar.
- The real-time HUD displays recording duration, file size, and framerate.
- Click **`[ ⏹ STOP RECORDING ]`** when done. Your multi-track MP4 video is instantly saved to `~/Videos/Recordings/` ready for YouTube or video editing.

### Step 6: Hook into OBS Studio
- **Video**: In OBS, add a **Window Capture** source and select `Garuda Stream Mirror`.
- **Game Audio**: Add an **Audio Output Capture** (PulseAudio/PipeWire) source and select `BGMI_Audio_Sink.monitor`.
- **Microphone**: Add an **Audio Input Capture** source and select your physical microphone.

---

## 📦 Releases & Downloads

Pre-built binaries and portable bundles are available on GitHub Releases:

| OS | Package | Format | Notes |
| :--- | :--- | :--- | :--- |
| **Linux (Arch / Garuda / Ubuntu)** | `garuda-stream-hub-linux-x86_64.tar.gz` | Standalone Binary | Ready to run, includes native engines & models |
| **Linux (Binary Executable)** | `garuda-stream-hub` | Direct Executable | Portable single-file binary |
| **Windows 10 / 11 (x64)** | `GarudaStreamHub-windows-x64.zip` | Standalone Bundle | Includes one-click builder & launch scripts |

👉 **[Download the Latest Release on GitHub](https://github.com/aswin18antony-code/Garuda-Stream-Hub/releases)**

---

## 🛠️ Developer Setup & Build Instructions

### Linux (Garuda / Arch / Ubuntu)

```bash
# Clone repository
git clone https://github.com/aswin18antony-code/Garuda-Stream-Hub.git
cd Garuda-Stream-Hub

# Build native C++ pybind11 module
make

# Run the PyQt6 Desktop GUI
./run.sh

# Or run in headless CLI mode
./run.sh --cli
```

### Windows (PowerShell / Command Prompt)

```cmd
git clone https://github.com/aswin18antony-code/Garuda-Stream-Hub.git
cd Garuda-Stream-Hub

pip install -r requirements.txt
python src/main.py
```

### Run Test Suite

```bash
make test
```

---

## 🏗️ Project Architecture

```
Garuda-Stream-Hub/
├── assets/                  # Hero screenshots, graphics, and badges
│   └── screenshots/         # Dashboard UI captures
├── src/
│   ├── main.py              # Application entrypoint (CLI & GUI dispatcher)
│   ├── android/             # Device discovery, auto-pairing, telemetry
│   ├── audio/               # PipeWire virtual sink, RNNoise DSP, voice isolation
│   ├── core/                # Pipeline orchestrator, configuration, system optimizer
│   ├── native/              # C++17 pybind11 low-overhead telemetry module
│   ├── obs/                 # Automated OBS Studio scene collection injector
│   ├── recorder/            # FFmpeg multi-track studio recording engine
│   ├── ui/                  # PyQt6 Tokyo Night / Dracula Neon responsive GUI
│   └── video/               # scrcpy controller & adaptive jitter buffer
├── tests/                   # Automated unit test suite
├── scripts/                 # Build and packaging automation (Linux & Windows)
├── .github/workflows/       # GitHub Actions CI/CD release pipeline
├── Makefile                 # C++ build & test recipes
└── pyproject.toml           # PEP 517/621 packaging metadata
```

---

## 👨‍💻 Developer & Portfolio Highlights

This project demonstrates production-grade software engineering competencies:
- **Systems & Native Programming**: C++17 pybind11 integration, Linux `/proc` IPC, low-overhead socket pings.
- **Digital Signal Processing (DSP)**: PipeWire module-null-sink, LADSPA neural noise filter-chains, FFmpeg multi-track multiplexing.
- **Concurrent GUI Architecture**: Thread-safe PyQt6 signal bridges, non-blocking asynchronous orchestrators.
- **DevOps & CI/CD**: Multi-platform matrix builds on GitHub Actions (Ubuntu + Windows), automated binary packaging with PyInstaller.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
