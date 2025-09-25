# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 17:25:24 2025

@author: eemeric2
"""

import pygame
import random
import time
import sys
# import serial
# import threading
import sqlite3
import os
from datetime import datetime
# import cv2
# import numpy as np
# import math
import traceback

class experiment():
    def __init__(self):
        self.DEBUG = True # DO NOT DISPLAY TEXT FOR SUBJECTS
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

        self.gmbl_gmbl_conditions = [(7,	4,	0.5,	4,   0,  1)]
        
        if self.DEBUG:
            self.current_conditions =  self.one_opt_conditions + self.two_opt_conditions + self.gmbl_sure_conditions 
        else:
            # TODO: MAKE RANDOM
            self.current_conditions = self.one_opt_conditions + self.two_opt_conditions + self.gmbl_sure_conditions
        
        self.total_trials = len(self.current_conditions)
        self.current_trials_counter = 0
        self.total_trial_counter = 0

        print(f"{len(self.current_conditions)} trials in block)")
        
        # Initialize Pygame first to get desktop size, but don't set the mode yet
        pygame.init()
        pygame.mixer.init() # sound
        
        
        # Load sound
        try:
            self.beep_sound500 = pygame.mixer.Sound("beep500.wav")
            self.beep_sound1000 = pygame.mixer.Sound("beep1000.wav")
        except:
            print("Warning: beep.wav not found. Sound effects will be skipped.")
            self.beep_sound500 = None
            self.beep_sound1000 = None
            
        self.clock = pygame.time.Clock()      
        
        # Get the size of the primary desktop display
        desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]
        if self.DEBUG:
            self.current_conditions =  self.one_opt_conditions + self.two_opt_conditions + self.gmbl_sure_conditions 
        else:
            self.current_conditions = self.one_opt_conditions + self.two_opt_conditions + self.gmbl_sure_conditions
        
        self.total_trials = len(self.current_conditions)
        
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
            # Create a full-screen surface at your monitor's current resolution
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

        pygame.display.set_caption("Experiment")

        # Circle settings
        self.CIRCLE_RADIUS = 100
        self.LEFT_CIRCLE_POS = (self.window_width // 4, self.window_height // 2)
        self.RIGHT_CIRCLE_POS = (3 * self.window_width // 4, self.window_height // 2)
        # options configuration
        self.opt_sp_config = random.choice(['left', 'right'])
        
        # SETUP sqlite_db
        self.setup_database()

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
            
            # Remove pictures table creation:
            # cursor.execute('''CREATE TABLE IF NOT EXISTS trial_pictures ...''')
            
            self.db_connection.commit()
            print("Database table created successfully")
            
        except Exception as e:
            print(f"Database setup error: {e}")
            
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
                self.current_conditions = self.one_opt_conditions + self.two_opt_conditions + self.gmbl_sure_conditions
                self.current_trials_counter = 0
            else:
                self.current_conditions = random.sample(self.one_opt_conditions) + random.sample(self.two_opt_conditions) + random.sample(self.gmbl_sure_conditions)
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
        print("Drawing Stimuli...")
        # self.opt_sp_config = 'left'

        if self.opt_sp_config == 'left':
            self.left_color_Lose  = self.COLORS[self.lose_Amount1-1]
            self.left_color_Win   = self.COLORS[self.win_Amount1-1]
            # draw option 1 on the left 
            if self.pWin1 < 1 and self.pWin1 > 0:
                # draw full circle. color: lose amount 1
                pygame.draw.circle(self.screen, self.left_color_Lose, self.LEFT_CIRCLE_POS, self.CIRCLE_RADIUS)
            if self.pWin1 > 0:
                # draw smaller circle. color: win amount 1
                pygame.draw.circle(self.screen, self.left_color_Win, self.LEFT_CIRCLE_POS, self.CIRCLE_RADIUS*self.pWin1)

            # draw option 2 on the right
            self.right_color_Lose  = self.COLORS[self.lose_Amount2-1]
            self.right_color_Win   = self.COLORS[self.win_Amount2-1]

            if self.pWin2 < 1 and self.pWin2 > 0:
                # draw full circle. color: lose amount 1
                pygame.draw.circle(self.screen, self.right_color_Lose, self.RIGHT_CIRCLE_POS, self.CIRCLE_RADIUS)
            if self.pWin2 > 0:
                # draw smaller circle. color: win amount 1
                pygame.draw.circle(self.screen, self.right_color_Win, self.RIGHT_CIRCLE_POS, self.CIRCLE_RADIUS*self.pWin2)

        else:
            self.right_color_Lose = self.COLORS[self.lose_Amount1-1]
            self.right_color_Win = self.COLORS[self.win_Amount1-1]
            # draw option 1 on the right
            if self.pWin1 < 1 and self.pWin1 > 0:
                # draw full circle. color: lose amount 1
                pygame.draw.circle(self.screen, self.right_color_Lose, self.RIGHT_CIRCLE_POS, self.CIRCLE_RADIUS)
            if self.pWin1 > 0:
                # draw smaller circle. color: win amount 1q
                pygame.draw.circle(self.screen, self.right_color_Win, self.RIGHT_CIRCLE_POS, self.CIRCLE_RADIUS*self.pWin1)
        
            # draw option 2 on the left
            self.left_color_Lose = self.COLORS[self.lose_Amount2-1]
            self.left_color_Win = self.COLORS[self.win_Amount2-1]

            if self.pWin2 < 1 and self.pWin2 > 0:
                # draw full circle. color: lose amount 1
                pygame.draw.circle(self.screen, self.left_color_Lose, self.LEFT_CIRCLE_POS, self.CIRCLE_RADIUS)

            if self.pWin2 > 0:
                # draw smaller circle. color: win amount 1
                pygame.draw.circle(self.screen, self.left_color_Win, self.LEFT_CIRCLE_POS, self.CIRCLE_RADIUS*self.pWin2)
        
    def wait_for_response(self):
        # remove events from the event queue
        pygame.event.clear()
        print("Waiting for response")
        # get time 
        # wait till max response time
        # add option to use arduino_buttons
        # flush serial buffer so responses before stimulus onset are not registered
        # start acquiring images at 5 FPS
        if self.SIMULATE:
            print("Simulated Choice")
            self.choice = 'left'
        else:
            running = True
            while running:
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
    
    def reveal_outcome(self):
        print("Reveal Outcome")
        # Check if display is still active
        if not pygame.get_init() or pygame.display.get_surface() is None:
            return
        
        if self.choice == 'no response':
            self.screen.fill(self.BLACK)
            pygame.display.flip()
            return
   
        if self.choice == 'no response':
            self.screen.fill(self.BLACK)
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
            if self.opt_sp_config == self.choice: # chose
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
            
            pygame.draw.circle(self.screen, self.reward_color, fbloc, self.CIRCLE_RADIUS)

        pygame.display.flip()       
        self.ts_outcome_reveal = pygame.time.get_ticks()
        pygame.time.delay(500)
    
    def deliver_reward(self):
        self.ts_reward_delivered = pygame.time.get_ticks()
        print(f"Reward Magnitude, {self.reward_magnitude }")
        
        if not self.success and (self.trial_type == 'choice sure' or self.trial_type == 'no choice sure'):
            # error tone
            self.beep_sound500.play()
            pygame.time.delay(500)       

        for beeps in range(self.reward_magnitude):
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
        self.setup_new_trial()
        self.draw_stimuli()
        pygame.display.flip()
        self.ts_stimuli_on = pygame.time.get_ticks()
        
        self.wait_for_response()
        self.handle_choice()
        self.reveal_outcome()
        pygame.time.delay(250)
        self.deliver_reward()
        self.log_trial_data()
        
        # clear display wait ITI befor initiating next trial
        self.screen.fill(self.BLACK)
        pygame.display.flip()

        pygame.time.delay(self.ITI)
        
        if self.success == True: # move on to next trial if correct
            self.current_trials_counter += 1
            
    def run(self):
        print('Running: Gambling Experiment')
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