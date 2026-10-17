#  tests/test_mock_hardware.py

"""
Unit Tests for Mock Hardware Controller

Tests basic functionality, button input, motor control, and error handling.
"""

import pytest
import time
import logging
from typing import List

from mnky_bx.hardware.mock_controller import MockHardwareController
from tests.fixtures.mock_hardware import MockHardwareFactory, MockHardwareScenarios

logger = logging.getLogger(__name__)


class TestMockHardwareBasics:
    """Test basic mock hardware functionality"""
    
    def test_connect_disconnect(self):
        """Test connect/disconnect"""
        controller = MockHardwareFactory.create_simple()
        
        assert not controller.is_connected
        assert controller.connect()
        assert controller.is_connected
        assert controller.disconnect()
        assert not controller.is_connected
    
    def test_health_check(self):
        """Test health check"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        status = controller.health_check()
        
        assert status["connected"]
        assert status["buttons"]
        assert status["leds"]
        assert status["motor"]
        assert len(status["errors"]) == 0
    
    def test_health_check_disconnected(self):
        """Test health check when disconnected"""
        controller = MockHardwareFactory.create_simple()
        
        status = controller.health_check()
        
        assert not status["connected"]
        assert "Not connected" in status["errors"]


class TestLEDControl:
    """Test LED control"""
    
    def test_led_on_off(self):
        """Test turning LED on and off"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        # Initially off
        assert controller.get_led_state("left") is False
        
        # Turn on
        assert controller.set_led("left", True)
        assert controller.get_led_state("left") is True
        
        # Turn off
        assert controller.set_led("left", False)
        assert controller.get_led_state("left") is False
    
    def test_led_both(self):
        """Test controlling both LEDs"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        controller.set_led("both", True)
        assert controller.get_led_state("left") is True
        assert controller.get_led_state("right") is True
        
        controller.set_led("both", False)
        assert controller.get_led_state("left") is False
        assert controller.get_led_state("right") is False
    
    def test_led_blink(self):
        """Test LED blinking"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        start_time = time.time()
        controller.blink_led("left", count=3, duration_ms=10)
        elapsed = time.time() - start_time
        
        # Should take ~60ms (3 on/off cycles * 20ms)
        assert elapsed >= 0.05


class TestMotorControl:
    """Test motor control"""
    
    def test_motor_home(self):
        """Test motor homing"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        assert controller.home_motor()
        assert controller.get_motor_position() == 0.0
        assert not controller.is_motor_moving()
    
    def test_motor_move(self):
        """Test motor movement"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        controller.home_motor()
        
        assert controller.move_motor(5.0, wait=True)
        assert controller.get_motor_position() == 5.0
    
    def test_motor_move_invalid_position(self):
        """Test motor with invalid position"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        # Too high
        assert not controller.move_motor(15.0)
        
        # Negative
        assert not controller.move_motor(-1.0)
    
    def test_motor_async_movement(self):
        """Test non-blocking motor movement"""
        controller = MockHardwareFactory.create_fast()
        controller.connect()
        
        # Start movement without waiting
        assert controller.move_motor(5.0, wait=False)
        assert controller.is_motor_moving()
        
        # Wait for completion
        time.sleep(0.05)
        assert controller.get_motor_position() == 5.0


class TestButtonInput:
    """Test button input"""
    
    def test_button_listener_start_stop(self):
        """Test starting and stopping button listener"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        def dummy_callback(button, event):
            pass
        
        assert controller.start_button_listener(dummy_callback)
        assert controller.button_listening
        
        assert controller.stop_button_listener()
        assert not controller.button_listening
    
    def test_button_press_callback(self):
        """Test button press callback"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        button_presses = []
        
        def callback(button, event):
            button_presses.append((button, event))
        
        controller.start_button_listener(callback)
        
        # Inject button press
        controller.inject_button_press("left", "pressed")
        
        # Wait for callback
        time.sleep(0.05)
        
        assert len(button_presses) == 1
        assert button_presses[0] == ("left", "pressed")
        
        controller.stop_button_listener()
    
    def test_button_sequence(self):
        """Test multiple button presses"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        button_presses = []
        
        def callback(button, event):
            button_presses.append((button, event))
        
        controller.start_button_listener(callback)
        
        # Inject sequence
        controller.inject_button_sequence([
            ("left", "pressed"),
            ("left", "released"),
            ("right", "pressed"),
            ("right", "released"),
        ])
        
        # Wait for callbacks
        time.sleep(0.1)
        
        assert len(button_presses) == 4
        assert button_presses[0] == ("left", "pressed")
        assert button_presses[1] == ("left", "released")
        assert button_presses[2] == ("right", "pressed")
        assert button_presses[3] == ("right", "released")
        
        controller.stop_button_listener()
    
    def test_button_statistics(self):
        """Test button press statistics"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        def callback(button, event):
            pass
        
        controller.start_button_listener(callback)
        
        controller.inject_button_press("left", "pressed")
        controller.inject_button_press("left", "pressed")
        controller.inject_button_press("right", "pressed")
        
        time.sleep(0.1)
        
        stats = controller.get_stats()
        assert stats.button_presses["left"] == 2
        assert stats.button_presses["right"] == 1
        
        controller.stop_button_listener()


class TestEventRecording:
    """Test event recording and logging"""
    
    def test_event_recording(self):
        """Test that events are recorded"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        controller.set_led("left", True)
        controller.home_motor()
        controller.move_motor(5.0)
        
        events = controller.get_event_log()
        
        assert len(events) > 0
        event_types = [e.event_type for e in events]
        assert "connect" in event_types
        assert "led_set" in event_types
        assert "motor_homed" in event_types
        assert "motor_moved" in event_types
    
    def test_get_events_by_type(self):
        """Test filtering events by type"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        controller.set_led("left", True)
        controller.set_led("right", True)
        controller.set_led("left", False)
        
        led_events = controller.get_events_by_type("led_set")
        
        assert len(led_events) == 3
    
    def test_clear_event_log(self):
        """Test clearing event log"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        controller.set_led("left", True)
        
        assert len(controller.get_event_log()) > 0
        
        controller.clear_event_log()
        
        assert len(controller.get_event_log()) == 0


class TestFailureInjection:
    """Test failure injection for error handling"""
    
    def test_inject_motor_home_failure(self):
        """Test injecting motor home failure"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        controller.inject_failure("motor_home")
        
        result = controller.home_motor()
        assert result is False
        
        assert controller.should_have_failed("motor_home")
    
    def test_inject_motor_move_failure(self):
        """Test injecting motor move failure"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        controller.inject_failure("motor_move")
        
        result = controller.move_motor(5.0)
        assert result is False
        
        assert controller.should_have_failed("motor_move")
    
    def test_failure_only_affects_next_operation(self):
        """Test that injected failure only affects next operation"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        controller.inject_failure("motor_home")
        
        # First call fails
        assert not controller.home_motor()
        
        # Second call succeeds
        assert controller.home_motor()


class TestStatistics:
    """Test statistics tracking"""
    
    def test_command_statistics(self):
        """Test command success/failure statistics"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        controller.set_led("left", True)
        controller.set_led("right", True)
        
        stats = controller.get_stats()
        
        assert stats.total_commands == 2
        assert stats.successful_commands == 2
        assert stats.failed_commands == 0
    
    def test_motor_statistics(self):
        """Test motor movement statistics"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        controller.home_motor()
        controller.move_motor(5.0)
        controller.move_motor(10.0)
        
        stats = controller.get_stats()
        
        assert stats.motor_movements == 3
    
    def test_reset_statistics(self):
        """Test resetting statistics"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        controller.set_led("left", True)
        controller.home_motor()
        
        stats_before = controller.get_stats()
        assert stats_before.total_commands > 0
        
        controller.reset_stats()
        
        stats_after = controller.get_stats()
        assert stats_after.total_commands == 0
        assert stats_after.motor_movements == 0


class TestScenarios:
    """Test realistic scenarios"""
    
    def test_button_press_left_then_right(self):
        """Test scenario: button sequence"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        button_presses = []
        
        def callback(button, event):
            button_presses.append(button)
        
        controller.start_button_listener(callback)
        
        MockHardwareScenarios.button_sequence_left_then_right(controller)
        
        time.sleep(0.1)
        
        assert len(button_presses) == 4
        assert button_presses[0] == "left"
        assert button_presses[2] == "right"
        
        controller.stop_button_listener()
    
    def test_reward_delivery(self):
        """Test scenario: reward delivery sequence"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        MockHardwareScenarios.reward_sequence(controller)
        
        assert controller.get_motor_position() == 5.0
    
    def test_led_feedback(self):
        """Test scenario: LED feedback"""
        controller = MockHardwareFactory.create_simple()
        controller.connect()
        
        MockHardwareScenarios.led_blink_sequence(controller)
        
        # LEDs should be off after blinking
        assert not controller.get_led_state("left")
        assert not controller.get_led_state("right")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
