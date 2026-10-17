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

- # Update 2026-10-17
## Hybrid Approach: MonkeyLogic Concepts + mnky_bx Implementation

### Current Architecture (Tightly Coupled)
```python
class GamblingExperiment(ExperimentBase):
    def run_trial(self):
        # Selection logic mixed with trial logic
        condition = self.select_condition()  # EMBEDDED
        self.execute_trial(condition)
```

**Integration of [MonkeyLogic](<https://monkeylogic.nimh.nih.gov/>) concepts into our existing framework:**

### Proposed Architecture (Modular)

1. Conditions File → conditions.json (or conditions.py) - Instead of a MATLAB text file, use a structured JSON config:
2. scenes.py (NEW - Experiment-specific)
3. experiment_base.py (UPDATED)
4. experiment.py (UPDATED - Gambling Experiment)
5. conditions.json (Experiment-specific)

```graphql
experiments/gambling_experiment/
├── experiment.py           # Stimulus rendering + outcome eval
├── scenes.py               # Scene definitions (NEW)
├── conditions.json         # Condition definitions (NEW)
├── config.json             # Experiment timing/display config
└── subject_params/
    ├── default.json
    └── subject_id_01.json

mnky_bx/core/
├── experiment_base.py      # Trial orchestration (UPDATED)
├── condition_manager.py    # Condition selection (NEW)
└── trial_manager.py
```

### Benefits of This Architecture
---
| Aspect	| Benefit |
|---|---|
| **Separation of Concerns**	| Conditions, scenes, and stimulus rendering are completely decoupled
| **Reusability**	| Scenes can be shared across experiments
| **Testability**	| Each module can be tested independently
| **Maintainability**	| Changes to conditions don't affect code; changes to scenes don't affect conditions
| **MonkeyLogic-like**	| Conditions file + timing script structure, but in Python 
| **Flexibility**	| Easy to add new block progression rules, scene types, etc.|
---

## Summary Table

| File	| Purpose	| Type
| --- | --- | --- |
| mnky_bx/core/condition_manager.py	| Condition selection & block progression	| Core Module
| mnky_bx/core/experiment_base.py | 	Trial orchestration framework	| Core Module
| experiments/gambling_experiment/scenes.py	| Scene-based trial phases	| Experiment
| experiments/gambling_experiment/experiment.py	| Gambling task implementation	| Experiment
| experiments/gambling_experiment/conditions.json	| Trial condition definitions	| Config
| experiments/gambling_experiment/config.json	| Experiment parameters	| Config
| experiments/gambling_experiment/subject_params/default.json	| Default adaptive params	| Config
| mnky_bx/core/__init__.py	| Package exports	| Package
experiments/__init__.py	| Experiments package	| Package
| experiments/gambling_experiment/__init__.py	| Module exports	| Package
---


## Key Design Principles
Separation of Concerns

### 1. ConditionManager handles all condition logic
- ExperimentBase handles trial orchestration
- Scenes handle stimulus rendering & timing
- Experiment subclass implements only outcome evaluation
### 2. JSON Configuration

- All timing, stimulus, and reward params in config.json
- All trial conditions in conditions.json
- All adaptive params in subject_params/ JSON files

### 3. Reusability

- Scenes can be shared across experiments
- ConditionManager is experiment-agnostic
- ExperimentBase provides consistent interface
### 4. Testability

- Each module can be tested independently
- Mock hardware/database for testing
- Scene logic independent of hardware