# tests/conftest.py 

"""
Pytest Configuration and Fixtures

Provides shared fixtures for all tests.
"""

import pytest
import logging
from pathlib import Path

from mnky_bx.hardware.mock_controller import MockHardwareController
from tests.fixtures.mock_hardware import MockHardwareFactory

# Setup logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)


@pytest.fixture
def mock_hardware_simple():
    """Fixture: simple mock hardware"""
    controller = MockHardwareFactory.create_simple()
    controller.connect()
    yield controller
    controller.disconnect()


@pytest.fixture
def mock_hardware_fast():
    """Fixture: fast mock hardware"""
    controller = MockHardwareFactory.create_fast()
    controller.connect()
    yield controller
    controller.disconnect()


@pytest.fixture
def mock_hardware_with_buttons(mock_hardware_simple):
    """Fixture: mock hardware with button listener"""
    button_presses = []
    
    def callback(button, event):
        button_presses.append((button, event))
    
    mock_hardware_simple.start_button_listener(callback)
    
    yield mock_hardware_simple, button_presses
    
    mock_hardware_simple.stop_button_listener()


@pytest.fixture
def project_root():
    """Fixture: project root path"""
    return Path(__file__).parent.parent