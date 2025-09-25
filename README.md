# Monkey Box Gambling Experiment
A behavioral neuroscience research project designed to study decision-making and gambling behavior in freely moving non-human primates.

## Project Overview
This is a computerized behavioral experiment that presents gambling choices to test subjects, measuring their decision-making patterns, risk preferences, and learning behaviors.

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
- Experimental Parameters:

##### Paradigm Features
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

###### Data Output
The system generates detailed behavioral datasets including:

- Choice preferences and patterns
- Reaction times
- Choice curves
- Risk attitude measures
- Session-by-session performance tracking
