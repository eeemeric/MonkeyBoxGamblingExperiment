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
    