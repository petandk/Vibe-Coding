# 🚀 Flipper Zero Key Spammer

A high-performance USB HID key spammer application for the Flipper Zero that allows you to spam any character at configurable speeds.

![Flipper Zero Key Spammer](https://img.shields.io/badge/Flipper%20Zero-Compatible-orange) ![License](https://img.shields.io/badge/License-MIT-blue) ![Status](https://img.shields.io/badge/Status-Working-green)

## 📋 What It Does

The **Key Spammer** transforms your Flipper Zero into a configurable USB keyboard that can rapidly spam any character you choose. Perfect for:

- 🎮 **Gaming** - Rapid fire inputs, auto-clicking, spam actions
- 🔧 **Testing** - Stress testing input fields, automation testing
- 💻 **Productivity** - Repetitive text input, form filling
- 🔬 **Research** - Input analysis, timing studies

## ✨ Features

- **Character Selection**: Navigate through a clean keyboard layout (letters, numbers, punctuation)
- **Three Speed Options**:
  - 🔥 **Fast (20ms)** - 50 characters per second
  - ⚡ **Medium (100ms)** - 10 characters per second
  - 🐌 **Slow (500ms)** - 2 characters per second
- **USB HID Integration**: Works as a real keyboard on any computer
- **Clean Interface**: Intuitive navigation without clutter
- **Precise Timing**: Timer-based spamming for consistent intervals
- **Easy Control**: Start/stop spamming with simple button presses

## 🎯 How It Works

1. **Select Character**: Use directional buttons to navigate the keyboard and press OK to select your character
2. **Choose Speed**: Pick from three frequency options using up/down arrows
3. **Start Spamming**: Press OK to begin continuous character transmission
4. **Stop Anytime**: Press OK or Back to stop spamming and return to character selection

## 🛠️ Development Story

This application was developed through an intensive AI-assisted coding session featuring:

- **Extensive Problem-Solving**: Multiple iterations to get USB HID functionality working
- **User-Driven Refinement**: Continuous improvements based on real testing feedback
- **Performance Optimization**: Fine-tuning delays and timing for optimal spam rates
- **UI Polish**: Multiple design iterations for the cleanest possible interface

**Total Development**: Several hours of coding, debugging, and optimization  
**AI Assistant**: GitHub Copilot (Claude)  
**Icon Design**: Microsoft Copilot  
**Result**: A robust, professional-quality Flipper Zero application

### 🔧 Technical Highlights

- **State Machine Architecture**: Clean separation between character selection, frequency selection, and active spamming
- **Optimized HID Timing**: Reduced delays (10ms key press vs standard 50ms) for maximum spam rate
- **Memory Efficient**: Minimal RAM usage with smart helper functions
- **Timer-Based**: Uses FuriTimer for precise interval control
- **USB Mode Switching**: Proper HID initialization and cleanup

## 📦 Installation

### Quick Install (Recommended)

1. Download the `key_spammer.fap` file from this repository
2. Copy it to your Flipper Zero's SD card: `/ext/apps/USB/`
3. The app will appear in **Apps > USB > Key Spammer**

### Install via qFlipper

1. Connect your Flipper Zero to your computer
2. Open qFlipper
3. Navigate to **SD Card > apps > USB**
4. Drag and drop `key_spammer.fap` into the USB folder
5. Disconnect and find the app in **Apps > USB > Key Spammer**

## 🔨 Building from Source

### Prerequisites

First, install uFBT (unofficial Flipper Build Tool):

```bash
# Install uFBT
pip3 install --upgrade ufbt

# Initialize uFBT (downloads SDK)
ufbt update
```

### Compilation Steps

1. **Clone this repository**:

   ```bash
   git clone https://github.com/yourusername/flipper-key-spammer.git
   cd flipper-key-spammer
   ```

2. **Navigate to source directory**:

   ```bash
   cd src
   ```

3. **Build the application**:

   ```bash
   ufbt
   ```

4. **Install to Flipper Zero** (optional):
   ```bash
   ufbt launch
   ```

The compiled `.fap` file will be in the `dist/` directory.

### Development Setup

For active development:

```bash
# Clean build
ufbt clean

# Build with debug symbols
ufbt DEBUG=1

# Monitor logs while running
ufbt cli
```

## 🎮 Usage Instructions

### Basic Operation

1. **Launch** the app from Apps > USB > Key Spammer
2. **Navigate** using directional buttons (Up/Down/Left/Right)
3. **Select** character with OK button
4. **Choose** spam frequency with Up/Down arrows
5. **Start** spamming with OK button
6. **Stop** spamming with OK or Back button
7. **Exit** app with Back button from character selection

### Keyboard Layout

```
1 2 3 4 5 6 7 8 9 0
q w e r t y u i o p
a s d f g h j k l ;
z x c v b n m , . _
```

_Note: Space is represented as underscore (\_)_

### Speed Reference

| Setting | Delay | Rate   | Use Case                  |
| ------- | ----- | ------ | ------------------------- |
| Fast    | 20ms  | 50/sec | Gaming, rapid input       |
| Medium  | 100ms | 10/sec | General automation        |
| Slow    | 500ms | 2/sec  | Precise, controlled input |

## ⚠️ Important Notes

- **USB HID Mode**: The app automatically switches Flipper Zero to USB HID mode
- **Computer Compatibility**: Works with Windows, Mac, Linux - any system that accepts USB keyboards
- **Responsible Use**: Please use this tool responsibly and only on systems you own or have permission to test
- **Battery Usage**: High-frequency spamming will drain battery faster

## 🤝 Contributing

Contributions are welcome! Please feel free to:

- 🐛 Report bugs
- 💡 Suggest features
- 🔧 Submit pull requests
- 📚 Improve documentation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Flipper Zero Community** - For the amazing development tools and documentation
- **uFBT Developers** - For making Flipper Zero development accessible
- **Beta Testers (aka petandk)** - For patience during the iterative development process
- **AI Pair Programming** - Demonstrating the power of human-AI collaboration in software development

## 🔗 Links

- [Flipper Zero Official](https://flipperzero.one/)
- [uFBT Documentation](https://pypi.org/project/ufbt/)
- [Flipper Zero Developer Documentation](https://developer.flipper.net/)

---

**Made with ❤️ by AI-Human collaboration**  
_Developed through iterative problem-solving, user feedback, and continuous optimization_

