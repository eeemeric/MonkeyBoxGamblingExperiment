# mnky_bx Kiosk System

Modular behavioral neuroscience kiosk system for primate experiments.

## Architecture

- **Hardware**: Dual configurations (Arduino Uno USB or Adafruit Feather BLE)
- **Input**: Physical buttons or touchscreen
- **Face Recognition**: Subject identification via camera
- **Database**: SQLite with image filesystem storage
- **Experiments**: Modular experiment framework

## Quick Start

1. Edit config/kiosk_config.json for your hardware setup
2. Run: `python launcher.py`
3. Select experiment and subject from launcher GUI

## Directory Structure
```bash
mnky_bx/
├── mnky_bx/           # Framework package
├── config/            # Configuration files
├── experiments/       # Experiment implementations
├── subjects/          # Subject data and face encodings
├── docs/              # Documentation
└── tests/             # Unit tests
```

## Configuration

- `config/kiosk_config.json` - Main kiosk settings
- `config/face_recognition_config.json` - Face recognition parameters
- `config/notification_config_TEMPLATE.json` - Email/SMS alerts (fill in credentials)
- `experiments/*/config.json` - Experiment-specific settings

## Hardware Configurations

### Config 1: Traditional Enclosure (USB)
- Arduino Uno on COM4 (USB)
- Button input: Physical left/right buttons
- LED feedback: Hardware LEDs
- Reward: Motor control via Arduino

### Config 2: Touchscreen Kiosk (BLE)
- Adafruit Feather on COM3 (BLE wireless)
- Button input: Touchscreen taps
- Visual feedback: Rendered on screen
- Reward: Motor control via Feather

## Face Recognition

Subjects are identified via camera:
- Recognized subjects: `subjects/subject_id_XX/`
- Unrecognized faces: `subjects/not_recognized/`

## Documentation

See `docs/` for:
- ARCHITECTURE.md - System design
- ORIGINAL_SCRIPT_REFERENCE.md - Original monolithic script info
- REFACTORING_GUIDE.md - Migration guide

## Requirements

See requirements.txt or install:
```bash
pip install -r requirements.txt
```
## Support
For issues or questions, see docs/ or contact: eee@jhu.edu
