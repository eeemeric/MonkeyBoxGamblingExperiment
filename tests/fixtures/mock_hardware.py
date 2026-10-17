# tests/fixtures/mock_hardware.py 

"""
Mock Hardware Fixtures for Testing

Provides pre-configured mock hardware for common test scenarios.
"""

import logging
from mnky_bx.hardware.mock_controller import MockHardwareController

logger = logging.getLogger(__name__)


class MockHardwareFactory:
    """Factory for creating pre-configured mock hardware"""
    
    @staticmethod
    def create_simple() -> MockHardwareController:
        """Create simple mock hardware with default settings"""
        return MockHardwareController({})
    
    @staticmethod
    def create_fast() -> MockHardwareController:
        """Create fast mock hardware (minimal delays)"""
        return MockHardwareController({
            "motor_delay_ms": 10,
            "motor_max_position": 10.0
        })
    
    @staticmethod
    def create_slow() -> MockHardwareController:
        """Create slow mock hardware (long delays)"""
        return MockHardwareController({
            "motor_delay_ms": 2000,
            "motor_max_position": 10.0
        })


class MockHardwareScenarios:
    """Pre-configured test scenarios"""
    
    @staticmethod
    def button_press_left(controller: MockHardwareController):
        """Simulate user pressing left button"""
        controller.inject_button_press("left", "pressed")
    
    @staticmethod
    def button_press_right(controller: MockHardwareController):
        """Simulate user pressing right button"""
        controller.inject_button_press("right", "pressed")
    
    @staticmethod
    def button_sequence_left_then_right(controller: MockHardwareController):
        """Simulate: press left, release left, press right, release right"""
        controller.inject_button_sequence([
            ("left", "pressed"),
            ("left", "released"),
            ("right", "pressed"),
            ("right", "released"),
        ])
    
    @staticmethod
    def reward_sequence(controller: MockHardwareController):
        """Simulate: home, then deliver reward"""
        controller.home_motor()
        controller.move_motor(5.0)
    
    @staticmethod
    def button_held_left(controller: MockHardwareController):
        """Simulate: hold left button"""
        controller.inject_button_sequence([
            ("left", "pressed"),
            ("left", "held"),
            ("left", "released"),
        ])
    
    @staticmethod
    def led_blink_sequence(controller: MockHardwareController):
        """Simulate: blink LEDs"""
        controller.set_led("left", True)
        controller.set_led("right", False)
        controller.blink_led("both", count=3, duration_ms=100)
    
    @staticmethod
    def failure_motor_home(controller: MockHardwareController):
        """Simulate: motor home failure"""
        controller.inject_failure("motor_home")
        result = controller.home_motor()
        return result is False
    
    @staticmethod
    def failure_motor_move(controller: MockHardwareController):
        """Simulate: motor move failure"""
        controller.inject_failure("motor_move")
        result = controller.move_motor(5.0)
        return result is False