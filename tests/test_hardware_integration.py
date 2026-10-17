# tests/test_hardware_integration.py 

"""
Hardware Integration Tests

Tests interactions between launcher, conditions, and hardware.
"""

import pytest
import time
from pathlib import Path

from mnky_bx.core.condition_manager import ConditionManager
from mnky_bx.core.kiosk_manager import KioskManager
from mnky_bx.hardware.mock_controller import MockHardwareController
from tests.fixtures.mock_hardware import MockHardwareFactory


class TestHardwareWithConditions:
    """Test hardware integration with condition manager"""
    
    def test_trial_execution_with_mock_hardware(self, project_root):
        """Test a complete trial execution with mock hardware"""
        # Setup
        hardware = MockHardwareFactory.create_simple()
        assert hardware.connect()
        
        # Button callback tracking
        responses = []
        def button_callback(button, event):
            responses.append(button)
        
        hardware.start_button_listener(button_callback)
        
        # Simulate trial
        hardware.home_motor()
        hardware.set_led("left", True)
        
        # User presses button
        hardware.inject_button_press("left", "pressed")
        time.sleep(0.05)
        
        # Show outcome
        hardware.set_led("left", False)
        hardware.move_motor(5.0)  # Deliver reward
        
        # Verify
        assert len(responses) == 1
        assert responses[0] == "left"
        assert hardware.get_motor_position() == 5.0
        
        # Cleanup
        hardware.stop_button_listener()
        hardware.disconnect()
    
    def test_multiple_trials_with_mock_hardware(self):
        """Test multiple consecutive trials"""
        hardware = MockHardwareFactory.create_simple()
        hardware.connect()
        
        responses = []
        def callback(button, event):
            responses.append(button)
        
        hardware.start_button_listener(callback)
        
        # Simulate 5 trials
        for trial_num in range(5):
            # Trial setup
            hardware.home_motor()
            hardware.set_led("left", True)
            hardware.set_led("right", True)
            
            # User chooses
            if trial_num % 2 == 0:
                hardware.inject_button_press("left", "pressed")
            else:
                hardware.inject_button_press("right", "pressed")
            
            time.sleep(0.05)
            
            # Feedback
            hardware.set_led("left", False)
            hardware.set_led("right", False)
            
            # Reward
            position = 5.0 if trial_num % 2 == 0 else 7.0
            hardware.move_motor(position)
        
        # Verify
        stats = hardware.get_stats()
        assert stats.motor_movements >= 5
        assert len(responses) == 5
        
        hardware.stop_button_listener()
        hardware.disconnect()


class TestHardwareWithKioskManager:
    """Test hardware integration with kiosk manager"""
    
    def test_session_initialization_with_hardware(self, project_root):
        """Test session initialization and hardware setup"""
        # Create kiosk manager
        config_path = project_root / "config" / "kiosk_config.json"
        if not config_path.exists():
            pytest.skip("kiosk_config.json not found")
        
        manager = KioskManager(config_path, project_root)
        
        # Create mock hardware
        hardware = MockHardwareFactory.create_simple()
        hardware.connect()
        
        # Verify hardware is ready
        health = hardware.health_check()
        assert health["connected"]
        assert health["motor"]
        
        # Initialize session
        session_path = manager.initialize_session(
            subject_id="subject_id_01",
            experiment_name="gambling_experiment"
        )
        
        assert session_path.exists()
        assert (session_path / "session_info.json").exists()
        
        hardware.disconnect()


class TestHardwareErrorRecovery:
    """Test hardware error recovery"""
    
    def test_recovery_from_motor_failure(self):
        """Test recovery from motor failure"""
        hardware = MockHardwareFactory.create_simple()
        hardware.connect()
        
        # Motor fails on first attempt
        hardware.inject_failure("motor_home")
        assert not hardware.home_motor()
        
        # Recovery: try again
        assert hardware.home_motor()
        assert hardware.get_motor_position() == 0.0
        
        hardware.disconnect()
    
    def test_health_check_after_operation(self):
        """Test health check after various operations"""
        hardware = MockHardwareFactory.create_simple()
        hardware.connect()
        
        # Do various operations
        hardware.set_led("left", True)
        hardware.home_motor()
        hardware.move_motor(5.0)
        
        # Check health
        health = hardware.health_check()
        assert health["connected"]
        assert len(health["errors"]) == 0
        
        hardware.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
    