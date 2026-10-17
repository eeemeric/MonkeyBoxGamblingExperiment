# mnky_bx/core/experiment_base.py

"""
Base Experiment Class - Pure Trial Execution

Responsibilities:
- Orchestrate trial flow using scenes
- Delegate condition selection to ConditionManager
- Handle stimulus drawing (implemented by subclass)
- Track trial metadata
- Interact with hardware/database/logging
"""

import pygame
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ExperimentBase:
    """
    Base class for all experiments.
    
    Subclasses must implement:
    - get_scene(scene_name: str) -> Scene
    - evaluate_trial_outcome()
    - And optionally override scene methods
    
    The ConditionManager handles:
    - Condition loading and selection
    - Block progression
    - Trial history tracking
    
    Usage:
        class MyExperiment(ExperimentBase):
            def __init__(self, config, logger, database, hardware):
                super().__init__(config, logger, database, hardware)
                self.scenes = MyScenes(self)
            
            def get_scene(self, scene_name: str):
                return self.scenes.get_scene(scene_name)
            
            def evaluate_trial_outcome(self):
                # Implement outcome logic
                pass
    """
    
    def __init__(
        self,
        config: dict,
        logger_instance,
        database,
        hardware,
        conditions_file: Path = None
    ):
        """
        Initialize experiment.
        
        Args:
            config: Experiment config (from config.json)
            logger_instance: ExperimentLogger instance
            database: Database manager
            hardware: HardwareController (Arduino/Feather)
            conditions_file: Path to conditions.json (defaults to config value)
        """
        self.config = config
        self.logger = logger_instance
        self.database = database
        self.hardware = hardware
        
        # Initialize condition manager (SEPARATE RESPONSIBILITY)
        from mnky_bx.core.condition_manager import ConditionManager
        
        if conditions_file is None:
            conditions_file = Path(config.get("conditions_file", "conditions.json"))
        
        self.condition_manager = ConditionManager(
            conditions_file,
            logger_instance=self.logger
        )
        
        # Trial state
        self.trial_number = 0
        self.current_condition = None
        self.choice = None
        self.trial_error = "correct"
        self.trial_success = False
        self.response_time_start = None
        self.motion_detected = False
        
        self.logger.info(f"ExperimentBase initialized")
    
    def run_session(self):
        """
        Main session loop.
        
        Continues until all blocks are complete or session is terminated.
        """
        pygame.init()
        
        try:
            self.logger.info("Starting experiment session")
            
            while self.condition_manager.should_continue_session():
                try:
                    self.run_trial()
                    self.trial_number += 1
                except Exception as e:
                    self.logger.error(f"Trial error: {e}", exc_info=True)
                    self.trial_error = "exception"
                    self.condition_manager.record_trial_outcome("exception")
        
        except KeyboardInterrupt:
            self.logger.info("Session interrupted by user")
        
        finally:
            pygame.quit()
            self.log_session_summary()
    
    def run_trial(self):
        """
        Execute single trial by chaining scenes.
        
        Flow:
        1. Select condition (via ConditionManager)
        2. Execute scene sequence
        3. Evaluate trial outcome
        4. Record result
        5. Check block progression
        """
        # Get next condition
        self.current_condition = self.condition_manager.get_next_condition()
        self.trial_error = "correct"
        self.choice = None
        self.trial_success = False
        
        # Log trial start
        self.logger.info(
            f"Trial {self.trial_number + 1} start: "
            f"condition {self.current_condition.condition_id} "
            f"({self.current_condition.trial_type})"
        )
        
        # Execute scene sequence
        scene_sequence = [
            "iti",
            "fixation",
            "stimulus",
            "response",
            "outcome",
            "reward"
        ]
        scenes_executed = []
        
        for scene_name in scene_sequence:
            scene = self.get_scene(scene_name)
            if scene is None:
                self.logger.warning(f"Scene '{scene_name}' not found")
                continue
            
            self.execute_scene(scene)
            scenes_executed.append(scene_name)
            
            # Stop if error occurred
            if self.trial_error != "correct":
                self.logger.debug(f"Trial stopped at scene '{scene_name}': {self.trial_error}")
                break
        
        # Evaluate trial outcome
        self.evaluate_trial_outcome()
        
        # Record trial
        self.database.record_trial(
            trial_number=self.trial_number,
            condition=self.current_condition,
            choice=self.choice,
            success=self.trial_success,
            error_code=self.trial_error,
            response_time=self.get_response_time(),
            scenes_executed=scenes_executed
        )
        
        # Record outcome in condition manager (for block progression)
        self.condition_manager.record_trial_outcome(
            self.trial_error,
            metadata={
                "choice": self.choice,
                "success": self.trial_success,
                "response_time": self.get_response_time()
            }
        )
        
        self.logger.info(
            f"Trial {self.trial_number + 1} end: "
            f"{self.trial_error} (success: {self.trial_success})"
        )
    
    def execute_scene(self, scene):
        """
        Execute a single scene.
        
        Args:
            scene: Scene object with on_enter, on_update, should_transition methods
        """
        scene.on_enter()
        
        start_time = pygame.time.get_ticks()
        while True:
            elapsed = pygame.time.get_ticks() - start_time
            
            # Check timeout
            if elapsed > scene.duration_ms:
                break
            
            # Update scene
            scene.on_update(elapsed)
            
            # Check transition condition
            if scene.should_transition():
                break
            
            pygame.time.delay(10)  # Don't hammer CPU
        
        if hasattr(scene, 'on_exit') and scene.on_exit:
            scene.on_exit()
    
    def get_scene(self, scene_name: str):
        """
        Get scene by name (implemented by subclass).
        
        Args:
            scene_name: Scene identifier (e.g., "iti", "stimulus", "response")
            
        Returns:
            Scene object or None if not found
        """
        raise NotImplementedError(
            "Subclass must implement get_scene(scene_name)"
        )
    
    def evaluate_trial_outcome(self):
        """
        Determine if trial was successful (implement in subclass).
        
        Must set:
        - self.trial_success (bool)
        - self.trial_error (str, default "correct")
        
        Called after all scenes execute.
        """
        raise NotImplementedError(
            "Subclass must implement evaluate_trial_outcome()"
        )
    
    def get_response_time(self) -> int:
        """
        Calculate response latency in milliseconds.
        
        Returns:
            Milliseconds since response window started, or -1 if not set
        """
        if self.response_time_start is None:
            return -1
        return pygame.time.get_ticks() - self.response_time_start
    
    def log_session_summary(self):
        """Log final session statistics"""
        summary = self.condition_manager.get_session_summary()
        
        self.logger.info(
            f"Session Summary: "
            f"{summary['total_trials']} trials, "
            f"{summary['accuracy']:.2%} accuracy, "
            f"{summary['blocks_completed']} blocks"
        )
        
        self.logger.info(f"Session summary:\n{summary}")