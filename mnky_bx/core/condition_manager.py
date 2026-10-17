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
            self.block_error_count[self.current_block_name] = 0
        
        self.block_trial_count[self.current_block_name] += 1
        
        if error_code != "correct":
            self.block_error_count[self.current_block_name] += 1
        
        self.logger.debug(
            f"Trial {trial_record['trial_number']}: "
            f"{error_code} in block '{self.current_block_name}'"
        )
        
        # Check if block progression rules are met
        self.check_block_progression()
    
    def check_block_progression(self) -> bool:
        """
        Evaluate if current block should advance to next.
        
        Checks:
        - Minimum trials completed
        - Performance threshold met
        
        Returns:
            True if block was advanced
        """
        current_block = self.blocks[self.current_block_name]
        rules = current_block.progression_rules
        
        trials_in_block = self.block_trial_count.get(self.current_block_name, 0)
        min_trials = rules.get("min_trials_per_block", 50)
        
        # Check minimum trials
        if trials_in_block < min_trials:
            return False
        
        # Check performance threshold
        if "performance_threshold" in rules:
            threshold = rules["performance_threshold"]
            errors = self.block_error_count.get(self.current_block_name, 0)
            correct_trials = trials_in_block - errors
            performance = correct_trials / trials_in_block if trials_in_block > 0 else 0
            
            self.logger.debug(
                f"Block performance: {performance:.2f} "
                f"(threshold: {threshold}, trials: {trials_in_block})"
            )
            
            if performance < threshold:
                return False  # Not ready yet
        
        # Advance to next block
        next_block_name = self.get_next_block_name()
        if next_block_name:
            self.logger.info(
                f"Block progression: "
                f"'{self.current_block_name}' -> '{next_block_name}' "
                f"(trials: {trials_in_block})"
            )
            
            # Log transition
            self.block_transition_log.append({
                "from_block": self.current_block_name,
                "to_block": next_block_name,
                "trial_number": len(self.trial_history),
                "timestamp": datetime.now().isoformat()
            })
            
            self.current_block_name = next_block_name
            self.block_trial_count[self.current_block_name] = 0
            self.block_error_count[self.current_block_name] = 0
            return True
        
        return False
    
    def should_continue_session(self) -> bool:
        """Check if there are more blocks to run"""
        return self.current_block_name is not None
    
    def get_current_block(self) -> Block:
        """Get current block object"""
        return self.blocks[self.current_block_name]
    
    def get_first_block_name(self) -> str:
        """Get name of first block"""
        return next(iter(self.blocks.keys())) if self.blocks else None
    
    def get_next_block_name(self) -> Optional[str]:
        """Get name of next block in sequence"""
        block_names = list(self.blocks.keys())
        if self.current_block_name not in block_names:
            return None
        
        current_index = block_names.index(self.current_block_name)
        
        if current_index + 1 < len(block_names):
            return block_names[current_index + 1]
        
        return None  # No more blocks
    
    def get_session_summary(self) -> Dict:
        """Get summary statistics for session"""
        total_trials = len(self.trial_history)
        correct_trials = sum(1 for t in self.trial_history if t["error_code"] == "correct")
        
        # Block statistics
        block_stats = {}
        for block_name in self.blocks.keys():
            trials_in_block = sum(
                1 for t in self.trial_history if t["block"] == block_name
            )
            if trials_in_block > 0:
                correct_in_block = sum(
                    1 for t in self.trial_history 
                    if t["block"] == block_name and t["error_code"] == "correct"
                )
                block_stats[block_name] = {
                    "total_trials": trials_in_block,
                    "correct": correct_in_block,
                    "accuracy": correct_in_block / trials_in_block
                }
        
        return {
            "total_trials": total_trials,
            "correct_trials": correct_trials,
            "accuracy": correct_trials / total_trials if total_trials > 0 else 0,
            "blocks_completed": len(set(t["block"] for t in self.trial_history)),
            "current_block": self.current_block_name,
            "block_statistics": block_stats,
            "block_transitions": self.block_transition_log,
            "trial_history": self.trial_history
        }
    
    def get_trial_history_by_block(self, block_name: str) -> List[Dict]:
        """Get all trials from specific block"""
        return [t for t in self.trial_history if t["block"] == block_name]
    
    def export_trial_history_json(self, output_path: Path):
        """Export trial history to JSON file"""
        summary = self.get_session_summary()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Trial history exported to {output_path}")