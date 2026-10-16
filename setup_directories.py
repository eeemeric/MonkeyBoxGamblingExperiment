#!/usr/bin/env python3
"""
Cross-platform directory setup script for mnky_bx kiosk system
Updated for dual hardware controller architecture (Arduino Uno + Adafruit Feather)

Creates complete directory structure with:
- Core framework modules (core, hardware, database, logging, etc.)
- Hardware abstraction layer (Arduino Uno full control + Feather reward-only)
- Touchscreen input system
- Face recognition system
- Configuration files (JSON)
- Placeholder Python files with docstrings and TODO markers
- Subject directories (up to 12)
- Experiment directories with configs

Usage: python setup_directories.py [project_root] [num_subjects] [experiments]
Example: python setup_directories.py . 12 gambling_experiment blackjack

Author: eee@jhu.edu

"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime


def create_placeholder_python_file(file_path, description):
    """Create a placeholder Python file with docstring and TODO"""
    
    content = f'''"""
{description}

TODO: Implement this module
"""

# Placeholder for implementation
pass
'''
    
    if not file_path.exists():
        file_path.write_text(content, encoding='utf-8')


def create_kiosk_config(config_path):
    """Create kiosk configuration file"""
    
    config = {
        "kiosk_id": "kiosk_001",
        "kiosk_type": "traditional_enclosure",
        "description": "Choose 'traditional_enclosure' (USB Arduino) or 'touchscreen_kiosk' (BLE Feather + Touchscreen)",
        
        "hardware": {
            "hardware_type": "auto",
            "description_hardware_type": "Options: 'arduino_uno_full', 'feather_reward_only', 'auto'",
            
            "arduino_uno": {
                "port": "COM4",
                "baudrate": 115200,
                "motor_max_position": 10.0,
                "motor_pulse_duration_ms": 500
            },
            
            "adafruit_feather": {
                "port": "COM3",
                "baudrate": 115200,
                "ble_device_name": "mnky_bx_feather_01",
                "motor_max_position": 10.0,
                "motor_pulse_duration_ms": 500,
                "battery_warning_threshold": 20.0
            }
        },
        
        "touchscreen": {
            "enabled": False,
            "description": "Enable if using Feather + Touchscreen kiosk setup",
            "device": "/dev/input/touchscreen0",
            "display_width": 1920,
            "display_height": 1080,
            "fullscreen": True,
            "button_size_pixels": 200,
            "button_y_offset_pixels": 850,
            "left_button_x": 100,
            "right_button_x": 1720,
            "hold_duration_ms": 100
        },
        
        "camera": {
            "device_id": 0,
            "width": 640,
            "height": 480,
            "fps": 30
        },
        
        "display": {
            "fullscreen": True,
            "width": 1920,
            "height": 1080,
            "monitor_index": 0
        },
        
        "logging": {
            "level": "INFO",
            "log_dir": "logs/"
        },
        
        "notifications": {
            "enabled": True,
            "smtp_enabled": True,
            "sms_enabled": True
        }
    }
    
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')


def create_face_recognition_config(config_path):
    """Create face recognition configuration"""
    
    config = {
        "embedding_model": "deepface",
        "description_embedding_model": "Options: 'deepface', 'facenet', 'vggface2'",
        
        "recognition": {
            "confidence_threshold": 0.7,
            "distance_threshold": 0.6,
            "description": "Face is recognized if distance < distance_threshold"
        },
        
        "unrecognized_clustering": {
            "enabled": True,
            "clustering_algorithm": "dbscan",
            "epsilon": 0.5,
            "min_samples": 3,
            "description": "Cluster unrecognized faces into potential new subjects"
        },
        
        "capture": {
            "capture_rate_fps": 3,
            "jpeg_quality": 85,
            "description": "Frame capture settings during trials"
        }
    }
    
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')


def create_notification_config_template(config_path):
    """Create notification configuration template (user fills in credentials)"""
    
    config = {
        "email": {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "YOUR_EMAIL@gmail.com",
            "sender_password": "YOUR_APP_PASSWORD",
            "recipient_emails": ["admin@lab.com"],
            "description": "Fill in your SMTP credentials or leave disabled"
        },
        
        "sms": {
            "enabled": False,
            "provider": "twilio",
            "twilio_account_sid": "YOUR_ACCOUNT_SID",
            "twilio_auth_token": "YOUR_AUTH_TOKEN",
            "twilio_from_number": "+1234567890",
            "recipient_numbers": ["+1234567890"],
            "description": "Fill in Twilio credentials or leave disabled"
        },
        
        "alerts": {
            "hardware_failure": True,
            "battery_low": True,
            "experiment_error": True,
            "storage_full": True
        }
    }
    
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')


def create_raspi_touchscreen_config(config_path):
    """Create Raspberry Pi touchscreen configuration"""
    
    config = {
        "enabled": False,
        "description": "Configuration for Raspberry Pi touchscreen kiosk setup",
        
        "display": {
            "device": "/dev/fb0",
            "resolution": [1920, 1080],
            "rotation": 0,
            "brightness": 100
        },
        
        "touchscreen": {
            "device": "/dev/input/touchscreen0",
            "calibration_enabled": False,
            "calibration_file": "calibration.dat"
        },
        
        "buttons": {
            "left": {
                "x_center": 100,
                "y_center": 850,
                "width": 200,
                "height": 200,
                "color_inactive": [100, 100, 100],
                "color_active": [0, 255, 0],
                "color_pressed": [255, 0, 0]
            },
            "right": {
                "x_center": 1820,
                "y_center": 850,
                "width": 200,
                "height": 200,
                "color_inactive": [100, 100, 100],
                "color_active": [0, 255, 0],
                "color_pressed": [255, 0, 0]
            }
        }
    }
    
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')


def create_experiment_config(config_path, exp_name):
    """Create experiment configuration"""
    
    config = {
        "experiment_name": exp_name,
        "description": f"Configuration for {exp_name} experiment",
        
        "timing": {
            "ITI_ms": 1000,
            "max_response_time_ms": 5000,
            "outcome_display_ms": 500
        },
        
        "trial": {
            "max_trials_per_session": 100,
            "randomize_trial_order": True
        },
        
        "stimulus": {
            "circle_radius_pixels": 100,
            "colors_enabled": True
        },
        
        "reward": {
            "default_magnitude": 5,
            "max_magnitude": 10
        }
    }
    
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')


def create_default_subject_params(config_path):
    """Create default subject parameters"""
    
    config = {
        "subject_id": "default",
        "description": "Default parameters for new subjects. Override per subject in subject_params/subject_id_XX.json",
        
        "timing": {
            "ITI_ms": 1000,
            "max_response_time_ms": 5000,
            "outcome_display_ms": 500
        },
        
        "trial": {
            "difficulty": "medium",
            "trial_order": "random"
        },
        
        "reward": {
            "magnitude": 5,
            "probability": 1.0
        }
    }
    
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')


def create_subject_metadata(config_path, subject_id):
    """Create subject metadata file"""
    
    config = {
        "subject_id": subject_id,
        "date_enrolled": datetime.now().isoformat(),
        "species": "macaque",
        "sex": "unknown",
        "weight_kg": None,
        "notes": "",
        
        "face_recognition": {
            "num_enrollments": 0,
            "avg_confidence": None,
            "last_recognized": None
        },
        
        "experiments": {}
    }
    
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')


def create_not_recognized_metadata(config_path):
    """Create metadata for unrecognized faces directory"""
    
    config = {
        "directory_type": "unrecognized_faces",
        "description": "Faces that were not recognized during trials",
        "clustering_results": "See clustering_results.json after running face_clustering",
        "created": datetime.now().isoformat()
    }
    
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')


def create_readme_files(project_root, experiments, num_subjects):
    """Create README files in key directories"""
    
    root_path = Path(project_root)
    
    # Main README
    main_readme = f"""# mnky_bx Kiosk System

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
        """
    # Write the content to the file 
    (root_path / "README.md").write_text(main_readme, encoding='utf-8')

    # Subjects README
    subjects_readme = """# Subjects Directory

    Each subject has their own directory:

    subjects/
    ├── not_recognized/          # Unrecognized faces from trials
    │   ├── raw_images/          # Original video frames
    │   ├── face_images/         # Detected face crops
    │   ├── embeddings/          # Face embeddings (for clustering)
    │   └── clustering_results.json
    │
    ├── subject_id_01/           # Individual subject
    │   ├── metadata.json        # Subject info (species, weight, etc.)
    │   ├── face_encodings/      # Face embeddings for recognition
    │   ├── gambling_experiment/
    │   │   ├── session_001/     # First session
    │   │   ├── session_002/
    │   │   └── session_archive/ # Older sessions
    │   └── blackjack/
    │       ├── session_001/
    │       └── session_archive/
    │
    └── subject_id_02/ through subject_id_{num_subjects:02d}/

    ## Session Directory Structure

    session_001/
    ├── database.db              # SQLite database (trial data, frame metadata)
    ├── trial_images/            # JPEG frames from trial videos
    │   ├── trial_001/
    │   │   ├── frame_001.jpg
    │   │   └── frame_002.jpg
    │   └── trial_002/
    ├── trial_videos/            # Encoded video files (optional)
    │   ├── trial_001.h265
    │   └── trial_002.h265
    ├── recognition_log.json     # Face recognition results per frame
    └── session_log.txt          # Event log with timestamps

    ## Session Directory Structure Explanation

    session_001/
    ├── database.db              # SQLite database (trial data, frame metadata)
    ├── trial_images/            # JPEG frames from trial videos
    │   ├── trial_001/
    │   │   ├── frame_001.jpg
    │   │   └── frame_002.jpg
    │   └── trial_002/
    ├── trial_videos/            # Encoded video files (optional)
    │   ├── trial_001.h265
    │   └── trial_002.h265
    ├── recognition_log.json     # Face recognition results per frame
    └── session_log.txt          # Event log with timestamps


    ## Subject Metadata
    Each subject's `metadata.json` contains:

    - Enrollment date
    - Demographics (species, sex, weight)
    - Face recognition statistics
    - Experiment history
    ## Face Recognition
    - Faces captured during trials are stored in trial_images/
    - Recognized: Subject ID + confidence score logged
    - Unrecognized: Stored in subjects/not_recognized/
    - Can cluster unrecognized faces to identify new subjects

    See face_recognition_system/ for details.
    """
    # Write the content to the file
    (root_path / "subjects" / "README.md").write_text(subjects_readme, encoding='utf-8')

    # Experiments README
    experiments_readme = """# Experiments Directory

    experiments/
    ├── gambling_experiment/
    │   ├── experiment.py        # Main experiment class (subclass ExperimentBase)
    │   ├── config.json          # Experiment parameters
    │   └── subject_params/
    │       ├── default.json     # Default parameters for new subjects
    │       ├── subject_id_01.json  # Subject-specific overrides
    │       └── subject_id_02.json
    │
    └── blackjack/
        ├── experiment.py
        ├── config.json
        └── subject_params/

    ## Creating a New Experiment
    1. Create directory: experiments/your_experiment/
    2. Implement experiment.py (subclass ExperimentBase)
    3. Define config.json with timing and parameters
    4. Add default subject params in subject_params/default.json
    ## ExperimentBase Interface
    Your experiment should implement:

    python
    from mnky_bx.core.experiment_base import ExperimentBase

    class YourExperiment(ExperimentBase):
        def draw_stimuli(self):
            # Render stimulus on screen
            pass
        
        def wait_for_response(self):
            # Wait for button/touchscreen input
            pass
        
        def reveal_outcome(self):
            # Show trial result
            pass
    ```
    ## Configuration
    `config.json` defines:

    - Timing (ITI, response timeout, outcome duration)
    - Stimulus properties (colors, sizes)
    - Reward (magnitude, probability)
    `subject_params/default.json` defines adaptive parameters that can be customized per subject.

    ## Trial Data
    Trial results saved to SQLite:

    - Trial number, type, choice
    - Success/failure
    - Reward delivered
    - Timestamps

    ## Face Recognition During Trials
    During each trial:

    1. Frames captured at 3 FPS
    2. Face detection per frame
    3. Face recognition (subject identification)
    4. Results logged in recognition_log.json
    5. Images stored in trial_images/
    6. Adaptive parameters can adjust based on recognized subject.
    """
    # Write the content to the file
    (root_path / "experiments" / "README.md").write_text(experiments_readme,encoding='utf-8')

    # Docs README
    docs_readme = """# Documentation
    ## Key Documents
    - **ARCHITECTURE.md** - Complete system architecture and design decisions
    - **ORIGINAL_SCRIPT_REFERENCE.md** - Mapping of original monolithic script to modular framework
    - **REFACTORING_GUIDE.md** - Step-by-step migration guide for existing experiments

    ## Original Scripts
    `original_scripts/` contains the original `MonkeyBoxGamblingExperiment.py` for reference during development.

    ## Examples
    See examples/ for sample configurations and experiment implementations.
    """
    # Write the content to the file
    (root_path / "docs" / "README.md").write_text(docs_readme, encoding='utf-8')

    # Tests README
    tests_readme = """# Tests Directory
    Unit and integration tests for mnky_bx framework.

    ### Running Tests
    ```bash
    pytest tests/
    pytest tests/test_hardware.py -v
    pytest tests/test_face_recognition.py -v
    ```
    ### Test Structure
    ```python
    tests/
    ├── fixtures/                # Test data and mocks
    │   ├── mock_hardware.py
    │   ├── mock_camera.py
    │   └── sample_images/
    ├── test_hardware.py         # Arduino/Feather controller tests
    ├── test_face_recognition.py # Face recognition pipeline tests
    ├── test_database.py         # Database operations tests
    ├── test_config.py           # Configuration loading tests
    └── test_experiment_base.py  # Experiment framework tests
    ```
    ###Contributing Tests
    Add tests for new features in:
    1. Create test_*.py in this directory
    2. Use fixtures from fixtures/
    3. Follow pytest conventions
    4. Run: pytest before committing
    """
    # Write the content to the file
    (root_path / "tests" / "README.md").write_text(tests_readme, encoding='utf-8')

def create_example_experiment(experiment_path: Path):
    """Create template experiment file"""

    content = '''"""
    Example Gambling Experiment

    Implements decision-making task with probabilistic outcomes.

    TODO: Complete implementation
    """

    import pygame
    from mnky_bx.core.experiment_base import ExperimentBase

    class GamblingExperiment(ExperimentBase):
    """
    Gambling experiment where subjects choose between:
    - Sure option: guaranteed reward
    - Gamble option: probabilistic reward
    """

        def __init__(self, config: dict, logger, database, hardware):
            """
            Initialize experiment.
            
            Args:
                config: Experiment configuration (from config.json)
                logger: ExperimentLogger instance
                database: Database manager
                hardware: HardwareController instance (Arduino or Feather)
            """
            super().__init__(config, logger, database, hardware)
            
            # TODO: Initialize experiment-specific parameters
            self.left_color = (0, 128, 0)      # Green
            self.right_color = (0, 0, 131)     # Blue
            self.circle_radius = 100

        def draw_stimuli(self):
            """Draw stimulus options on screen"""
            # TODO: Render left and right circles
            # self.draw_circle(self.left_color, "left")
            # self.draw_circle(self.right_color, "right")
            pygame.display.flip()

        def wait_for_response(self):
            """Wait for subject to make choice"""
            # TODO: Implement response waiting
            # - For Arduino: listen for button presses
            # - For Touchscreen: listen for screen taps
            # Set self.choice to "left" or "right"
            pass

        def reveal_outcome(self):
            """Show trial outcome"""
            # TODO: Render outcome (win/loss) on screen
            # If win: show reward color
            # If loss: show error
            pygame.display.flip()

        def run_trial(self):
            """Execute single trial"""
            # TODO: Implement trial flow if needed
            # Otherwise inherit from ExperimentBase
            super().run_trial()

        if name == "main":
        # For standalone testing
        pass
        '''
    # Write the content to the file
    experiment_path.write_text(content, encoding='utf-8')

def create_directories(project_root, num_subjects=12, experiments=None):
    """Create all directories for mnky_bx system"""

    if experiments is None:
        experiments = ["gambling_experiment", "blackjack"]

    project_path = Path(project_root)

    # Core package directory
    mnky_bx_dir = project_path / "mnky_bx"

    print(f"\n{'='*70}")
    print(f"Creating mnky_bx kiosk system structure")
    print(f"Project root: {project_path.absolute()}")
    print(f"Subjects: {num_subjects}")
    print(f"Experiments: {', '.join(experiments)}")
    print(f"{'='*70}\n")

    # ===== Core Directories =====
    directories = [
        # Core package
        mnky_bx_dir,
        mnky_bx_dir / "core",
        mnky_bx_dir / "database",
        mnky_bx_dir / "logging",
        mnky_bx_dir / "notifications",
        mnky_bx_dir / "face_recognition_system",

        # Hardware modules
        mnky_bx_dir / "hardware",
        mnky_bx_dir / "hardware" / "arduino",
        mnky_bx_dir / "hardware" / "camera",

        # UI modules
        mnky_bx_dir / "ui",
        mnky_bx_dir / "ui" / "input_handlers",

        # Utils
        mnky_bx_dir / "utils",

        # Top-level directories
        project_path / "config",
        project_path / "experiments",
        project_path / "subjects",
        project_path / "tests",
        project_path / "tests" / "fixtures",
        project_path / "docs",
        project_path / "docs" / "original_scripts",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory.relative_to(project_path)}")

    # ===== Create Subject Directories =====
    print(f"\n--- Creating subject directories ---")

    # Not recognized directory
    not_recognized_dir = project_path / "subjects" / "not_recognized"
    not_recognized_subdirs = [
        not_recognized_dir / "raw_images",
        not_recognized_dir / "face_images",
        not_recognized_dir / "embeddings",
    ]
    for d in not_recognized_subdirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {d.relative_to(project_path)}")

    # Subject directories (subject_id_01 through subject_id_XX)
    for i in range(1, num_subjects + 1):
        subject_id = f"subject_id_{i:02d}"
        subject_dir = project_path / "subjects" / subject_id
        subject_subdirs = [
            subject_dir / "face_encodings",
        ]

        # Add experiment subdirs for each subject
        for exp in experiments:
            subject_subdirs.append(subject_dir / exp / "session_archive")

        for d in subject_subdirs:
            d.mkdir(parents=True, exist_ok=True)

        print(f"✓ Created: {subject_dir.relative_to(project_path)}")

    # ===== Create Experiment Directories =====
    print(f"\n--- Creating experiment directories ---")

    for exp in experiments:
        exp_dir = project_path / "experiments" / exp
        exp_subdirs = [
            exp_dir / "subject_params",
        ]

        for d in exp_subdirs:
            d.mkdir(parents=True, exist_ok=True)

        print(f"✓ Created: {exp_dir.relative_to(project_path)}")

    # ===== Create __init__.py files =====
    print(f"\n--- Creating __init__.py files ---")

    init_paths = [
        mnky_bx_dir / "__init__.py",
        mnky_bx_dir / "core" / "__init__.py",
        mnky_bx_dir / "database" / "__init__.py",
        mnky_bx_dir / "logging" / "__init__.py",
        mnky_bx_dir / "notifications" / "__init__.py",
        mnky_bx_dir / "face_recognition_system" / "__init__.py",
        mnky_bx_dir / "hardware" / "__init__.py",
        mnky_bx_dir / "hardware" / "arduino" / "__init__.py",
        mnky_bx_dir / "hardware" / "camera" / "__init__.py",
        mnky_bx_dir / "ui" / "__init__.py",
        mnky_bx_dir / "ui" / "input_handlers" / "__init__.py",
        mnky_bx_dir / "utils" / "__init__.py",
        project_path / "tests" / "__init__.py",
        project_path / "tests" / "fixtures" / "__init__.py",
    ]

    for path in init_paths:
        path.touch()

    print(f"✓ Created {len(init_paths)} __init__.py files")

    # ===== Create Python Module Files =====
    print(f"\n--- Creating Python module files ---")

    module_files = {
        # Core modules
        mnky_bx_dir / "core" / "config.py": "Configuration management",
        mnky_bx_dir / "core" / "experiment_base.py": "Base experiment class",
        mnky_bx_dir / "core" / "kiosk_manager.py": "Kiosk session management",
        mnky_bx_dir / "core" / "trial_manager.py": "Trial orchestration",
        mnky_bx_dir / "core" / "db_manager.py": "Database operations",

        # Database modules
        mnky_bx_dir / "database" / "schemas.py": "SQLite database schemas",

        # Logging modules
        mnky_bx_dir / "logging" / "experiment_logger.py": "Trial and event logging",
        mnky_bx_dir / "logging" / "error_handler.py": "Error handling and reporting",

        # Notification modules
        mnky_bx_dir / "notifications" / "notification_manager.py": "Notification dispatcher",
        mnky_bx_dir / "notifications" / "email_notifier.py": "Email notifications",
        mnky_bx_dir / "notifications" / "sms_notifier.py": "SMS notifications via Twilio",

        # Face recognition modules
        mnky_bx_dir / "face_recognition_system" / "recognition_engine.py": "Face recognition core",
        mnky_bx_dir / "face_recognition_system" / "subject_registry.py": "Subject metadata management",
        mnky_bx_dir / "face_recognition_system" / "subject_parameter_manager.py": "Adaptive parameters per subject",
        mnky_bx_dir / "face_recognition_system" / "face_clustering.py": "Cluster unrecognized faces",

        # Hardware modules - Base
        mnky_bx_dir / "hardware" / "hardware_interface.py": "High-level hardware abstraction",
        mnky_bx_dir / "hardware" / "health_monitor.py": "Hardware health checking",
        mnky_bx_dir / "hardware" / "hardware_factory.py": "Controller factory (Arduino/Feather)",

        # Hardware modules - Arduino
        mnky_bx_dir / "hardware" / "arduino" / "base_controller.py": "Abstract hardware controller",
        mnky_bx_dir / "hardware" / "arduino" / "protocol.py": "Serial communication protocol",
        mnky_bx_dir / "hardware" / "arduino" / "commands.py": "Command enumerations",
        mnky_bx_dir / "hardware" / "arduino" / "arduino_uno_controller.py": "Arduino Uno (USB full control)",
        mnky_bx_dir / "hardware" / "arduino" / "adafruit_feather_controller.py": "Adafruit Feather (BLE reward-only)",

        # Hardware modules - Camera
        mnky_bx_dir / "hardware" / "camera" / "camera_system.py": "Camera and motion detection",
        mnky_bx_dir / "hardware" / "camera" / "capture_manager.py": "Frame capture and storage",
        mnky_bx_dir / "hardware" / "camera" / "face_encoder.py": "Face embedding extraction",

        # UI modules
        mnky_bx_dir / "ui" / "pygame_utils.py": "Pygame helper utilities",
        mnky_bx_dir / "ui" / "error_screen.py": "Error display overlay",
        mnky_bx_dir / "ui" / "launcher_ui.py": "Experiment launcher GUI",
        mnky_bx_dir / "ui" / "subject_enrollment_ui.py": "Subject enrollment interface",
        mnky_bx_dir / "ui" / "input_system.py": "Unified input manager",

        # UI input handlers
        mnky_bx_dir / "ui" / "input_handlers" / "input_base.py": "Abstract input handler",
        mnky_bx_dir / "ui" / "input_handlers" / "keyboard_handler.py": "Keyboard input",
        mnky_bx_dir / "ui" / "input_handlers" / "button_handler.py": "Physical button input (Arduino)",
        mnky_bx_dir / "ui" / "input_handlers" / "touchscreen_handler.py": "Touchscreen input",

        # Utils
        mnky_bx_dir / "utils" / "config_loader.py": "JSON configuration loader",
        mnky_bx_dir / "utils" / "helpers.py": "Utility helper functions",
        mnky_bx_dir / "utils" / "storage_utils.py": "Storage and file management",

        # Top-level
        project_path / "launcher.py": "Main kiosk launcher application",
    }

    for file_path, description in module_files.items():
        create_placeholder_python_file(file_path, description)

    print(f"✓ Created {len(module_files)} Python module files")

    # ===== Create Configuration Files =====
    print(f"\n--- Creating configuration files ---")

    create_kiosk_config(project_path / "config" / "kiosk_config.json")
    create_face_recognition_config(project_path / "config" / "face_recognition_config.json")
    create_notification_config_template(project_path / "config" / "notification_config_TEMPLATE.json")
    create_raspi_touchscreen_config(project_path / "config" / "raspi_touchscreen_config.json")

    print(f"✓ Created 4 configuration files")

    # ===== Create Experiment Configs =====
    print(f"\n--- Creating experiment configurations ---")

    for exp in experiments:
        create_experiment_config(project_path / "experiments" / exp / "config.json", exp)
        create_default_subject_params(project_path / "experiments" / exp / "subject_params" / "default.json")

    print(f"✓ Created {len(experiments)} experiment configs")

    # ===== Create Subject Configs =====
    print(f"\n--- Creating subject metadata files ---")

    for i in range(1, num_subjects + 1):
        subject_id = f"subject_id_{i:02d}"
        subject_dir = project_path / "subjects" / subject_id
        create_subject_metadata(subject_dir / "metadata.json", subject_id)

    create_not_recognized_metadata(project_path / "subjects" / "not_recognized" / "metadata.json")

    print(f"✓ Created {num_subjects + 1} subject metadata files")

    # ===== Create README Files =====
    print(f"\n--- Creating README files ---")

    create_readme_files(project_path, experiments, num_subjects)

    print(f"✓ Created README files")

    # ===== Create Example Experiment =====
    print(f"\n--- Creating example experiment template ---")

    create_example_experiment(project_path / "experiments" / "gambling_experiment" / "experiment.py")

    print(f"✓ Created example experiment template")

    # ===== Summary =====
    print(f"\n{'=' * 70}")
    print(f"✓ Setup complete!")
    print(f"{'=' * 70}")
    print(f"\nNext steps:")
    print(f"1. Fill in module implementations in: mnky_bx/")
    print(f"2. Edit configuration files in: config/")
    print(f"3. Create experiment implementations in: experiments/")
    print(f"4. Install dependencies: pip install -r requirements.txt")
    print(f"5. Run launcher: python launcher.py")
    print(f"\nDocumentation: See docs/ directory")
    print(f"\n")

def main():
    """Main entry point"""
    if __name__ == "__main__":
        """Main entry point"""
        if len(sys.argv) > 1:
            project_root = sys.argv[1]
        else:
            project_root = "."

        if len(sys.argv) > 2:
            try:
                num_subjects = int(sys.argv[2])
            except ValueError:
                num_subjects = 12
        else:
            num_subjects = 12

        if len(sys.argv) > 3:
            experiments = sys.argv[3:]
        else:
            experiments = ["gambling_experiment", "blackjack"]

        try:
            create_directories(project_root, num_subjects, experiments)
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()


