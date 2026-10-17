#  mnky_bx/core/kiosk_manager.py
"""
Kiosk Manager - Session and Subject Management

Responsibilities:
- Discover available experiments
- List available subjects
- Auto-increment session numbers
- Initialize experiment sessions
- Manage subject-experiment sessions
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class Subject:
    """Subject metadata and session management"""
    
    def __init__(self, subject_id: str, subject_dir: Path):
        """
        Args:
            subject_id: e.g. "subject_id_01"
            subject_dir: Path to subjects/{subject_id}/
        """
        self.subject_id = subject_id
        self.subject_dir = Path(subject_dir)
        self.metadata_file = self.subject_dir / "metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """Load subject metadata"""
        if not self.metadata_file.exists():
            return {
                "subject_id": self.subject_id,
                "created_date": datetime.now().isoformat(),
                "species": "unknown",
                "sex": "unknown",
                "weight_kg": 0.0,
                "enrollment_date": datetime.now().isoformat(),
                "notes": ""
            }
        
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_metadata(self):
        """Save metadata to file"""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)
    
    def get_next_session_number(self, experiment_name: str) -> int:
        """
        Get next session number for experiment.
        
        Returns:
            Next session number (e.g., 2 if session_001 exists)
        """
        experiment_dir = self.subject_dir / experiment_name
        
        if not experiment_dir.exists():
            return 1
        
        # Find all session_XXX directories
        session_dirs = sorted([
            d for d in experiment_dir.iterdir()
            if d.is_dir() and re.match(r'session_\d{3}', d.name)
        ])
        
        if not session_dirs:
            return 1
        
        # Extract session numbers
        session_numbers = [
            int(re.search(r'(\d{3})', d.name).group(1))
            for d in session_dirs
        ]
        
        return max(session_numbers) + 1
    
    def get_session_path(self, experiment_name: str, session_number: int = None) -> Path:
        """
        Get path to session directory.
        
        Args:
            experiment_name: e.g. "gambling_experiment"
            session_number: Optional. If None, returns next session path
            
        Returns:
            Path to session directory (e.g., subjects/subject_id_01/gambling_experiment/session_001/)
        """
        if session_number is None:
            session_number = self.get_next_session_number(experiment_name)
        
        session_dir = self.subject_dir / experiment_name / f"session_{session_number:03d}"
        return session_dir
    
    def __repr__(self) -> str:
        return f"Subject({self.subject_id}, species={self.metadata.get('species')})"


class Experiment:
    """Experiment metadata and configuration"""
    
    def __init__(self, name: str, experiment_dir: Path):
        """
        Args:
            name: e.g. "gambling_experiment"
            experiment_dir: Path to experiments/{name}/
        """
        self.name = name
        self.experiment_dir = Path(experiment_dir)
        self.config_file = self.experiment_dir / "config.json"
        self.conditions_file = self.experiment_dir / "conditions.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load experiment configuration"""
        if not self.config_file.exists():
            return {
                "experiment_name": self.name,
                "description": "Unknown experiment",
                "version": "1.0"
            }
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_description(self) -> str:
        """Get human-readable experiment description"""
        return self.config.get("description", self.name)
    
    def has_conditions_file(self) -> bool:
        """Check if conditions.json exists"""
        return self.conditions_file.exists()
    
    def __repr__(self) -> str:
        return f"Experiment({self.name}, {self.get_description()})"


class KioskManager:
    """
    High-level kiosk management.
    
    Responsibilities:
    - Discover experiments from experiments/ directory
    - List subjects from subjects/ directory
    - Create new subjects
    - Initialize experiment sessions
    - Auto-increment session numbers
    - Manage kiosk configuration
    
    Usage:
        manager = KioskManager(kiosk_config_path, project_root)
        
        # List available experiments and subjects
        experiments = manager.list_experiments()
        subjects = manager.list_subjects()
        
        # Create new subject
        manager.create_subject("subject_id_03")
        
        # Initialize session
        session_path = manager.initialize_session(
            subject_id="subject_id_01",
            experiment_name="gambling_experiment"
        )
    """
    
    def __init__(
        self,
        kiosk_config_path: Path,
        project_root: Path = None
    ):
        """
        Initialize kiosk manager.
        
        Args:
            kiosk_config_path: Path to config/kiosk_config.json
            project_root: Project root directory (auto-detected if None)
        """
        self.kiosk_config_path = Path(kiosk_config_path)
        
        # Auto-detect project root if not provided
        if project_root is None:
            project_root = self.kiosk_config_path.parent.parent
        
        self.project_root = Path(project_root)
        self.subjects_dir = self.project_root / "subjects"
        self.experiments_dir = self.project_root / "experiments"
        
        # Load kiosk config
        with open(self.kiosk_config_path, 'r', encoding='utf-8') as f:
            self.kiosk_config = json.load(f)
        
        self.kiosk_id = self.kiosk_config.get("kiosk_id", "kiosk_001")
        
        logger.info(
            f"KioskManager initialized: {self.kiosk_id}, "
            f"root={self.project_root}"
        )
    
    def list_experiments(self) -> List[Experiment]:
        """
        Discover all experiments in experiments/ directory.
        
        Returns:
            List of Experiment objects
        """
        experiments = []
        
        if not self.experiments_dir.exists():
            logger.warning(f"Experiments directory not found: {self.experiments_dir}")
            return experiments
        
        for exp_dir in sorted(self.experiments_dir.iterdir()):
            if not exp_dir.is_dir():
                continue
            
            # Skip special directories
            if exp_dir.name.startswith('.') or exp_dir.name == '__pycache__':
                continue
            
            # Check for config.json
            config_file = exp_dir / "config.json"
            if not config_file.exists():
                logger.debug(f"Skipping {exp_dir.name}: no config.json")
                continue
            
            try:
                experiment = Experiment(exp_dir.name, exp_dir)
                experiments.append(experiment)
                logger.debug(f"Discovered experiment: {exp_dir.name}")
            except Exception as e:
                logger.warning(f"Error loading experiment {exp_dir.name}: {e}")
        
        return experiments
    
    def get_experiment(self, experiment_name: str) -> Optional[Experiment]:
        """Get experiment by name"""
        exp_dir = self.experiments_dir / experiment_name
        
        if not exp_dir.exists():
            return None
        
        return Experiment(experiment_name, exp_dir)
    
    def list_subjects(self) -> List[Subject]:
        """
        List all subjects in subjects/ directory.
        
        Skips 'not_recognized' directory.
        
        Returns:
            Sorted list of Subject objects
        """
        subjects = []
        
        if not self.subjects_dir.exists():
            logger.warning(f"Subjects directory not found: {self.subjects_dir}")
            return subjects
        
        for subject_dir in sorted(self.subjects_dir.iterdir()):
            if not subject_dir.is_dir():
                continue
            
            # Skip special directories
            if subject_dir.name in ('not_recognized', '.', '__pycache__'):
                continue
            
            # Subject directories should match pattern subject_id_XX
            if not re.match(r'subject_id_\d{2}', subject_dir.name):
                logger.debug(f"Skipping non-subject directory: {subject_dir.name}")
                continue
            
            try:
                subject = Subject(subject_dir.name, subject_dir)
                subjects.append(subject)
                logger.debug(f"Discovered subject: {subject_dir.name}")
            except Exception as e:
                logger.warning(f"Error loading subject {subject_dir.name}: {e}")
        
        return subjects
    
    def get_subject(self, subject_id: str) -> Optional[Subject]:
        """Get subject by ID"""
        subject_dir = self.subjects_dir / subject_id
        
        if not subject_dir.exists():
            return None
        
        return Subject(subject_id, subject_dir)
    
    def create_subject(
        self,
        subject_id: str,
        metadata: Dict = None
    ) -> Subject:
        """
        Create new subject with metadata.
        
        Args:
            subject_id: e.g. "subject_id_03"
            metadata: Optional metadata dict (species, sex, weight, etc.)
            
        Returns:
            Subject object
            
        Raises:
            ValueError: If subject_id already exists
        """
        subject_dir = self.subjects_dir / subject_id
        
        if subject_dir.exists():
            raise ValueError(f"Subject {subject_id} already exists")
        
        # Create directories
        subject_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subject
        subject = Subject(subject_id, subject_dir)
        
        # Update metadata if provided
        if metadata:
            subject.metadata.update(metadata)
        
        subject.save_metadata()
        
        logger.info(f"Created subject: {subject_id}")
        
        return subject
    
    def get_next_subject_id(self) -> str:
        """
        Get next available subject ID.
        
        Returns:
            e.g. "subject_id_03" if subject_id_01 and subject_id_02 exist
        """
        subjects = self.list_subjects()
        
        if not subjects:
            return "subject_id_01"
        
        # Extract numbers
        numbers = []
        for subject in subjects:
            match = re.search(r'subject_id_(\d{2})', subject.subject_id)
            if match:
                numbers.append(int(match.group(1)))
        
        if not numbers:
            return "subject_id_01"
        
        next_number = max(numbers) + 1
        return f"subject_id_{next_number:02d}"
    
    def initialize_session(
        self,
        subject_id: str,
        experiment_name: str,
        auto_create_subject: bool = False
    ) -> Path:
        """
        Initialize new experiment session.
        
        Creates session directory structure:
        subjects/{subject_id}/{experiment_name}/session_{number:03d}/
        
        Args:
            subject_id: e.g. "subject_id_01"
            experiment_name: e.g. "gambling_experiment"
            auto_create_subject: If True, create subject if not exists
            
        Returns:
            Path to session directory
            
        Raises:
            ValueError: If subject or experiment not found
        """
        # Get subject
        subject = self.get_subject(subject_id)
        if not subject:
            if auto_create_subject:
                subject = self.create_subject(subject_id)
            else:
                raise ValueError(f"Subject not found: {subject_id}")
        
        # Get experiment
        experiment = self.get_experiment(experiment_name)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_name}")
        
        # Get next session number
        session_number = subject.get_next_session_number(experiment_name)
        session_path = subject.get_session_path(experiment_name, session_number)
        
        # Create session directories
        session_path.mkdir(parents=True, exist_ok=True)
        (session_path / "trial_images").mkdir(exist_ok=True)
        (session_path / "trial_videos").mkdir(exist_ok=True)
        
        # Create session info file
        session_info = {
            "subject_id": subject_id,
            "experiment_name": experiment_name,
            "session_number": session_number,
            "session_path": str(session_path),
            "start_time": datetime.now().isoformat(),
            "kiosk_id": self.kiosk_id,
            "status": "initialized"
        }
        
        info_file = session_path / "session_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(session_info, f, indent=2)
        
        logger.info(
            f"Session initialized: {subject_id}/{experiment_name}/"
            f"session_{session_number:03d}"
        )
        
        return session_path
    
    def get_session_summary(self, subject_id: str, experiment_name: str) -> Dict:
        """
        Get summary of all sessions for a subject-experiment pair.
        
        Returns:
            Dict with session counts and recent sessions
        """
        subject = self.get_subject(subject_id)
        if not subject:
            return {}
        
        experiment_dir = subject.subject_dir / experiment_name
        
        if not experiment_dir.exists():
            return {
                "total_sessions": 0,
                "latest_session": None
            }
        
        # Find all session directories
        session_dirs = sorted([
            d for d in experiment_dir.iterdir()
            if d.is_dir() and re.match(r'session_\d{3}', d.name)
        ])
        
        return {
            "total_sessions": len(session_dirs),
            "latest_session": session_dirs[-1].name if session_dirs else None,
            "all_sessions": [d.name for d in session_dirs]
        }
    
    def __repr__(self) -> str:
        return (
            f"KioskManager({self.kiosk_id}, "
            f"experiments={len(self.list_experiments())}, "
            f"subjects={len(self.list_subjects())})"
        )
