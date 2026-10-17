# mnky_bx/core/condition_manager.py
"""
Condition Management Module

Handles:
- Loading condition definitions from JSON
- Selecting conditions based on frequency/probability
- Managing block progression
- Tracking condition history
- Adaptive subject parameters
"""

import json
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Condition:
    """Single trial condition definition"""
    condition_id: int
    frequency: float
    trial_type: str
    block: str
    parameters: Dict
    metadata: Dict = None
    
    def __post_init__(self):
        """Validate condition"""
        if self.frequency < 0 or self.frequency > 1:
            raise ValueError(f"Frequency must be 0-1, got {self.frequency}")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Block:
    """Logical grouping of conditions"""
    name: str
    description: str
    conditions: List[Condition]
    progression_rules: Dict


class ConditionManager:
    """
    Manages trial conditions and block progression.
    
    Responsibilities:
    - Load conditions from JSON config
    - Select weighted random condition
    - Track condition history per trial
    - Manage block progression
    - Apply subject-specific parameter overrides
    
    Example:
        manager = ConditionManager(
            conditions_file=Path("conditions.json"),
            subject_params={"learning_rate": 0.9}
        )
        condition = manager.get_next_condition()
        manager.record_trial_outcome(error_code="correct")
        summary = manager.get_session_summary()
    """
    
    def __init__(
        self,
        conditions_file: Path,
        subject_params: Dict = None,
        logger_instance=None
    ):
        """
        Initialize condition manager.
        
        Args:
            conditions_file: Path to conditions.json
            subject_params: Subject-specific parameter overrides (e.g., adaptive params)
            logger_instance: Optional logger instance
        """
        self.conditions_file = Path(conditions_file)
        self.subject_params = subject_params or {}
        self.logger = logger_instance or logger
        
        # Load conditions
        self.blocks: Dict[str, Block] = {}
        self.all_conditions: List[Condition] = []
        self.load_conditions()
        
        # Tracking
        self.current_block_name = self.get_first_block_name()
        self.trial_history: List[Dict] = []
        self.condition_history: List[Condition] = []
        self.block_trial_count: Dict[str, int] = {}
        self.block_error_count: Dict[str, int] = {}
        self.block_transition_log: List[Dict] = []
        
        self.logger.info(
            f"ConditionManager initialized: "
            f"{len(self.all_conditions)} conditions, "
            f"{len(self.blocks)} blocks"
        )
    
    def load_conditions(self):
        """
        Load and parse conditions.json
        
        Expected format:
        {
            "blocks": {
                "learning": {
                    "description": "...",
                    "conditions": [
                        {
                            "condition_id": 1,
                            "frequency": 0.25,
                            "trial_type": "sure_vs_gamble",
                            "parameters": {...}
                        }
                    ]
                }
            },
            "progression_rules": {
                "min_trials_per_block": 50,
                "performance_threshold": 0.70
            }
        }
        """
        try:
            with open(self.conditions_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Conditions file not found: {self.conditions_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in conditions file: {e}")
        
        # Parse blocks
        for block_name, block_data in config.get("blocks", {}).items():
            conditions = []
            
            for cond_data in block_data.get("conditions", []):
                try:
                    condition = Condition(
                        condition_id=cond_data["condition_id"],
                        frequency=cond_data["frequency"],
                        trial_type=cond_data["trial_type"],
                        block=block_name,
                        parameters=cond_data.get("parameters", {}),
                        metadata=cond_data.get("metadata", {})
                    )
                    conditions.append(condition)
                    self.all_conditions.append(condition)
                except (KeyError, ValueError) as e:
                    self.logger.warning(f"Skipping invalid condition: {e}")
            
            block = Block(
                name=block_name,
                description=block_data.get("description", ""),
                conditions=conditions,
                progression_rules=config.get("progression_rules", {})
            )
            self.blocks[block_name] = block
        
        self.logger.info(
            f"Loaded {len(self.all_conditions)} conditions "
            f"across {len(self.blocks)} blocks"
        )
    
    def get_next_condition(self) -> Condition:
        """
        Select next condition using weighted probability.
        
        Uses frequency weights from current block to select condition.
        
        Returns:
            Condition object for this trial
            
        Raises:
            ValueError: If current block has no conditions
        """
        current_block = self.blocks[self.current_block_name]
        
        if not current_block.conditions:
            raise ValueError(f"Block '{self.current_block_name}' has no conditions")
        
        # Extract conditions and frequencies for this block
        conditions = current_block.conditions
        frequencies = [c.frequency for c in conditions]
        
        # Normalize frequencies to probabilities
        total_freq = sum(frequencies)
        probabilities = [f / total_freq for f in frequencies]
        
        # Weighted random selection
        selected_condition = random.choices(conditions, weights=probabilities, k=1)[0]
        
        # Track selection
        self.condition_history.append(selected_condition)
        
        self.logger.debug(
            f"Selected condition {selected_condition.condition_id} "
            f"(type: {selected_condition.trial_type}) "
            f"from block '{self.current_block_name}'"
        )
        
        return selected_condition
    
    def record_trial_outcome(self, error_code: str = "correct", metadata: Dict = None):
        """
        Record trial outcome for block progression logic.
        
        Args:
            error_code: "correct", "no_response", "broke_fixation", etc.
            metadata: Optional additional metadata to store
        """
        if not self.condition_history:
            self.logger.warning("No condition history - trial outcome not recorded")
            return
        
        trial_record = {
            "trial_number": len(self.trial_history) + 1,
            "condition_id": self.condition_history[-1].condition_id,
            "block": self.current_block_name,
            "error_code": error_code,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.trial_history.append(trial_record)
        
        # Update block trial counts
        if self.current_block_name not in self.block_trial_count:
            self.block_trial_count[self.current_block_name] = 0
            self.block_error_count[self