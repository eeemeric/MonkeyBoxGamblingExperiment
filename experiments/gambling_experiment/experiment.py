# mnky_bx/experiments/gambling_experiment/experiment.py
"""
Gambling Experiment Implementation

This experiment:
- Loads conditions from conditions.json via ConditionManager
- Uses Scene-based trial structure from scenes.py
- Implements only stimulus drawing and outcome evaluation

Subjects choose between:
- Sure option: guaranteed reward/loss
- Gamble option: probabilistic outcome
"""

import pygame
import random
from mnky_bx.core.experiment_base import ExperimentBase
from experiments.gambling_experiment.scenes import GamblingScenes
import logging

logger = logging.getLogger(__name__)


class GamblingExperiment(ExperimentBase):
    """
    Gambling decision-making task.
    
    Subjects choose between:
    - Sure option: guaranteed reward/loss
    - Gamble option: probabilistic outcome
    
    Conditions are loaded from conditions.json.
    Trial flow is defined in scenes.py.
    """
    
    def __init__(self, config, logger_instance, database, hardware, conditions_file=None):
        """
        Initialize gambling experiment.
        
        Args:
            config: Experiment config (from config.json)
            logger_instance: ExperimentLogger
            database: Database manager
            hardware: HardwareController
            conditions_file: Optional path to conditions.json
        """
        super().__init__(config, logger_instance, database, hardware, conditions_file)
        
        # Load scene library
        self.scene_lib = GamblingScenes(self)
        
        # Display setup
        self.screen_width = config.get("display", {}).get("width", 1920)
        self.screen_height = config.get("display", {}).get("height", 1080)
        
        # Stimulus parameters
        self.circle_radius = config.get("stimulus", {}).get("circle_radius_pixels", 100)
        self.circle_left_x = self.screen_width // 4
        self.circle_right_x = 3 * self.screen_width // 4
        self.circle_y = self.screen_height // 2
        
        # Colors
        self.colors = {
            "left": (0, 128, 0),          # Green
            "right": (0, 0, 131),         # Blue
            "fixation": (255, 255, 255),  # White
            "reward": (255, 215, 0),      # Gold
            "error": (255, 0, 0),         # Red
            "background": (0, 0, 0),      # Black
        }
        
        self.logger.info("GamblingExperiment initialized")
    
    def get_scene(self, scene_name: str):
        """Retrieve scene from library"""
        return self.scene_lib.get_scene(scene_name)
    
    def draw_blank(self):
        """Draw blank screen"""
        screen = pygame.display.get_surface()
        if screen:
            screen.fill(self.colors["background"])
    
    def draw_fixation_point(self):
        """Draw central fixation point"""
        screen = pygame.display.get_surface()
        if not screen:
            return
        
        screen.fill(self.colors["background"])
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        pygame.draw.circle(
            screen,
            self.colors["fixation"],
            (center_x, center_y),
            20
        )
    
    def draw_circles(self, parameters: dict):
        """
        Draw left and right stimulus circles.
        
        Args:
            parameters: Condition parameters containing option details
        """
        screen = pygame.display.get_surface()
        if not screen:
            return
        
        screen.fill(self.colors["background"])
        
        pygame.draw.circle(
            screen,
            self.colors["left"],
            (self.circle_left_x, self.circle_y),
            self.circle_radius
        )
        pygame.draw.circle(
            screen,
            self.colors["right"],
            (self.circle_right_x, self.circle_y),
            self.circle_radius
        )
    
    def draw_reward_feedback(self):
        """Draw reward/win feedback"""
        screen = pygame.display.get_surface()
        if screen:
            screen.fill(self.colors["reward"])
    
    def draw_error_feedback(self):
        """Draw error/loss feedback"""
        screen = pygame.display.get_surface()
        if screen:
            screen.fill(self.colors["error"])
    
    def evaluate_trial_outcome(self):
        """
        Determine if trial was successful based on choice and condition.
        
        In gambling task:
        - Any response is technically "correct" (no task errors)
        - Success depends on probabilistic outcome of chosen option
        
        Sets:
        - self.trial_success (bool)
        - self.trial_error (str, "correct" if completed)
        """
        condition = self.current_condition
        
        # Check if choice was made
        if self.choice is None:
            self.trial_success = False
            return
        
        # Determine which option was chosen
        if self.choice == "left":
            chosen_option = condition.parameters.get("left_option", {})
        else:
            chosen_option = condition.parameters.get("right_option", {})
        
        # Evaluate probabilistic outcome
        prob_win = chosen_option.get("prob_win", 0.0)
        self.trial_success = (random.random() < prob_win)
        
        self.logger.debug(
            f"Outcome: choice={self.choice}, "
            f"prob_win={prob_win}, success={self.trial_success}"
        )


if __name__ == "__main__":
    # For standalone testing
    logger.info("GamblingExperiment module loaded successfully")