# mnky_bx/logging/experiment_logger.py

"""
Experiment Logger

Logs all trial events and metadata to file and database.
"""

import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ExperimentLogger:
    """
    Logs trial-by-trial data and events.
    
    Writes to:
    - SQLite database (trial_data table)
    - JSON log file (session_log.json)
    - Text log file (session_log.txt)
    """
    
    def __init__(self, session_path: Path, subject_id: str, experiment_name: str):
        """
        Args:
            session_path: Path to session directory
            subject_id: Subject identifier
            experiment_name: Experiment name
        """
        self.session_path = Path(session_path)
        self.subject_id = subject_id
        self.experiment_name = experiment_name
        
        # Log files
        self.json_log_file = self.session_path / "session_log.json"
        self.text_log_file = self.session_path / "session_log.txt"
        
        # Event log
        self.events = []
        
        # Setup file logging
        self._setup_file_logging()
    
    def _setup_file_logging(self):
        """Initialize log files"""
        # Create parent directory
        self.session_path.mkdir(parents=True, exist_ok=True)
        
        # Write initial log files
        self._write_json_log()
        self._write_text_log()
    
    def log_trial_start(self, trial_number: int, condition: Dict):
        """Log trial start"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "trial_start",
            "trial_number": trial_number,
            "condition": condition
        }
        self.events.append(event)
        logger.info(f"Trial {trial_number} started: {condition}")
    
    def log_trial_end(self, trial_number: int, result: Dict):
        """Log trial end"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "trial_end",
            "trial_number": trial_number,
            "result": result
        }
        self.events.append(event)
        logger.info(f"Trial {trial_number} ended: {result}")
    
    def log_event(self, event_type: str, data: Dict = None):
        """Log custom event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data or {}
        }
        self.events.append(event)
    
    def _write_json_log(self):
        """Write events to JSON log file"""
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.events, f, indent=2)
    
    def _write_text_log(self):
        """Write events to text log file"""
        with open(self.text_log_file, 'w', encoding='utf-8') as f:
            f.write(f"Session Log: {self.subject_id} / {self.experiment_name}\n")
            f.write(f"Started: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            
            for event in self.events:
                f.write(f"{event['timestamp']} | {event['event_type']}\n")
                if 'data' in event:
                    f.write(f"  {event['data']}\n")
                f.write("\n")
    
    def finalize(self):
        """Write final logs"""
        self.log_event("session_end", {"end_time": datetime.now().isoformat()})
        self._write_json_log()
        self._write_text_log()
