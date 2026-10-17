#launcher.py#!/usr/bin/env python3
"""
mnky_bx Kiosk Launcher

Main entry point for the kiosk system.

Workflow:
1. Load kiosk configuration
2. Show launcher GUI for experiment/subject selection
3. Initialize experiment session
4. Load and run experiment

Usage:
    python launcher.py

Or with custom config:
    python launcher.py --config /path/to/kiosk_config.json
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import pygame

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from mnky_bx.core.kiosk_manager import KioskManager
from mnky_bx.ui.launcher_ui import LauncherUI
from mnky_bx.logging.experiment_logger import ExperimentLogger


def setup_logging(log_dir: Path = None) -> logging.Logger:
    """Setup logging configuration"""
    if log_dir is None:
        log_dir = PROJECT_ROOT / "logs"
    
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("mnky_bx")
    logger.setLevel(logging.DEBUG)
    
    # File handler
    fh = logging.FileHandler(log_dir / "launcher.log")
    fh.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


def find_kiosk_config(custom_path: Optional[Path] = None) -> Path:
    """Find kiosk configuration file"""
    if custom_path and custom_path.exists():
        return custom_path
    
    # Default locations
    default_paths = [
        PROJECT_ROOT / "config" / "kiosk_config.json",
        Path.home() / ".mnky_bx" / "kiosk_config.json",
    ]
    
    for path in default_paths:
        if path.exists():
            return path
    
    # Fallback: create default
    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "kiosk_config.json"
    
    if not config_path.exists():
        import json
        default_config = {
            "kiosk_id": "kiosk_001",
            "kiosk_type": "traditional_enclosure",
            "hardware": {
                "hardware_type": "auto",
                "arduino_uno": {
                    "port": "COM4",
                    "baudrate": 115200
                }
            }
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
    
    return config_path


def run_experiment(experiment, subject, session_path, kiosk_config):
    """
    Load and run the selected experiment.
    
    TODO: Full implementation
    """
    logger = logging.getLogger("mnky_bx")
    
    logger.info(
        f"Starting experiment: {experiment.name} "
        f"for {subject.subject_id} "
        f"in {session_path}"
    )
    
    # TODO: Implement experiment loading and execution
    # 1. Load experiment module dynamically
    # 2. Load experiment config
    # 3. Load subject adaptive parameters
    # 4. Initialize database
    # 5. Initialize hardware
    # 6. Initialize experiment instance
    # 7. Run experiment.run_session()


def main():
    """Main entry point"""
    # Setup logging
    logger = setup_logging()
    logger.info("=" * 70)
    logger.info("mnky_bx Kiosk Launcher Starting")
    logger.info("=" * 70)
    
    try:
        # Find configuration
        config_path = find_kiosk_config()
        logger.info(f"Using config: {config_path}")
        
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return 1
        
        # Load kiosk configuration
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            kiosk_config = json.load(f)
        
        logger.info(f"Kiosk ID: {kiosk_config.get('kiosk_id')}")
        
        # Initialize kiosk manager
        kiosk_manager = KioskManager(config_path, PROJECT_ROOT)
        logger.info(f"KioskManager: {kiosk_manager}")
        
        # List available resources
        experiments = kiosk_manager.list_experiments()
        subjects = kiosk_manager.list_subjects()
        
        logger.info(f"Experiments available: {len(experiments)}")
        for exp in experiments:
            logger.info(f"  - {exp.name}: {exp.get_description()}")
        
        logger.info(f"Subjects available: {len(subjects)}")
        for subj in subjects:
            logger.info(f"  - {subj.subject_id}")
        
        # Show launcher GUI
        logger.info("Launching GUI...")
        launcher = LauncherUI(kiosk_manager)
        
        experiment, subject, session_path = launcher.run()
        
        if experiment and subject and session_path:
            logger.info(f"Selected: {experiment.name} / {subject.subject_id}")
            logger.info(f"Session path: {session_path}")
            
            # Run experiment
            run_experiment(experiment, subject, session_path, kiosk_config)
            
            logger.info("Experiment completed")
            return 0
        
        else:
            logger.info("Launcher closed without selection")
            return 0
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    
    finally:
        logger.info("=" * 70)
        logger.info("mnky_bx Kiosk Launcher Closed")
        logger.info("=" * 70)


if __name__ == "__main__":
    sys.exit(main())
