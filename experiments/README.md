# Experiments Directory

    experiments/
    ├── gambling_experiment/
    │   ├── experiment.py        # Main experiment class (subclass ExperimentBase)
    │   ├── config.json          # Experiment parameters
    │   └── subject_params/
    │       ├── default.json     # Default parameters for new subjects
    │       ├── subject_id_01.json  # Subject-specific overrides
    │       └── subject_id_02.json
    │
    └── blackjack/
        ├── experiment.py
        ├── config.json
        └── subject_params/

    ## Creating a New Experiment
    1. Create directory: experiments/your_experiment/
    2. Implement experiment.py (subclass ExperimentBase)
    3. Define config.json with timing and parameters
    4. Add default subject params in subject_params/default.json
    ## ExperimentBase Interface
    Your experiment should implement:

    python
    from mnky_bx.core.experiment_base import ExperimentBase

    class YourExperiment(ExperimentBase):
        def draw_stimuli(self):
            # Render stimulus on screen
            pass
        
        def wait_for_response(self):
            # Wait for button/touchscreen input
            pass
        
        def reveal_outcome(self):
            # Show trial result
            pass
    ```
    ## Configuration
    `config.json` defines:

    - Timing (ITI, response timeout, outcome duration)
    - Stimulus properties (colors, sizes)
    - Reward (magnitude, probability)
    `subject_params/default.json` defines adaptive parameters that can be customized per subject.

    ## Trial Data
    Trial results saved to SQLite:

    - Trial number, type, choice
    - Success/failure
    - Reward delivered
    - Timestamps

    ## Face Recognition During Trials
    During each trial:

    1. Frames captured at 3 FPS
    2. Face detection per frame
    3. Face recognition (subject identification)
    4. Results logged in recognition_log.json
    5. Images stored in trial_images/
    6. Adaptive parameters can adjust based on recognized subject.
    