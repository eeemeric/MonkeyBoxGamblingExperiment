# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 17:25:24 2025

@author: eemeric2
"""

import pygame
import random
import time
import sys
import serial
import threading
import sqlite3
import os
from datetime import datetime
import cv2
import numpy as np
import math
import traceback
import queue

class CameraDetectionSystem:
    def __init__(self):
        print('Camera setup...')
        # Camera setup
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Motion detection
        self.background_subtractor = None
        self.motion_threshold = 5000
        self.frames_to_stabilize = 30
        
        # Detection flags
        self.motion_detected_flag = False
        self.face_detected_flag = False
        
        # Threading controls
        self.detection_active = False
        self.detection_thread = None
        self.stop_detection = threading.Event()
        
        # Picture capture during trials
        self.capture_pictures = False
        self.picture_thread = None
        self.picture_queue = queue.Queue()
        self.trial_number = 0
        
    def reset_for_new_detection_cycle(self):
        """Reset detection system for new motion->face cycle"""
        print("Resetting detection system...")
        
        # Stop any existing detection
        self.stop_all_detection()
        
        # Reset flags
        self.motion_detected_flag = False
        self.face_detected_flag = False
        
        # Create fresh background subtractor for motion detection
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=False,
            varThreshold=50,
            history=500
        )
        
        # Stabilize background model
        print("Stabilizing background model...")
        for i in range(self.frames_to_stabilize):
            ret, frame = self.cap.read()
            if ret:
                self.background_subtractor.apply(frame)
                
        print("Detection system reset complete")
    
    def _detection_thread(self):
        """Main detection thread: motion -> face detection"""
        print("Detection thread started")
        
        while not self.stop_detection.is_set() and self.detection_active:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Phase 1: Motion Detection
            if not self.motion_detected_flag:
                fg_mask = self.background_subtractor.apply(frame)
                motion_area = cv2.countNonZero(fg_mask)
                
                if motion_area > self.motion_threshold:
                    print(f"Motion detected! Area: {motion_area}")
                    self.motion_detected_flag = True
                    
            # Phase 2: Face Detection (only after motion detected)
            elif not self.face_detected_flag:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(50, 50)
                )
                
                if len(faces) > 0:
                    print(f"Face detected! {len(faces)} face(s) found")
                    self.face_detected_flag = True
                    break  # Exit detection loop to run trial
            
            time.sleep(0.03)  # ~30 FPS
        
        print("Detection thread ended")
    
    def _picture_capture_thread(self, db_connection, trial_number):
        """Capture pictures at 5 FPS during trial"""
        print("Picture capture thread started")
        frame_interval = 1.0 / 3.0  # 3 FPS = 0.333 seconds between frames
        frame_number = 0
        
        while self.capture_pictures and not self.stop_detection.is_set():
            start_time = time.time()
            
            ret, frame = self.cap.read()
            if ret:
                # Convert frame to JPEG for database storage
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                image_data = buffer.tobytes()
                
                # Store in queue for database insertion
                picture_data = {
                    'trial_number': trial_number,
                    'timestamp': pygame.time.get_ticks(),
                    'frame_number': frame_number,
                    'image_data': image_data,
                    'image_width': frame.shape[1],
                    'image_height': frame.shape[0]
                }
                
                self.picture_queue.put(picture_data)
                frame_number += 1
                
                print(f"Captured frame {frame_number} for trial {trial_number}")
            
            # Maintain 5 FPS timing
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            time.sleep(sleep_time)
        
        print("Picture capture thread ended")
    
    def start_detection_cycle(self):
        """Start motion->face detection cycle"""
        if self.detection_thread and self.detection_thread.is_alive():
            return False
            
        self.detection_active = True
        self.stop_detection.clear()
        
        self.detection_thread = threading.Thread(target=self._detection_thread)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        
        return True
    
    def start_picture_capture(self, db_connection, trial_number):
        """Start capturing pictures at 5 FPS during trial"""
        if self.picture_thread and self.picture_thread.is_alive():
            return False
            
        self.capture_pictures = True
        self.trial_number = trial_number
        
        self.picture_thread = threading.Thread(
            target=self._picture_capture_thread,
            args=(db_connection, trial_number)
        )
        self.picture_thread.daemon = True
        self.picture_thread.start()
        
        return True
    
    def stop_picture_capture(self):
        """Stop picture capture"""
        self.capture_pictures = False
        
        if self.picture_thread and self.picture_thread.is_alive():
            self.picture_thread.join(timeout=1.0)
    
    def stop_all_detection(self):
        """Stop all detection threads"""
        self.detection_active = False
        self.capture_pictures = False
        self.stop_detection.set()
        
        # Wait for threads to finish
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)
            
        if self.picture_thread and self.picture_thread.is_alive():
            self.picture_thread.join(timeout=1.0)
    
    def is_motion_detected(self):
        """Check if motion has been detected"""
        return self.motion_detected_flag
    
    def is_face_detected(self):
        """Check if face has been detected"""
        return self.face_detected_flag
    
    def save_captured_pictures(self, db_connection):
        """Save all captured pictures to database"""
        if not db_connection:
            return
            
        cursor = db_connection.cursor()
        pictures_saved = 0
        
        while not self.picture_queue.empty():
            try:
                picture_data = self.picture_queue.get_nowait()
                
                cursor.execute('''INSERT INTO trial_pictures 
                    (trial_number, timestamp, frame_number, image_data, image_width, image_height)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (picture_data['trial_number'],
                     picture_data['timestamp'],
                     picture_data['frame_number'],
                     picture_data['image_data'],
                     picture_data['image_width'],
                     picture_data['image_height']))
                
                pictures_saved += 1
                
            except queue.Empty:
                break
            except Exception as e:
                print(f"Error saving picture: {e}")
        
        if pictures_saved > 0:
            db_connection.commit()
            print(f"Saved {pictures_saved} pictures to database")
    
    def cleanup(self):
        """Cleanup all resources"""
        self.stop_all_detection()
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()




class experiment():
    def __init__(self):
        self.DEBUG = True # Use buttons instead of keyboard and fullscreen display
        self.SIMULATE = False
        
        self.max_RT = 5000
        self.ITI = 1000
        self.trial_type = None #['no response','no choice sure','no choice gamble','choice sure','choice gamble sure']

        self.choice = 'no response'
        
        # trial timestamps, milliseconds relative to pygame.init()
        self.ts_trial_start = None
        self.ts_motion_detect = None
        self.ts_face_detect = None
        self.ts_trial_start = None
        self.stimuli_on = None
        self.ts_button_press = None
        self.ts_outcome_reveal = None
        self.ts_reward_delivered = None
        
        # Circle settings
        self.CIRCLE_RADIUS = 100
        self.CIRCLE_AREA = math.pi*pow(self.CIRCLE_RADIUS,2)
        
        # options configuration
        self.opt_sp_config = random.choice(['left', 'right'])

        # Colors
        self.BLACK = (0, 0, 0)
        # look up table for colors
        self.COLORS =((127,0,0),    # dark red
                   (200,75,0),     # dark orange
                   (255, 215, 0),   # gold
                   (0,128,0),       # Screamin Green
                   (0,215,255),     # Deep Sky Blue
                   (0,0,131),       # Dark Blue
                   (48,25,52))      # Dark purple
        
        # conditions
        self.one_opt_conditions =[(1,   0,  1,	0,   0,  0),
                             (2,   0,  1,	0,   0,  0),
                             (3,   0,  1,	0,   0,  0),
                             (4,   0,  1,	0,   0,  0),
                             (5,   0,  1,	0,   0,  0),
                             (6,   0,  1,	0,   0,  0),
                             (7,   0,  1,	0,   0,  0),
                             (7,   4,0.5,   0,   0,  0),
                             (7,   1,0.5,	0,   0,  0),
                             (5,   1,0.5,	0,   0,  0),
                             (6,   2,0.1,	0,   0,  0),
                             (4,   1,0.1,	0,   0,  0)]
        
        self.two_opt_conditions =[(7,   0,  1,	1,   0,  1),
                                (7,   0,  1,	2,   0,  1),
                                (7,   0,  1,	3,   0,  1),
                                (7,   0,  1,	4,   0,  1),
                                (7,   0,  1,	5,   0,  1),
                                (7,   0,  1,	6,   0,  1),
                                (6,   0,  1,	1,   0,  1),
                                (6,   0,  1,	2,   0,  1),
                                (6,   0,  1,	3,   0,  1),
                                (6,   0,  1,	4,   0,  1),
                                (6,   0,  1,	5,   0,  1),
                                (5,   0,  1,	1,   0,  1),
                                (5,   0,  1,	2,   0,  1),
                                (5,   0,  1,	3,   0,  1),
                                (5,   0,  1,	4,   0,  1),
                                (4,   0,  1,	1,   0,  1),
                                (4,   0,  1,	2,   0,  1),
                                (4,   0,  1,	3,   0,  1),
                                (3,   0,  1,	1,   0,  1),
                                (3,   0,  1,	2,   0,  1),
                                (2,   0,  1,	1,   0,  1)]
        
        self.gmbl_sure_conditions = [(7,	4,	0.5,	4,   0,  1),
                            (7,	4,	0.5,	5,   0,  1),
                            (7,	4,	0.5,	6,   0,  1),
                            (7,	4,	0.5,	7,   0,  1),
                            (7,	1,	0.5,	1,   0,  1),
                            (7,	1,	0.5,	2,   0,  1),
                            (7,	1,	0.5,	3,   0,  1),
                            (7,	1,	0.5,	4,   0,  1),
                            (7,	1,	0.5,	5,   0,  1),
                            (7,	1,	0.5,	6,   0,  1),
                            (7,	1,	0.5,	7,   0,  1),
                            (5,	1,	0.5,	1,   0,  1),
                            (5,	1,	0.5,	2,   0,  1),
                            (5,	1,	0.5,	3,   0,  1),
                            (5,	1,	0.5,	4,   0,  1),
                            (5,	1,	0.5,	5,   0,  1),
                            (6,	2,	0.1,	2,   0,  1),
                            (6,	2,	0.1,	3,   0,  1),
                            (6,	2,	0.1,	4,   0,  1),
                            (6,	2,	0.1,	5,   0,  1),
                            (6,	2,	0.1,	6,   0,  1),
                            (4,	1,	0.1,	1,   0,  1),
                            (4,	1,	0.1,	2,   0,  1),
                            (4,	1,	0.1,	3,   0,  1),
                            (4,	1,	0.1,	4,   0,  1)]

        self.gmbl_gmbl_conditions = [(7,	1,	0.50,	7,	2,	0.40),
                                     (7,	1,	0.50,	6,	2,	0.50),
                                     (7,	1,	0.50,	6,	1,	0.60), 
                                     (7,	1,	0.50,	5,	1,	0.75),
                                     (7,	1,	0.50,	7,	3,	0.25),
                                     (7,	2,	0.40,	6,	2,	0.50),
                                     (7,	2,	0.40,	6,	1,	0.60),
                                     (7,	2,	0.40,	5,	1,	0.75),
                                     (7,	2,	0.40,	7,	3,	0.25),
                                     (6,	2,	0.50,	6,	1,	0.60),
                                     (6,	2,	0.50,	5,	1,	0.75),
                                     (6,	2,	0.50,	7,	3,	0.25),
                                     (6,	1,	0.60,	5,	1,	0.75),
                                     (6,	1,	0.60,	7,	3,	0.25),
                                     (5,	1,	0.75,	7,	3,	0.25)]
        
        if self.DEBUG:
            self.current_conditions = self.one_opt_conditions + self.two_opt_conditions + self.gmbl_sure_conditions + self.gmbl_gmbl_conditions 
            # self.current_conditions = self.gmbl_sure_conditions
        else:
            # TODO: MAKE RANDOM
            self.current_conditions = self.one_opt_conditions + self.two_opt_conditions + self.gmbl_sure_conditions + self.gmbl_gmbl_conditions
            # self.current_conditions = self.gmbl_sure_conditions
        
        self.total_trials = len(self.current_conditions)
        self.current_trials_counter = 0
        self.total_trial_counter = 0

        print(f"{len(self.current_conditions)} trials in block)")
        
        # Initialize Pygame first to get desktop size, but don't set the mode yet
        pygame.init()
        pygame.mixer.init() # sound
        
        
        # Load sound
        try:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            print(script_dir)
            # Create database file with timestamp
            sound_path = os.path.join(script_dir, 'beep500.wav')
            self.beep_sound500 = pygame.mixer.Sound(sound_path)
            sound_path = os.path.join(script_dir, 'beep1000.wav')
            self.beep_sound1000 = pygame.mixer.Sound(sound_path)
        except:
            print("Warning: beep500.wav or beep1000.wav not found. Sound effects will be skipped.")
            self.beep_sound500 = None
            self.beep_sound1000 = None
            
        self.clock = pygame.time.Clock()      
        
        # Get the size of the primary desktop display
        desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]
        
        # look up table for colors
        self.COLORS =((127,0,0),    # dark red
                   (200,75,0),     # dark orange
                   (255, 215, 0),   # gold
                   (0,128,0),       # Screamin Green
                   (0,215,255),     # Deep Sky Blue
                   (0,0,131),       # Dark Blue
                   (48,25,52))      # Dark purple
        
        # Initialize Pygame first to get desktop size, but don't set the mode yet
        pygame.init()
        pygame.mixer.init() # sound
        
        # Load sound
        try:
            self.beep_sound500 = pygame.mixer.Sound("beep500.wav")
            self.beep_sound1000 = pygame.mixer.Sound("beep1000.wav")
            # test sound
            self.beep_sound500.play()
            pygame.time.delay(500)
            self.beep_sound1000.play()
            pygame.time.delay(500)
        except:
            print("Warning: beep.wav not found. Sound effects will be skipped.")
            self.beep_sound500 = None
            self.beep_sound1000 = None
            
        self.clock = pygame.time.Clock()      
        
        # Get the size of the primary desktop display
        desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]

        # Set the window size
        self.window_width = 800
        self.window_height = 600

        self.LEFT_CIRCLE_POS = (self.window_width // 4, self.window_height // 2)
        self.RIGHT_CIRCLE_POS = (3 * self.window_width // 4, self.window_height // 2)

        # Calculate the coordinates for the top-right quadrant
        # The x-coordinate is the desktop width minus the window width
        # The y-coordinate is 0 for the top edge of the screen
        x_pos = desktop_width - self.window_width
        y_pos = 50
        if self.DEBUG:
            # Set the SDL environment variable before setting the display mode
            os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x_pos},{y_pos}'
            # Now, set the display mode
            self.screen = pygame.display.set_mode((self.window_width, self.window_height))
        else:
            # Set the SDL environment variable before setting the display mode
            os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x_pos},{y_pos}'
            # Now, set the display mode
            self.screen = pygame.display.set_mode((self.window_width, self.window_height))
            
            # # Create a full-screen surface at your monitor's current resolution
            # self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

        pygame.display.set_caption("Experiment")
        
        # SETUP sqlite_db
        self.db_connection = None
        self.setup_database()
        
        # Initialize camera detection system
        self.camera_system = CameraDetectionSystem() 
        # Detection timeouts
        self.MOTION_TIMEOUT = 300  # 5 minutes
        self.FACE_TIMEOUT = 10     # 10 seconds

        # Arduino setup
        self.arduino_buttons = None
        self.arduino_buttons_connected = False
        self.arduino_buttons_button_pressed = None
        self.setup_arduino_buttons()
        self.arduino_reward = None
        self.arduino_reward_connected = False
        self.reward_max_position = 10
        self.reward_current_position = 0
        self.setup_arduino_reward()

    def setup_arduino_buttons(self):
        """Setup Arduino buttons serial connection"""
        try:
            self.arduino_buttons = serial.Serial('COM14', 115200, timeout=1)
            print("Attempting to connect to Arduino on COM14...")
            
            # Wait for Arduino to initialize and send "buttons"
            start_time = time.time()
            while time.time() - start_time < 5:  # Wait up to 5 seconds
                if self.arduino_buttons.in_waiting > 0:
                    data = self.arduino_buttons.readline().decode('utf-8').strip()
                    print(f"Received from Arduino: {data}")
                    if data == "buttons":
                        self.arduino_buttons_connected = True
                        print("Arduino connected and ready!")
                        # Start Arduino reading thread
                        self.arduino_buttons_thread = threading.Thread(target=self.read_arduino_buttons, daemon=True)
                        self.arduino_buttons_thread.start()
                        return
                time.sleep(0.1)
            
            print("Arduino did not send 'buttons' confirmation. Using keyboard input.")
            self.arduino_buttons.close()
            self.arduino_buttons = None
        except Exception as e:
            print(f"Failed to connect to Arduino: {e}")
            print("Using keyboard input instead.")
            self.arduino_buttons = None

    def setup_arduino_reward(self):
        """Setup Arduino reward serial connection"""
        try:
            self.reward_current_position = 0
            self.reward_current_direction = 1 # 1 = forward, 0 = backward

            self.arduino_reward = serial.Serial('COM4', 115200, timeout=1)
            print("Attempting to connect to Arduino on COM4...")
            # Wait for Arduino to initialize and send "reward"
            start_time = time.time()
            while time.time() - start_time < 5:  # Wait up to 5 seconds
                if self.arduino_reward.in_waiting > 0:
                    data = self.arduino_reward.readline().decode().strip()
                    print(f"Received from Arduino: {data}")
                    while data != "Grbl 1.1h ['$' for help]" and time.time() - start_time < 5:
                        data = self.arduino_reward.readline().decode().strip()
                        if data == "Grbl 1.1h ['$' for help]":
                            self.arduino_reward_connected = True
                            print("Arduino_reward connected and ready!")
                            # set starting position
                            command = "G92 X0 Y0 Z0\n"
                            self.arduino_reward.write(command.encode()) # Encode the string to bytes before sending
                            send_time = time.time()
                            while time.time() - send_time < 5:  # Wait up to 5 seconds
                                if self.arduino_reward.in_waiting > 0:
                                    response = self.arduino_reward.readline().decode().strip()
                                    print(response)
                                    if response == "ok":
                                        print("Homing command acknowledged by Arduino.")
                                        break
                            command = "G0 X5\n"
                        self.arduino_reward.write(command.encode()) # Encode the string to bytes before sending
                        time.sleep(2)
                        command = "G0 X0\n"
                        self.arduino_reward.write(command.encode()) # Encode the string to bytes before sending
                    if self.arduino_reward_connected:
                            return
                    time.sleep(0.1)

            if not self.arduino_reward_connected:
                print("Arduino did not send 'Grbl 1.1h ['$' for help]' confirmation. Using sound output.")
                self.arduino_reward.close()
        except Exception as e:
            print(f"Failed to connect to Arduino_reward: {e}")  
            print("Using sound output instead.")
            self.arduino_reward.close()
            self.arduino_buttons = None

    def read_arduino_buttons(self):
        """Continuously read from Arduino in separate thread"""
        while self.arduino_buttons and self.arduino_buttons_connected:
            try:
                if self.arduino_buttons.in_waiting > 0:
                    data = self.arduino_buttons.readline().decode('utf-8').strip()
                    if data == "20":
                        self.arduino_buttons_button_pressed = "left"
                    elif data == "21":
                        self.arduino_buttons_button_pressed = "right"
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage
            except Exception as e:
                print(f"Arduino read error: {e}")
                self.arduino_buttons_connected = False
                break

    def setup_database(self):
        """Setup SQLite database with trial data"""
        try:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Create database file with timestamp
            db_filename = f"experiment_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            db_path = os.path.join(script_dir, db_filename)
            
            self.db_connection = sqlite3.connect(db_path)
            cursor = self.db_connection.cursor()
            
            # Create trial data table only
            cursor.execute('''CREATE TABLE IF NOT EXISTS trial_data (
                trial_number INTEGER,
                trial_type TEXT,
                win_Amount1 REAL,
                lose_Amount1 REAL,
                pWin1 REAL,
                win_Amount2 REAL,
                lose_Amount2 REAL,
                pWin2 REAL,
                options_spacial_config TEXT,
                left_circle_x INTEGER,
                left_circle_y INTEGER,
                right_circle_x INTEGER,
                right_circle_y INTEGER,
                ts_motion_detect INTEGER,
                ts_face_detect INTEGER,
                ts_trial_start INTEGER,
                ts_stimuli_on INTEGER,
                ts_button_press INTEGER,
                choice TEXT,
                ts_outcome_reveal INTEGER,
                ts_reward_delivered INTEGER,
                reward_magnitude INTEGER,
                ts_trial_end INTEGER
            )''')
            
           # New pictures table for trial photos
            cursor.execute('''CREATE TABLE IF NOT EXISTS trial_pictures (
                picture_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trial_number INTEGER,
                timestamp INTEGER,
                frame_number INTEGER,
                image_data BLOB,
                image_width INTEGER,
                image_height INTEGER,
                FOREIGN KEY (trial_number) REFERENCES trial_data (trial_number)
            )''')
            
            self.db_connection.commit()
            print("Database table created successfully")
            
        except Exception as e:
            print(f"Database setup error: {e}")

    def wait_for_motion_and_face(self):
        """
        Wait for motion detection, then face detection
        Returns True if both detected, False otherwise
        """
        # Reset detection system
        self.camera_system.reset_for_new_detection_cycle()
        
        # Start detection cycle
        self.camera_system.start_detection_cycle()
        
        print("Waiting for motion detection...")
        motion_start_time = time.time()
        
        # Wait for motion detection
        while time.time() - motion_start_time < self.MOTION_TIMEOUT:
            if self.camera_system.is_motion_detected():
                self.ts_motion_detect = pygame.time.get_ticks()
                print(f"Motion detected at {self.ts_motion_detect} ms!")
                break
                
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    return False
            
            time.sleep(0.01)
        else:
            print("Motion detection timeout")
            return False
        
        # Now wait for face detection
        print("Motion detected! Now waiting for face...")
        face_start_time = time.time()
        
        while time.time() - face_start_time < self.FACE_TIMEOUT:
            if self.camera_system.is_face_detected():
                self.ts_face_detect = pygame.time.get_ticks()
                print(f"Face detected at {self.ts_face_detect} ms!")
                return True
                
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    return False
            
            time.sleep(0.01)
        
        print("Face detection timeout - returning to motion detection")
        return False

    def setup_new_trial(self):
        # time stamps
        self.ts_trial_start = pygame.time.get_ticks()
        self.ts_stimuli_on = None
        self.ts_button_press = None
        self.ts_outcome_reveal = None
        self.ts_reward_delivered = None
        self.ts_end_of_trial = None
        
        # correct trial flag
        self.success = False
        
        if self.current_trials_counter >= len(self.current_conditions):
            print(f"Trial {self.current_trials_counter+1} in block: Reshuffling...")
            # shuffle trials and reset block counter
            if self.DEBUG:
                self.current_conditions = self.one_opt_conditions + self.two_opt_conditions + self.gmbl_sure_conditions + self.gmbl_gmbl_conditions
                # self.current_conditions = self.gmbl_sure_conditions
                self.current_trials_counter = 0
            else:
                self.current_conditions = random.sample(self.one_opt_conditions) + random.sample(self.two_opt_conditions) + random.sample(self.gmbl_sure_conditions) + random.sample(self.gmbl_gmbl_conditions)
                # self.current_conditions = self.gmbl_sure_conditions
                self.current_trials_counter = 0

        # going through the list of conditions using the counter for the current trial block
        self.win_Amount1    = self.current_conditions[self.current_trials_counter][0]
        self.lose_Amount1   = self.current_conditions[self.current_trials_counter][1]
        self.pWin1          = self.current_conditions[self.current_trials_counter][2]
        self.win_Amount2    = self.current_conditions[self.current_trials_counter][3]
        self.lose_Amount2   = self.current_conditions[self.current_trials_counter][4]
        self.pWin2          = self.current_conditions[self.current_trials_counter][5]
        self.opt_sp_config  = random.choice(['left', 'right'])
        
        # parse trial type
        if self.pWin1 == 1 and self.pWin2 == 0:
            self.trial_type = 'no choice sure'
        if self.pWin1 < 1 and self.pWin2 == 0:
                self.trial_type = 'no choice gamble'
        if self.pWin1 == 1 and self.pWin2 == 1:
            self.trial_type = 'choice sure'
        if self.pWin1 < 1 and self.pWin2 == 1:
            self.trial_type = 'choice gamble sure'
        if self.pWin1 < 1 and self.pWin2 < 1:
            self.trial_type = 'choice gamble gamble'

        # option 1 on right
        print(f"Initialializing trial {self.total_trial_counter+1}")
        print(f"Trial {self.current_trials_counter+1} in block of {len(self.current_conditions)} trials")
        print(f"Trial type: {self.trial_type}")
        print(f"Option 1 on {self.opt_sp_config}")
        print(f"Parameters: winAmount1, {self.win_Amount1}")
        print(f"Parameters: loseAmount1, {self.lose_Amount1}")
        print(f"Parameters: pWin1, {self.pWin1}")
        print(f"Parameters: winAmount2, {self.win_Amount2}")
        print(f"Parameters: loseAmount2, {self.lose_Amount2}")
        print(f"Parameters: pWin2, {self.pWin2}")
        print(" ")
    
    def draw_stimuli(self):
        self.left_color_Lose  = None
        self.left_color_Win   = None
        self.right_color_Lose = None
        self.right_color_Win  = None

        print("Drawing Stimuli...")
        self.opt_sp_config = random.choice(['left', 'right'])
        # self.opt_sp_config = 'right'
        
        self.CIRCLE_AREA = math.pi*pow(self.CIRCLE_RADIUS,2)
        area_win1 = self.CIRCLE_AREA*self.pWin1
        radius_win1 = int(math.sqrt(float(area_win1)/math.pi))
        area_win2 = self.CIRCLE_AREA*self.pWin2
        radius_win2 = int(math.sqrt(float(area_win2)/math.pi))

        if self.opt_sp_config == 'left':
            # Option 1 COLORS on the left
            self.left_color_Lose  = self.COLORS[self.lose_Amount1-1]
            self.left_color_Win   = self.COLORS[self.win_Amount1-1]
            # Option 2 COLORS on the right
            self.right_color_Lose = self.COLORS[self.lose_Amount2-1]
            self.right_color_Win  = self.COLORS[self.win_Amount2-1]
            
            # draw left option
            if self.lose_Amount1 > 0: # Draw lose amount first if >0
                pygame.draw.circle(self.screen, self.left_color_Lose, self.LEFT_CIRCLE_POS, self.CIRCLE_RADIUS)
            if self.win_Amount1 > 0: # Draw win amount on top of lose amount if win_amount1 > 0
                pygame.draw.circle(self.screen, self.left_color_Win, self.LEFT_CIRCLE_POS, radius_win1)
            
            # draw option 2 on the right
            if self.lose_Amount2 > 0:
                pygame.draw.circle(self.screen,self.right_color_Lose, self.RIGHT_CIRCLE_POS, self.CIRCLE_RADIUS)
            if self.win_Amount2 > 0:
                pygame.draw.circle(self.screen,self.right_color_Win, self.RIGHT_CIRCLE_POS, radius_win2)

        else:
            # Option 2 COLORS on the LEFT
            self.left_color_Lose = self.COLORS[self.lose_Amount2-1]
            self.left_color_Win = self.COLORS[self.win_Amount2-1]
            # Option 2 COLORS on the RIGHT
            self.right_color_Lose = self.COLORS[self.lose_Amount1-1]
            self.right_color_Win = self.COLORS[self.win_Amount1-1]
            
            # draw option 1 on the right
            if self.lose_Amount1 > 0: # Draw lose amount first if >0
                pygame.draw.circle(self.screen, self.right_color_Lose, self.RIGHT_CIRCLE_POS, self.CIRCLE_RADIUS)
            if self.win_Amount1 > 0:
                pygame.draw.circle(self.screen, self.right_color_Win, self.RIGHT_CIRCLE_POS, radius_win1)
            
            # draw option 2 on the left
            if self.lose_Amount2 > 0:
                pygame.draw.circle(self.screen, self.left_color_Lose, self.LEFT_CIRCLE_POS, self.CIRCLE_RADIUS)
            if self.win_Amount2 > 0:
                pygame.draw.circle(self.screen, self.left_color_Win, self.LEFT_CIRCLE_POS, radius_win2)
        
    def wait_for_response(self):
        # remove events from the event queue
        
        pygame.event.clear()
        if self.arduino_buttons_connected:
            self.arduino_buttons.flushInput()
        
        print("Waiting for response")
        # get time 
        # wait till max response time
        # add option to use arduino_buttons
        # flush serial buffer so responses before stimulus onset are not registered
        # start acquiring images at 5 FPS
        if self.SIMULATE:
            print("Simulated Choice")
            self.choice = 'left'
        elif self.DEBUG:
            running = True
            while running:
                if self.arduino_buttons_connected and self.arduino_buttons_button_pressed:
                    print(f"{self.arduino_buttons_button_pressed} button pressed" )
                    self.choice = self.arduino_buttons_button_pressed
                    self.ts_button_press = pygame.time.get_ticks()
                    self.arduino_buttons_button_pressed = None
                    running = False
                    break
                    
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        self.clean_up()
                    # Check for a key press
                    if event.type == pygame.KEYDOWN:
                        # If the key pressed is 'q', set running to False
                        if event.key == pygame.K_q:
                            running = False
                            self.clean_up()
                            
                        # If the key pressed is '<-', set running to False
                        if event.key == pygame.K_LEFT:
                            self.time_of_response = pygame.time.get_ticks()
                            self.choice = 'left'
                            print("Left arrow key pressed!")
                            self.ts_button_press = pygame.time.get_ticks()
                            running = False
                            return True
                        
                        # If the key pressed is '->', set running to False
                        if event.key == pygame.K_RIGHT:
                            self.time_of_response = pygame.time.get_ticks()
                            self.choice = 'right'
                            print("Right arrow key pressed!")
                            self.ts_button_press = pygame.time.get_ticks()
                            running = False
                            return True
                if pygame.time.get_ticks() > self.max_RT + self.ts_stimuli_on:
                    running = False
                    self.choice = 'no response'
                    print("No Response")
                    
                pygame.time.delay(10)
        else:
            # use arduino buttons
            running = True
            while running:
                if self.arduino_buttons_connected and self.arduino_buttons_button_pressed:
                    self.choice = self.arduino_buttons_button_pressed
                    self.ts_button_press = pygame.time.get_ticks()
                    running = False
                if pygame.time.get_ticks() > self.max_RT + self.ts_stimuli_on:
                    running = False
                    self.choice = 'no response'
                    print("No Response")
                    
                pygame.time.delay(4)
            
    def handle_choice(self):
        # parse trial type
        if self.choice == 'no response':
            self.success = False
            self.reward_magnitude = -1
            return
        print("Parsing response")
        if self.trial_type == 'no choice sure': 
            if self.opt_sp_config == self.choice:
                self.success = True
            else:
                self.reward_magnitude = -1
                self.success = False
                
        if self.trial_type == 'no choice gamble': 
            if self.opt_sp_config == self.choice:
                self.success = True
                
                # gamble to win lose
                self.win = random.random() < self.pWin1 # roll the dice
                if self.win:
                    print("Gambled, won")
                else:
                    print("Gambled, lost")
                
            else:
                self.reward_magnitude = -1
                self.success = False
                
        if self.trial_type == 'choice sure':
            if (self.opt_sp_config == self.choice):
                # larger Amount chosen
                self.success = True
            elif self.opt_sp_config != self.choice:
                # smaller Amount chosen
                self.reward_magnitude = -1
                self.success = False
                
        if self.trial_type == 'choice gamble sure':
            self.success = True
            if (self.opt_sp_config == self.choice):
                print('Gamble option chosen')
                # gamble to win lose
                self.win = random.random() < self.pWin1 # roll the dice
                if self.win:
                    print("Gambled, won")
                else:
                    print("Gambled, lost")
            else:
                print('Sure option chosen')
    
        if self.trial_type == 'choice gamble gamble':
            self.success = True
            if (self.opt_sp_config == self.choice):
                # option 1 chosen
                # gamble to win/lose
                self.win = random.random() < self.pWin1 # roll the dice
            if (self.opt_sp_config != self.choice):
                # option 1 chosen
                # gamble to win/lose
                self.win = random.random() < self.pWin2 # roll the dice
            if self.win:
                print("Gambled, won")
            else:
                print("Gambled, lost")
                
    def reveal_outcome(self):
        print("Reveal Outcome")
        # Check if display is still active
        if not pygame.get_init() or pygame.display.get_surface() is None:
            return
        self.screen.fill(self.BLACK)

        if self.choice == 'no response':
            pygame.display.flip()
            return
    
        self.screen.fill(self.BLACK)
        pygame.display.flip()
        pygame.time.delay(250)
        
        if self.trial_type == 'no choice sure': 
            self.beep_count = self.win_Amount1 - 1
            if self.success:
                self.reward_magnitude = self.win_Amount1
            else:
                self.reward_magnitude = -1

            self.reward_color = self.COLORS[self.win_Amount1-1]
            
            if self.opt_sp_config == 'left' and self.success == True:
                # draw smaller circle. color: win amount 1
                pygame.draw.circle(self.screen, self.reward_color, self.LEFT_CIRCLE_POS, self.CIRCLE_RADIUS)
            if self.opt_sp_config == 'right' and self.success == True:
                # draw smaller circle. color: win amount 1
                pygame.draw.circle(self.screen, self.reward_color, self.RIGHT_CIRCLE_POS, self.CIRCLE_RADIUS)
            
        if self.trial_type == 'no choice gamble':
            if self.opt_sp_config == self.choice: # chose option 1
                if self.win == 1:
                    self.beep_count = self.win_Amount1 - 1
                    self.reward_magnitude = self.win_Amount1
                    self.reward_color = self.COLORS[self.win_Amount1-1]
                else:
                    self.beep_count = self.lose_Amount1 - 1
                    self.reward_magnitude = self.lose_Amount1
                    self.reward_color = self.COLORS[self.lose_Amount1-1]
                
                if self.opt_sp_config == 'left':
                    fbloc = self.LEFT_CIRCLE_POS
                else:
                    fbloc = self.RIGHT_CIRCLE_POS
                    
            # draw win or lose amount 1
            pygame.draw.circle(self.screen, self.reward_color, fbloc, self.CIRCLE_RADIUS)
                
        if self.trial_type == 'choice sure':
            if self.opt_sp_config == self.choice and self.success == True:
                self.beep_count = self.win_Amount1 - 1
                self.reward_magnitude = self.win_Amount1
                self.reward_color = self.COLORS[self.win_Amount1-1]
                
                if self.opt_sp_config == 'left':
                    fbloc = self.LEFT_CIRCLE_POS
                else:
                    fbloc = self.RIGHT_CIRCLE_POS
        
            if self.opt_sp_config != self.choice and self.success == False:
                self.beep_count = self.win_Amount2 - 1
                self.reward_magnitude = self.win_Amount2
                self.reward_color = self.COLORS[self.win_Amount2-1]
                
                if self.opt_sp_config == 'left':
                    fbloc = self.RIGHT_CIRCLE_POS
                else:
                    fbloc = self.LEFT_CIRCLE_POS
            
            # draw win or lose amount 1
            pygame.draw.circle(self.screen, self.reward_color, fbloc, self.CIRCLE_RADIUS)
            
        if self.trial_type == 'choice gamble sure':
            if self.opt_sp_config == self.choice: # chose the gamble
                if self.win == 1:
                    self.beep_count = self.win_Amount1 - 1
                    self.reward_magnitude = self.win_Amount1
                    self.reward_color = self.COLORS[self.win_Amount1-1]
                else:
                    self.beep_count = self.lose_Amount1 - 1
                    self.reward_magnitude = self.lose_Amount1
                    self.reward_color = self.COLORS[self.lose_Amount1-1]
                
                if self.opt_sp_config == 'left':
                    fbloc = self.LEFT_CIRCLE_POS
                else:
                    fbloc = self.RIGHT_CIRCLE_POS  

            if self.opt_sp_config != self.choice: # chose the sure option
                self.beep_count = self.win_Amount2 - 1
                self.reward_magnitude = self.win_Amount2
                self.reward_color = self.COLORS[self.win_Amount2-1]

                if self.opt_sp_config == 'left':
                    fbloc = self.RIGHT_CIRCLE_POS
                else:
                    fbloc = self.LEFT_CIRCLE_POS  
            
        if self.trial_type == 'choice gamble gamble':
            if self.opt_sp_config == self.choice: # chose option 1 gamble
                if self.win == 1:
                    self.beep_count = self.win_Amount1 - 1
                    self.reward_magnitude = self.win_Amount1
                    self.reward_color = self.COLORS[self.win_Amount1-1]
                else:
                    self.beep_count = self.lose_Amount1 - 1
                    self.reward_magnitude = self.lose_Amount1
                    self.reward_color = self.COLORS[self.lose_Amount1-1]

                if self.opt_sp_config == 'left':
                    fbloc = self.LEFT_CIRCLE_POS
                else:
                    fbloc = self.RIGHT_CIRCLE_POS 
            else:
                if self.win == 1:
                    self.beep_count = self.win_Amount2 - 1
                    self.reward_magnitude = self.win_Amount2
                    self.reward_color = self.COLORS[self.win_Amount2-1]
                else:
                    self.beep_count = self.lose_Amount2 - 1
                    self.reward_magnitude = self.lose_Amount2
                    self.reward_color = self.COLORS[self.lose_Amount2-1]

                if self.opt_sp_config == 'right':
                    fbloc = self.LEFT_CIRCLE_POS
                else:
                    fbloc = self.RIGHT_CIRCLE_POS    
                
            pygame.draw.circle(self.screen, self.reward_color, fbloc, self.CIRCLE_RADIUS)

        pygame.display.flip()       
        self.ts_outcome_reveal = pygame.time.get_ticks()
        pygame.time.delay(500)
    
    def deliver_reward(self):
        self.ts_reward_delivered = pygame.time.get_ticks()
        print(f"Reward Magnitude, {self.reward_magnitude }")
        
        if not self.success and (self.trial_type == 'choice sure' or self.trial_type == 'no choice sure'):
             if self.beep_sound500: # error tone
                self.beep_sound500.play()
                pygame.time.delay(500)       

        for beeps in range(self.reward_magnitude):
            if self.beep_sound1000: # reward tone
                self.beep_sound1000.play()
            pygame.time.delay(500)
    
    def log_trial_data(self):
        print("Logging trial data to SQLite database")
        self.ts_end_of_trial = pygame.time.get_ticks()
        if not self.db_connection:
            return
        try:
            cursor = self.db_connection.cursor()
            data = [self.total_trial_counter+1,
                    self.trial_type,
                    self.win_Amount1,
                    self.lose_Amount1,
                    self.pWin1,
                    self.win_Amount2,
                    self.lose_Amount2,
                    self.pWin2,self.opt_sp_config,
                    self.LEFT_CIRCLE_POS[0],
                    self.LEFT_CIRCLE_POS[1],
                    self.RIGHT_CIRCLE_POS[0],
                    self.RIGHT_CIRCLE_POS[1],
                    self.ts_motion_detect,
                    self.ts_face_detect,
                    self.ts_trial_start,
                    self.ts_stimuli_on,
                    self.ts_button_press,
                    self.choice,
                    self.ts_outcome_reveal,
                    self.ts_reward_delivered,
                    self.reward_magnitude,
                    self.ts_end_of_trial]
            cursor.execute('''INSERT INTO trial_data (
                trial_number,
                trial_type,
                win_Amount1,
                lose_Amount1,
                pWin1,
                win_Amount2,
                lose_Amount2,
                pWin2,
                options_spacial_config,
                left_circle_x,
                left_circle_y,
                right_circle_x,
                right_circle_y,
                ts_motion_detect,
                ts_face_detect,
                ts_trial_start,
                ts_stimuli_on,
                ts_button_press,
                choice,
                ts_outcome_reveal,
                ts_reward_delivered,
                reward_magnitude,
                ts_trial_end) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',data)
            self.db_connection.commit()
            print(f"Trial {self.total_trial_counter + 1} data logged to database")
            print(" ")
            print(" ")
            # if trial completed and correct, increment block counter
            self.total_trial_counter += 1
        except Exception as e:
            print(f"Database logging error: {e}")
    
    def run_trial(self):
        print(f"Running Trial {self.total_trial_counter + 1}")      
        # Start picture capture at 5 FPS
        self.camera_system.start_picture_capture(
            self.db_connection, 
            self.total_trial_counter + 1
        )

        # Arduino LED control: ON
        if self.arduino_buttons_connected:
            try:
                self.arduino_buttons.write("3\n".encode('utf-8'))
            except Exception as e:
                print(f"Arduino write error: {e}")

        self.setup_new_trial()
        self.draw_stimuli()
        pygame.display.flip()
        self.ts_stimuli_on = pygame.time.get_ticks()
        
        self.wait_for_response()
        
        # Arduino LED control: OFF
        if self.arduino_buttons_connected:
            try:
                self.arduino_buttons.write("4\n".encode('utf-8'))
            except Exception as e:
                print(f"Arduino write error: {e}")
        self.handle_choice()
        self.reveal_outcome()
        pygame.time.delay(250)
        self.deliver_reward()

         # Stop picture capture
        self.camera_system.stop_picture_capture()
        
        # Save captured pictures to database
        self.camera_system.save_captured_pictures(self.db_connection)

        self.log_trial_data()
        
        # clear display wait ITI befor initiating next trial
        self.screen.fill(self.BLACK)
        pygame.display.flip()

        pygame.time.delay(self.ITI)
        
        if self.success == True: # move on to next trial if correct
            self.current_trials_counter += 1
            
    def run(self):
        """Main experiment loop with camera detection"""
        print('Running: Gambling Experiment with Camera Detection')
        running = True
        clock = pygame.time.Clock() 

        while running: 
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                # Check for a key press
                elif event.type == pygame.KEYDOWN:
                    # If the key pressed is 'q', set running to False
                    if event.key == pygame.K_q:
                        running = False
                        break
            # Camera detection cycle: motion -> face -> trial
            if not self.SIMULATE:
                if self.wait_for_motion_and_face():
                    # Both motion and face detected, run trial
                    if running and pygame.display.get_surface() is not None:
                        try:
                            self.run_trial()
                        except pygame.error as e:
                            if "display Surface quit" in str(e):
                                print("Display closed, ending experiment")
                                running = False
                            else:
                                raise e
                # If face not detected, loop continues to motion detection
            else:
                # Only run trial if still running and display is active
                if running and pygame.display.get_surface() is not None:
                    try:
                        self.run_trial()
                    except pygame.error as e:
                        if "display Surface quit" in str(e):
                            print("Display closed, ending experiment")
                            running = False
                        else:
                            raise e
            
            clock.tick(60)  # Limit to 60 FPS
        
        self.clean_up()
        
    def clean_up(self):
        print('Cleaning up ...')
        try:
            # Close database connection first
            if hasattr(self, 'db_connection') and self.db_connection:
                self.db_connection.close()
                print("Database connection closed")
            
            # Quit pygame properly
            if pygame.get_init():
                pygame.mixer.quit()  # Quit mixer first if using sound
                pygame.display.quit()
                pygame.quit()
                print("Pygame quit successfully")
            
            if self.arduino_buttons_connected and self.arduino_buttons:
                # Arduino LED control: OFF
                self.arduino_buttons.write("4\n".encode('utf-8'))
                self.arduino_buttons.close()
                print("Arduino buttons connection closed")
            if self.arduino_reward_connected and self.arduino_reward:
                # command = "G0 X0\n"
                # self.arduino_reward.write(command.encode()) # Encode the string to bytes before
                # time.sleep(10)
                self.arduino_reward.close()
                print("Arduino Reward connection closed")
                
            # Force garbage collection
            import gc
            gc.collect()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        print("Cleanup completed")
        
            
# Run the experiment
if __name__ == "__main__":
    try:
        exp = experiment()
        exp.run() 
        
    except Exception as e:
        print(f"An error occurred: {e}")
        # print traceback and line number    
        traceback.print_exc()
    finally:
        pygame.quit()