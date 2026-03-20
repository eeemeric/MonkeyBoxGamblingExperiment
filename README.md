# Monkey Box Gambling Experiment

A behavioral neuroscience research project designed to study decision-making under uncertainty and gambling behavior in freely moving non-human primates.

## Project Overview

This is a computerized behavioral experiment that presents gambling choices to subjects, measuring decision-making patterns and risk attitude. The system uses picamera2 for video acquisition, motion/face detection for trial initiation, and event-triggered video recording with pre-roll buffer.

## Experimental Design

### Trial Types:
- **One Option trials**: Single option presentations (probabilistic gamble or guaranteed reward)
- **Choice Sure**: Subject chooses between 2 guaranteed rewards of different magnitudes
- **Choice Gamble Sure**: Subject chooses between a guaranteed reward and a probabilistic gamble
- **Choice Gamble Gamble**: Subject chooses between two gambles of equal expected value

### Key Features:
- Visual stimuli presented as colored circles on screen
- Gamble stimuli are 2 concentric circles where:
  - Larger circle color indicates losing amount magnitude
  - Smaller circle color indicates winning amount magnitude
  - Smaller circle area indicates probability of receiving winning amount
- Touch/button press responses for choice selection
- Probabilistic reward delivery based on predefined conditions
- Real-time behavioral monitoring with motion and face detection
- Audio feedback (beeps) corresponding to reward magnitude

## Technical Implementation

### Hardware Integration:
- **Camera**: Picamera2-based video capture (replaces cv2.VideoCapture to avoid blocking on Raspberry Pi)
- **Motion Detection**: Background subtraction using MOG2 algorithm
- **Face Detection**: Haar Cascade classifier
- **Input**: Keyboard or Arduino button press (left/right buttons)
- **Reward Delivery**: Arduino-controlled via serial (consolidates button monitoring and reward delivery on single port)
- **Audio Output**: Pygame mixer for secondary reinforcement

### Software Stack:
- Pygame-based visual interface
- OpenCV for motion and face detection
- Picamera2 with circular buffer for event-triggered video recording
- SQLite database for trial-by-trial data logging
- Threading for parallel motion/face detection and video recording

## Key Features (Latest Update)

### Camera System (Refactored with picamera2)
- ✅ No more blocking on `cv2.VideoCapture(0)` - uses picamera2 directly
- ✅ Continuous frame capture thread feeds frames to detection algorithms
- ✅ Motion and face detection working on real-time frames
- ✅ Event-triggered video recording with circular buffer (pre-roll capture)
- ✅ Videos saved to disk with metadata stored in database

### Welcome Screen
- ✅ Title: "MonkeyBox: Gambling Experiment"
- ✅ BEGIN button (green, left) and EXIT button (dark red, right)
- ✅ Responds to left/right arrow keys
- ✅ Responds to Arduino left/right button presses
- ✅ Q-key exits from welcome screen

### Consolidated Arduino Interface
- ✅ Single serial connection for both button input and reward delivery
- ✅ Button presses: "20" (left), "21" (right)
- ✅ Reward commands: Send duration in milliseconds (e.g., "100\n" for 100ms reward)
- ✅ Graceful fallback to sound output if Arduino disconnects

### Improved Exit Handling
- ✅ Q-key now exits from any state (motion detection, face detection, ITI, trials)
- ✅ ITI uses event-driven loop instead of blocking delay
- ✅ Continuous experiment loop with block reshuffling
- ✅ Clean shutdown with proper camera cleanup

### Data Collection:
- **SQLite Database** for trial-by-trial data logging with tables:
  - `trial_data`: Trial parameters and outcomes with comprehensive timestamps
  - `trial_videos`: Video filenames and metadata for event-triggered recordings
  - `trial_pictures`: Individual frame captures (optional, currently disabled in favor of video)
- **Comprehensive timestamp recording**: Motion detection, face detection, stimulus onset, response, outcome, reward delivery
- **Spatial configuration tracking**: Left/right positioning of choices
- **Choice accuracy and response time measurements**
- **Event-triggered video files**: H.264 encoded with pre-roll buffer (1 second before event, configurable post-event duration)

### Paradigm Parameters
- Multiple reward magnitudes (1-7 pellets/units)
- Variable probability conditions (0.1, 0.5, 1.0)
- Configurable win/lose amounts for each option
- Randomized spatial positioning of choices
- Inter-trial intervals and timing controls
- Configurable motion/face detection timeouts

## Research Applications
This type of experiment is typically used to study:
- Risk attitude and decision-making under uncertainty
- Reward valuation and magnitude sensitivity
- Comparative cognition across species
- Effects of neural manipulations on gambling behavior

## Data Output
The system generates detailed behavioral datasets including:
- Choice preferences and patterns
- Reaction times
- Choice curves
- Risk attitude measures
- Session-by-session performance tracking
- Event-triggered video recordings with pre-roll buffer
- Frame-by-frame timestamps synchronized with trial events

## Installation & Setup

### Requirements:
- Python 3.7+
- pygame
- opencv-python
- picamera2
- numpy
- serial (pyserial)

### Camera Cascade Files:
Download Haar Cascade classifier for face detection:
```bash
mkdir -p ~/opencv_cascades
cd ~/opencv_cascades
wget https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml

###### Bash
python MonkeyBoxGamblingExperiment.py

###### CHANGES
### 2025/03/19
✅ Refactored camera system to use picamera2 instead of cv2.VideoCapture (eliminates hanging on Raspberry Pi)
✅ Event-triggered video recording with circular buffer (pre-roll capture of ~1 second before trigger)
✅ Consolidated Arduino interface - single serial connection for both button input and reward delivery
✅ Improved exit handling - Q-key now works during motion detection, face detection, and ITI
✅ Added welcome screen with BEGIN/EXIT options supporting keyboard and Arduino buttons
✅ Removed picture BLOB storage - keeping only video files for better performance
✅ Cleaned up ITI loop - now uses event-driven approach instead of blocking delay
✅ Proper path handling using Path(__file__).parent.resolve() for portability

###### 

This updated README reflects all the major changes we made including the picamera2 


