# Monkey Box Gambling Experiment
A behavioral neuroscience research project designed to study decision-making under uncertainty and gambling behavior in freely moving non-human primates.

## Project Overview
This is a computerized behavioral experiment that presents gambling choices to test subjects, measuring their decision-making patterns and risk attitude.

### Experimental Design
#### Trial Types:
- One Option trials: Single option presentations for baseline measurements
- Choice Sure: Subject chooses between guaranteed rewards of different magnitudes
- Choice Gamble Sure: Subject chooses between a guaranteed reward and a probabilistic gamble

#### Key Features:
- Visual stimuli presented as colored circles on screen
- Touch/button press responses for choice selection
- Probabilistic reward delivery based on predefined conditions
- Real-time behavioral monitoring with motion and face detection
- Audio feedback (beeps) corresponding to reward magnitude

#### Technical Implementation
##### Hardware Integration:
- Pygame-based visual interface
- Touch screen or button press input detection
- Motion detection sensors
- Face detection cameras
- Audio output for reward feedback

##### Data Collection:
- SQLite database for trial-by-trial data logging
- Comprehensive timestamp recording (motion detection, face detection, stimulus onset, response, outcome, reward delivery)
- Spatial configuration tracking (left/right positioning)
- Choice accuracy and response time measurements


##### Paradigm Parameters
- Multiple reward magnitudes (1-7 pellets/units)
- Variable probability conditions (0.1, 0.5, 1.0)
- Configurable win/lose amounts for each option
- Randomized spatial positioning of choices
- Inter-trial intervals and timing controls

##### Research Applications
This type of experiment is typically used to study:
- Risk attitude and decision-making under uncertainty
- Reward valuation and magnitude sensitivity
- Comparative cognition across species

##### Data Output
The system generates detailed behavioral datasets including:

- Choice preferences and patterns
- Reaction times
- Choice curves
- Risk attitude measures
- Session-by-session performance tracking


## CHANGES
### 2025/09/25
- Initial upload. fully functional task using keyboard as user input. 
- Button input (arduino) or keyboard can now be used as user input.

### 2025/09/26
- Added Motion detection, face detection, and still photo capture. The system will continuously cycle through motion detection → face detection → trial execution → repeat, capturing pictures during each trial at 5 frames per second. Still photos are saved to the same database as the trial_data in table "trial_pictures".  Trials are only initiated after the installed camera detects motion. 
- Added GamblingExperimentAnalyzer.py. The program will import and analyze the SQLite database from the gambling experiment. The program automatically opens a file selection dialog when run without arguments. 

## TODO
- face detection
- still photos acquired in the interval starting at face_detection and ending at max_response_time or reward delivery
- reward system
