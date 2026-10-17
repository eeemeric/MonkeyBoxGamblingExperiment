# mnky_bx/experiments/gambling_experiment/scenes.py
"""
Scene Definitions for Gambling Experiment

Scenes are reusable trial phases that can be chained together.
Each scene knows how to render itself and detect transition conditions.

A Scene object has:
- name: str
- duration_ms: int
- on_enter(): Called when scene starts
- on_update(elapsed_ms): Called each frame
- should_transition(): Returns True to move to next scene
- on_exit(): Optional cleanup
"""

import pygame
from dataclasses import dataclass
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Scene:
    """Definition of a trial phase/scene"""
    name: str
    duration_ms: int
    on_enter: Callable
    on_update: Callable
    should_transition: Callable
    on_exit: Optional[Callable] = None


class GamblingScenes:
    """
    Scene library for gambling experiment.
    
    Scenes are pure functions/methods that know how to:
    1. Render a state
    2. Check if transition conditions are met
    3. Handle errors gracefully
    
    Example:
        scenes = GamblingScenes(experiment)
        scene = scenes.get_scene("stimulus")
        scene.on_enter()
    """
    
    def __init__(self, experiment):
        """
        Args:
            experiment: Parent ExperimentBase instance
        """
        self.exp = experiment
        
        # Scene definitions
        self.scenes = {
            "iti": Scene(
                name="Inter-Trial Interval",
                duration_ms=self.exp.config.get("timing", {}).get("iti_ms", 1000),
                on_enter=self.iti_enter,
                on_update=self.iti_update,
                should_transition=self.iti_should_transition,
            ),
            "fixation": Scene(
                name="Fixation Hold",
                duration_ms=500,
                on_enter=self.fixation_enter,
                on_update=self.fixation_update,
                should_transition=self.fixation_should_transition,
            ),
            "stimulus": Scene(
                name="Show Stimulus",
                duration_ms=1000,
                on_enter=self.stimulus_enter,
                on_update=self.stimulus_update,
                should_transition=self.stimulus_should_transition,
            ),
            "response": Scene(
                name="Wait for Response",
                duration_ms=self.exp.config.get("timing", {}).get("max_response_time_ms", 5000),
                on_enter=self.response_enter,
                on_update=self.response_update,
                should_transition=self.response_should_transition,
            ),
            "outcome": Scene(
                name="Reveal Outcome",
                duration_ms=self.exp.config.get("timing", {}).get("outcome_display_ms", 500),
                on_enter=self.outcome_enter,
                on_update=self.outcome_update,
                should_transition=self.outcome_should_transition,
            ),
            "reward": Scene(
                name="Deliver Reward",
                duration_ms=500,
                on_enter=self.reward_enter,
                on_update=self.reward_update,
                should_transition=self.reward_should_transition,
            ),
        }
    
    def get_scene(self, scene_name: str) -> Optional[Scene]:
        """Retrieve scene by name"""
        return self.scenes.get(scene_name)
    
    # ===== ITI Scene =====
    def iti_enter(self):
        """Start ITI: blank screen"""
        self.exp.draw_blank()
        pygame.display.flip()
    
    def iti_update(self, elapsed_ms: int):
        """ITI update (nothing to do)"""
        pass
    
    def iti_should_transition(self) -> bool:
        """Always transition after ITI duration"""
        return True
    
    # ===== Fixation Scene =====
    def fixation_enter(self):
        """Show fixation point"""
        self.exp.draw_fixation_point()
        pygame.display.flip()
        self.fixation_hold_start = pygame.time.get_ticks()
    
    def fixation_update(self, elapsed_ms: int):
        """Redraw fixation point"""
        self.exp.draw_fixation_point()
        pygame.display.flip()
    
    def fixation_should_transition(self) -> bool:
        """Transition if fixation held long enough or error"""
        required_hold_ms = 500
        current_hold_ms = pygame.time.get_ticks() - self.fixation_hold_start
        
        # Check for break fixation (error)
        if self.exp.motion_detected and current_hold_ms < required_hold_ms:
            self.exp.trial_error = "broke_fixation"
            logger.debug("Fixation broken")
            return True
        
        if current_hold_ms >= required_hold_ms:
            return True
        
        return False
    
    # ===== Stimulus Scene =====
    def stimulus_enter(self):
        """Show stimulus options (left and right circles)"""
        condition = self.exp.current_condition
        self.exp.draw_circles(condition.parameters)
        pygame.display.flip()
    
    def stimulus_update(self, elapsed_ms: int):
        """Redraw stimulus"""
        condition = self.exp.current_condition
        self.exp.draw_circles(condition.parameters)
        pygame.display.flip()
    
    def stimulus_should_transition(self) -> bool:
        """Always transition after stimulus duration"""
        return True
    
    # ===== Response Scene =====
    def response_enter(self):
        """Wait for button press"""
        self.exp.choice = None
        self.exp.response_time_start = pygame.time.get_ticks()
    
    def response_update(self, elapsed_ms: int):
        """Redraw stimulus while waiting"""
        condition = self.exp.current_condition
        self.exp.draw_circles(condition.parameters)
        pygame.display.flip()
    
    def response_should_transition(self) -> bool:
        """Transition if response made or timeout"""
        if self.exp.choice is not None:
            return True
        
        elapsed = pygame.time.get_ticks() - self.exp.response_time_start
        if elapsed > self.exp.scenes["response"].duration_ms:
            self.exp.trial_error = "no_response"
            logger.debug("Response timeout")
            return True
        
        return False
    
    # ===== Outcome Scene =====
    def outcome_enter(self):
        """Show win/loss feedback"""
        if self.exp.trial_success:
            self.exp.draw_reward_feedback()
        else:
            self.exp.draw_error_feedback()
        pygame.display.flip()
    
    def outcome_update(self, elapsed_ms: int):
        """Redraw outcome"""
        if self.exp.trial_success:
            self.exp.draw_reward_feedback()
        else:
            self.exp.draw_error_feedback()
        pygame.display.flip()
    
    def outcome_should_transition(self) -> bool:
        """Always transition after outcome duration"""
        return True
    
    # ===== Reward Scene =====
    def reward_enter(self):
        """Deliver physical reward"""
        if self.exp.trial_success:
            reward_amount = self.exp.current_condition.parameters.get("reward_magnitude", 5)
            self.exp.hardware.move_motor(float(reward_amount), 500)
    
    def reward_update(self, elapsed_ms: int):
        """Wait for motor to complete"""
        pass
    
    def reward_should_transition(self) -> bool:
        """Transition when motor finishes"""
        if not hasattr(self.exp.hardware, 'is_motor_moving'):
            return True
        return not self.exp.hardware.is_motor_moving()