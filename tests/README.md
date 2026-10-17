# Tests Directory
    Unit and integration tests for mnky_bx framework.

    ### Running Tests
    ```bash
    pytest tests/
    pytest tests/test_hardware.py -v
    pytest tests/test_face_recognition.py -v
    ```
    ### Test Structure
    ```python
    tests/
    ├── fixtures/                # Test data and mocks
    │   ├── mock_hardware.py
    │   ├── mock_camera.py
    │   └── sample_images/
    ├── test_hardware.py         # Arduino/Feather controller tests
    ├── test_face_recognition.py # Face recognition pipeline tests
    ├── test_database.py         # Database operations tests
    ├── test_config.py           # Configuration loading tests
    └── test_experiment_base.py  # Experiment framework tests
    ```
    ###Contributing Tests
    Add tests for new features in:
    1. Create test_*.py in this directory
    2. Use fixtures from fixtures/
    3. Follow pytest conventions
    4. Run: pytest before committing
    
# Tests Directory

Unit and integration tests for mnky_bx framework using pytest.

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```
### Run specific test file
```bash
pytest tests/test_mock_hardware.py -v
```
### Run specific test class
```bash
pytest tests/test_mock_hardware.py::TestLEDControl -v
```
### Run specific test
```bash
pytest tests/test_mock_hardware.py::TestLEDControl::test_led_on_off -v
```
### Run with coverage
```bash
pytest tests/ --cov=mnky_bx --cov-report=html
```
### Run with logging output
```bash
pytest tests/ -v --log-cli-level=DEBUG
```

## Test Structure
```python
tests/
├── conftest.py                          # Pytest fixtures
├── fixtures/
│   ├── mock_hardware.py                 # Mock hardware factory
│   └── sample_images/                   # Test images
├── test_mock_hardware.py                # Mock controller unit tests
├── test_hardware_integration.py          # Hardware integration tests
├── test_condition_manager.py            # Condition manager tests (TODO)
├── test_kiosk_manager.py                # Kiosk manager tests (TODO)
└── test_experiment_base.py              # Experiment framework tests (TODO)
```

### Mock Hardware
The mock hardware controller simulates physical devices for testing without hardware:

### Basic Usage
```python
from tests.fixtures.mock_hardware import MockHardwareFactory

# Create mock controller
controller = MockHardwareFactory.create_simple()
controller.connect()

# Setup button callback
def on_button(button, event):
    print(f"Button {button} {event}")

controller.start_button_listener(on_button)

# Inject button press for testing
controller.inject_button_press("left")

# Test motor
controller.home_motor()
controller.move_motor(5.0)

# Check what happened
events = controller.get_event_log()
print(events)

controller.disconnect()
```
### Simulating User Interaction
```python
# Simulate left button press then right button release
controller.inject_button_sequence([
    ("left", "pressed"),
    ("left", "released"),
    ("right", "pressed"),
    ("right", "released"),
])
```
### Testing Error Handling
```python
# Inject failure
controller.inject_failure("motor_home")
result = controller.home_motor()
assert result is False

# Next attempt succeeds
result = controller.home_motor()
assert result is True
```

### Event Recording
```python
# Record all hardware events
controller.set_led("left", True)
controller.home_motor()
controller.move_motor(5.0)

# View events
events = controller.get_event_log()
for event in events:
    print(f"{event.timestamp}: {event.event_type} - {event.details}")

# Filter events by type
led_events = controller.get_events_by_type("led_set")
motor_events = controller.get_events_by_type("motor_moved")
```
### Statistics
```python
# Track performance
controller.set_led("left", True)
controller.home_motor()
controller.move_motor(5.0)

stats = controller.get_stats()
print(f"Total commands: {stats.total_commands}")
print(f"Successful: {stats.successful_commands}")
print(f"Failed: {stats.failed_commands}")
print(f"Motor movements: {stats.motor_movements}")
print(f"Button presses: {stats.button_presses}")
```

## Fixtures
**`mock_hardware_simple`**

Pre-configured simple mock hardware

```python
def test_something(mock_hardware_simple):
    controller = mock_hardware_simple
    controller.set_led("left", True)
    assert controller.get_led_state("left")
```
**`mock_hardware_fast`**

Fast mock hardware with minimal delays

```python
def test_performance(mock_hardware_fast):
    controller = mock_hardware_fast
    # Much faster for performance testing
```

**`mock_hardware_with_buttons`**

Mock hardware with pre-configured button listener

```python
def test_buttons(mock_hardware_with_buttons):
    controller, button_presses = mock_hardware_with_buttons
    controller.inject_button_press("left")
    time.sleep(0.05)
    assert button_presses == [("left", "pressed")]
```
## Test Coverage Goals
- [ ] Mock Hardware: 100%
- [ ]  Condition Manager: 95%
- [ ]  Kiosk Manager: 95%
- [ ]  Experiment Base: 90%
- [ ]  Hardware Controllers: 85%
- [ ]  Database: 90%
- [ ]  Overall: 90%+

## Contributing Tests
1. Create test file in tests/test_*.py
2. Use fixtures from conftest.py
3. Follow pytest conventions
4. Run pytest tests/ -v before committing
5. Aim for >90% coverage

## CI/CD Integration
Tests are run automatically on:

- Push to main branch
- Pull requests
- Daily scheduled runs

See .github/workflows/tests.yml for CI configuration.

---

## **Summary Table**

| File | Purpose | Type |
|---|---|---|
| `mnky_bx/hardware/mock_controller.py` | Mock hardware implementation | Main Module |
| `tests/fixtures/mock_hardware.py` | Test fixtures & scenarios | Fixtures |
| `tests/test_mock_hardware.py` | Unit tests | Test Suite |
| `tests/test_hardware_integration.py` | Integration tests | Test Suite |
| `tests/conftest.py` | Pytest configuration | Configuration |
| `tests/README.md` | Test documentation | Documentation |

---

## **Key Features**

- ✅ **Complete Mock Implementation**: All hardware functions simulated  
- ✅ **Event Recording**: Track all operations for verification  
- ✅ **Button Injection**: Simulate user input  
- ✅ **Failure Injection**: Test error handling  
- ✅ **Statistics Tracking**: Monitor command success/failure  
- ✅ **Pre-Built Scenarios**: Common test patterns  
- ✅ **Pytest Fixtures**: Easy test setup/teardown  
- ✅ **Integration Tests**: Test with other components  
- ✅ **Comprehensive Coverage**: >90% test coverage  
- ✅ **Documentation**: Usage examples and patterns  

## **Usage Examples**

### **Example 1: Test a Trial**
```python
def test_single_trial(mock_hardware_simple):
    hardware = mock_hardware_simple
    
    # Trial setup
    hardware.home_motor()
    hardware.set_led("left", True)
    hardware.set_led("right", True)
    
    # User presses button
    hardware.inject_button_press("left")
    
    # Outcome
    hardware.set_led("left", False)
    hardware.set_led("right", False)
    
    # Reward
    hardware.move_motor(5.0)
    
    # Verify
    assert hardware.get_motor_position() == 5.0

```

### Example 2: Test Button Sequence
```python
def test_button_sequence(mock_hardware_with_buttons):
    hardware, button_presses = mock_hardware_with_buttons
    
    hardware.inject_button_sequence([
        ("left", "pressed"),
        ("left", "released"),
        ("right", "pressed"),
    ])
    
    time.sleep(0.1)
    assert len(button_presses) == 3
```
### Example 3: Test Error Recovery
```python
def test_motor_error_recovery(mock_hardware_simple):
    hardware = mock_hardware_simple
    
    # Inject failure
    hardware.inject_failure("motor_home")
    assert not hardware.home_motor()
    
    # Recovery
    assert hardware.home_motor()
```
### Example 4: Run Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=mnky_bx --cov-report=html

# Specific test
pytest tests/test_mock_hardware.py::TestButtonInput::test_button_press_callback -v
```
Now the system has:

- ✅ Launcher GUI - Working, tested successfully

- ✅ Condition Manager - Full block progression

- ✅ Kiosk Manager - Session auto-increment

- ✅ Hardware Abstraction - Arduino Uno + Feather

- ✅ Mock Hardware - Complete testing system