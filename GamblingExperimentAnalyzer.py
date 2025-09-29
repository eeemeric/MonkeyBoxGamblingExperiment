""" 
# Quick data loading
db_path = "your_experiment_database.db"

# Load trial data
trials = quick_load_trials(db_path)
print(trials.head())

# Load picture metadata
pictures = quick_load_pictures_metadata(db_path)
print(f"Total pictures: {len(pictures)}")

# Extract specific picture
extract_single_picture(db_path, picture_id=1, output_path="sample_picture.jpg")

# Full analysis
analyzer = GamblingExperimentAnalyzer(db_path)
analyzer.load_trial_data()
analyzer.create_visualizations()
analyzer.export_to_csv()

Usage Options:
1. Command Line with File Path:
bash
Copy code
python database_analyzer.py "path/to/your/database.db"
2. GUI File Selection (no arguments):
bash
Copy code
python database_analyzer.py
3. Quick Functions with GUI:
python
Copy code
# Load data with GUI file selector
trials = quick_load_trials()  # Opens file dialog
pictures = quick_load_pictures_metadata()  # Opens file dialog
Key GUI Features:
File Dialog: Opens native OS file picker for database selection
File Type Filtering: Shows only .db, .sqlite, .sqlite3 files by default
Error Messages: GUI popup messages for errors and completion
Fallback Support: Works without GUI (command line only) if tkinter unavailable
Cross-Platform: Works on Windows, Mac, and Linux
"""
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import cv2
from PIL import Image
import io
import sys
from scipy.optimize import curve_fit
from scipy.stats import logistic
import warnings
from sklearn.cluster import DBSCAN
from sklearn.metrics import pairwise_distances
import matplotlib.pyplot as plt
from collections import defaultdict

# GUI imports with fallback handling
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("Warning: tkinter not available. GUI file selection disabled.")

class GamblingExperimentAnalyzer:
    def __init__(self, db_path=None):
        """
        Initialize the analyzer with database path
        
        Args:
            db_path (str): Path to the SQLite database file. If None, opens GUI selector.
        """
        self.db_path = db_path
        self.connection = None
        self.trial_data = None
        self.picture_data = None
        
        # Get database path if not provided
        if self.db_path is None:
            self.db_path = self.select_database_file()
            
        if self.db_path is None:
            raise ValueError("No database file selected")
            
        # Connect to database
        self.connect_database()
    
    def select_database_file(self):
        """
        Open GUI file selector for database file
        
        Returns:
            str: Selected database file path or None if cancelled
        """
        if not GUI_AVAILABLE:
            print("GUI not available. Please provide database path as argument.")
            return None
            
        # Create root window (hidden)
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.lift()      # Bring to front
        root.attributes('-topmost', True)  # Keep on top
        
        # Configure file dialog
        file_types = [
            ('SQLite Database', '*.db'),
            ('SQLite Database', '*.sqlite'),
            ('SQLite Database', '*.sqlite3'),
            ('All Files', '*.*')
        ]
        
        # Show file selection dialog
        db_path = filedialog.askopenfilename(
            title="Select Gambling Experiment Database File",
            filetypes=file_types,
            initialdir=os.getcwd()
        )
        
        # Clean up
        root.destroy()
        
        if db_path:
            print(f"Selected database file: {db_path}")
            return db_path
        else:
            print("No file selected")
            return None
    
    def connect_database(self):
        """Connect to the SQLite database"""
        try:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database file not found: {self.db_path}")
                
            self.connection = sqlite3.connect(self.db_path)
            print(f"Successfully connected to database: {os.path.basename(self.db_path)}")
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def get_database_info(self):
        """Get information about the database structure"""
        cursor = self.connection.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("Database Tables:")
        for table in tables:
            table_name = table[0]
            print(f"\n--- {table_name} ---")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("Columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"Total rows: {count}")
    
    def load_trial_data(self):
        """Load trial data into pandas DataFrame"""
        query = """
        SELECT * FROM trial_data
        ORDER BY trial_number
        """
        
        try:
            self.trial_data = pd.read_sql_query(query, self.connection)
            print(f"Loaded {len(self.trial_data)} trials")
            return self.trial_data
        except Exception as e:
            print(f"Error loading trial data: {e}")
            return None
    
    def load_picture_data(self):
        """Load picture metadata (without image data for memory efficiency)"""
        query = """
        SELECT 
            picture_id,
            trial_number,
            timestamp,
            frame_number,
            image_width,
            image_height
        FROM trial_pictures
        ORDER BY trial_number, frame_number
        """
        
        try:
            self.picture_data = pd.read_sql_query(query, self.connection)
            print(f"Loaded metadata for {len(self.picture_data)} pictures")
            return self.picture_data
        except Exception as e:
            print(f"Error loading picture data: {e}")
            return None
    
    def get_trial_summary(self):
        """Generate summary statistics for trials"""
        if self.trial_data is None:
            self.load_trial_data()
        
        summary = {
            'total_trials': len(self.trial_data),
            'completed_trials': len(self.trial_data[self.trial_data['choice'].notna()]),
            'choice_distribution': self.trial_data['choice'].value_counts(),
            'trial_types': self.trial_data['trial_type'].value_counts(),
            'reward_distribution': self.trial_data['reward_magnitude'].value_counts(),
            'mean_reaction_time': None,
            'session_duration': None
        }
        
        # Calculate reaction times (button press - stimuli on)
        if 'ts_button_press' in self.trial_data.columns and 'ts_stimuli_on' in self.trial_data.columns:
            reaction_times = (self.trial_data['ts_button_press'] - 
                            self.trial_data['ts_stimuli_on'])
            reaction_times = reaction_times[reaction_times > 0]  # Remove invalid times
            summary['mean_reaction_time'] = reaction_times.mean()
            summary['median_reaction_time'] = reaction_times.median()
        
        # Calculate session duration
        if 'ts_trial_start' in self.trial_data.columns:
            start_time = self.trial_data['ts_trial_start'].min()
            end_time = self.trial_data['ts_trial_end'].max()
            summary['session_duration'] = (end_time - start_time) / 1000  # Convert to seconds
        
        return summary
    
    def export_to_csv(self, output_dir='exported_data'):
        """Export data to CSV files"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Export trial data
        if self.trial_data is not None:
            trial_csv_path = os.path.join(output_dir, 'trial_data.csv')
            self.trial_data.to_csv(trial_csv_path, index=False)
            print(f"Trial data exported to: {trial_csv_path}")
        
        # Export picture metadata
        if self.picture_data is not None:
            picture_csv_path = os.path.join(output_dir, 'picture_metadata.csv')
            self.picture_data.to_csv(picture_csv_path, index=False)
            print(f"Picture metadata exported to: {picture_csv_path}")
    
    def export_to_numpy(self, output_dir='exported_data'):
        """Export data to numpy arrays"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        if self.trial_data is not None:
            # Export trial data as numpy array
            trial_array = self.trial_data.to_numpy()
            trial_npy_path = os.path.join(output_dir, 'trial_data.npy')
            np.save(trial_npy_path, trial_array)
            
            # Save column names separately
            columns_path = os.path.join(output_dir, 'trial_columns.npy')
            np.save(columns_path, self.trial_data.columns.to_numpy())
            
            print(f"Trial data exported to: {trial_npy_path}")
            print(f"Column names saved to: {columns_path}")
    
    def extract_pictures(self, output_dir='extracted_pictures', trial_numbers=None):
        """
        Extract pictures from database and save as image files
        
        Args:
            output_dir (str): Directory to save pictures
            trial_numbers (list): Specific trial numbers to extract (None for all)
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        cursor = self.connection.cursor()
        
        # Build query
        if trial_numbers:
            placeholders = ','.join(['?' for _ in trial_numbers])
            query = f"""
            SELECT trial_number, frame_number, image_data, timestamp
            FROM trial_pictures 
            WHERE trial_number IN ({placeholders})
            ORDER BY trial_number, frame_number
            """
            cursor.execute(query, trial_numbers)
        else:
            query = """
            SELECT trial_number, frame_number, image_data, timestamp
            FROM trial_pictures 
            ORDER BY trial_number, frame_number
            """
            cursor.execute(query)
        
        pictures = cursor.fetchall()
        
        print(f"Extracting {len(pictures)} pictures...")
        
        for trial_num, frame_num, image_data, timestamp in pictures:
            try:
                # Convert blob to image
                image_array = np.frombuffer(image_data, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                
                # Create filename
                filename = f"trial_{trial_num:03d}_frame_{frame_num:03d}_ts_{timestamp}.jpg"
                filepath = os.path.join(output_dir, filename)
                
                # Save image
                cv2.imwrite(filepath, image)
                
            except Exception as e:
                print(f"Error extracting picture for trial {trial_num}, frame {frame_num}: {e}")
        
        print(f"Pictures extracted to: {output_dir}")
    
    def create_visualizations(self, output_dir='plots'):
        """Create visualization plots"""
        if self.trial_data is None:
            self.load_trial_data()
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Set style
        plt.style.use('seaborn-v0_8')
        
        # 1. Choice distribution
        plt.figure(figsize=(12, 8))
        
        # Check if we have valid data
        if len(self.trial_data) == 0:
            print("No trial data available for visualization")
            return
        
        plt.subplot(2, 2, 1)
        if 'choice' in self.trial_data.columns and not self.trial_data['choice'].isna().all():
            choice_counts = self.trial_data['choice'].value_counts()
            choice_counts.plot(kind='bar')
            plt.title('Choice Distribution')
            plt.xlabel('Choice')
            plt.ylabel('Count')
            plt.xticks(rotation=45)
        else:
            plt.text(0.5, 0.5, 'No choice data available', ha='center', va='center')
            plt.title('Choice Distribution')
        
        # 2. Reward magnitude distribution
        plt.subplot(2, 2, 2)
        if 'reward_magnitude' in self.trial_data.columns and not self.trial_data['reward_magnitude'].isna().all():
            reward_counts = self.trial_data['reward_magnitude'].value_counts().sort_index()
            reward_counts.plot(kind='bar')
            plt.title('Reward Magnitude Distribution')
            plt.xlabel('Reward Magnitude')
            plt.ylabel('Count')
        else:
            plt.text(0.5, 0.5, 'No reward data available', ha='center', va='center')
            plt.title('Reward Magnitude Distribution')
        
        # 3. Reaction time distribution
        plt.subplot(2, 2, 3)
        if ('ts_button_press' in self.trial_data.columns and 
            'ts_stimuli_on' in self.trial_data.columns):
            reaction_times = (self.trial_data['ts_button_press'] - 
                            self.trial_data['ts_stimuli_on'])
            reaction_times = reaction_times[(reaction_times > 0) & (reaction_times < 10000)]
            
            if len(reaction_times) > 0:
                plt.hist(reaction_times, bins=30, alpha=0.7)
                plt.title('Reaction Time Distribution')
                plt.xlabel('Reaction Time (ms)')
                plt.ylabel('Frequency')
            else:
                plt.text(0.5, 0.5, 'No valid reaction time data', ha='center', va='center')
                plt.title('Reaction Time Distribution')
        else:
            plt.text(0.5, 0.5, 'No reaction time data available', ha='center', va='center')
            plt.title('Reaction Time Distribution')
        
        # 4. Trial types
        plt.subplot(2, 2, 4)
        if 'trial_type' in self.trial_data.columns and not self.trial_data['trial_type'].isna().all():
            trial_type_counts = self.trial_data['trial_type'].value_counts()
            plt.pie(trial_type_counts.values, labels=trial_type_counts.index, autopct='%1.1f%%')
            plt.title('Trial Type Distribution')
        else:
            plt.text(0.5, 0.5, 'No trial type data available', ha='center', va='center')
            plt.title('Trial Type Distribution')
        
        plt.tight_layout()
        plot_path = os.path.join(output_dir, 'experiment_summary.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Plots saved to: {plot_path}")
    
    def analyze_performance_over_time(self):
        """Analyze performance changes over time"""
        if self.trial_data is None:
            self.load_trial_data()
        
        analysis = {}
        
        # Choice consistency over time
        if 'choice' in self.trial_data.columns:
            choices_numeric = pd.get_dummies(self.trial_data['choice'])
            if len(choices_numeric) > 0:
                window_size = min(20, len(choices_numeric))
                rolling_choices = choices_numeric.rolling(window=window_size, min_periods=1).mean()
                analysis['choice_trends'] = rolling_choices
        
        # Reaction time trends
        if ('ts_button_press' in self.trial_data.columns and 
            'ts_stimuli_on' in self.trial_data.columns):
            reaction_times = (self.trial_data['ts_button_press'] - 
                            self.trial_data['ts_stimuli_on'])
            reaction_times = reaction_times[(reaction_times > 0) & (reaction_times < 10000)]
            
            if len(reaction_times) > 0:
                window_size = min(10, len(reaction_times))
                rolling_rt = reaction_times.rolling(window=window_size, min_periods=1).mean()
                analysis['reaction_time_trend'] = rolling_rt
        
        return analysis
    
    def analyze_gamble_vs_sure_choices(self, output_dir='plots'):
        """
        For 'choice gamble sure' trials, fit logistic functions to probability of choosing gamble 
        as a function of guaranteed amount for each unique gamble option
        """
        if self.trial_data is None:
            self.load_trial_data()
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Filter for 'choice gamble sure' trials only
        gamble_sure_trials = self.trial_data[
            self.trial_data['trial_type'] == 'choice gamble sure'
        ].copy()
        
        if len(gamble_sure_trials) == 0:
            print("No 'choice gamble sure' trials found in the data")
            return
        
        print(f"Analyzing {len(gamble_sure_trials)} 'choice gamble sure' trials")
        
        # Determine which option was the gamble and which was sure
        gamble_sure_trials['gamble_win_amount'] = gamble_sure_trials['win_Amount1']
        gamble_sure_trials['gamble_lose_amount'] = gamble_sure_trials['lose_Amount1'] 
        gamble_sure_trials['gamble_prob'] = gamble_sure_trials['pWin1']
        gamble_sure_trials['sure_amount'] = gamble_sure_trials['win_Amount2']
        
        # Calculate expected value of gamble
        gamble_sure_trials['gamble_ev'] = (
            gamble_sure_trials['gamble_win_amount'] * gamble_sure_trials['gamble_prob'] +
            gamble_sure_trials['gamble_lose_amount'] * (1 - gamble_sure_trials['gamble_prob'])
        )
        
        # Create gamble option identifier
        gamble_sure_trials['gamble_option'] = (
            'Win: ' + gamble_sure_trials['gamble_win_amount'].astype(str) + 
            ', Lose: ' + gamble_sure_trials['gamble_lose_amount'].astype(str) + 
            ', P: ' + gamble_sure_trials['gamble_prob'].astype(str)
        )
        
        # Determine if gamble was chosen
        gamble_sure_trials['chose_gamble'] = (
            gamble_sure_trials['options_spacial_config'] == gamble_sure_trials['choice']
        )
        
        # Get unique gamble options
        unique_gambles = sorted(gamble_sure_trials['gamble_option'].unique())
        
        print(f"\nFound {len(unique_gambles)} unique gamble options:")
        for i, gamble in enumerate(unique_gambles):
            count = len(gamble_sure_trials[gamble_sure_trials['gamble_option'] == gamble])
            print(f"  {i+1}. {gamble} ({count} trials)")
        
        # Define logistic function
        def logistic_function(x, b0, b1):
            """Logistic function: P(G) = 1 / (1 + exp(-(b0 + b1*x)))"""
            return 1 / (1 + np.exp(-(b0 + b1 * x)))
        
        # Store fit results
        fit_results = {}
        
        # Create the main plot
        plt.figure(figsize=(16, 12))
        
        # Plot 1: Logistic fits vs guaranteed amount
        plt.subplot(2, 2, 1)
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(unique_gambles)))
        
        for i, gamble_option in enumerate(unique_gambles):
            # Filter data for this gamble option
            gamble_data = gamble_sure_trials[
                gamble_sure_trials['gamble_option'] == gamble_option
            ].copy()
            
            print(f"\nAnalyzing: {gamble_option}")
            print(f"Total trials: {len(gamble_data)}")
            
            # Group by sure amount and calculate probability of choosing gamble
            prob_data = gamble_data.groupby('sure_amount').agg({
                'chose_gamble': ['mean', 'count', 'sum']
            }).round(4)
            
            prob_data.columns = ['prob_choose_gamble', 'n_trials', 'n_chose_gamble']
            prob_data = prob_data.reset_index()
            
            if len(prob_data) > 2:  # Need at least 3 points for fitting
                # Get gamble expected value (constant for this gamble option)
                gamble_ev = gamble_data['gamble_ev'].iloc[0]
                
                # Fit logistic regression using guaranteed amount as predictor
                x_data = prob_data['sure_amount'].values
                y_data = prob_data['prob_choose_gamble'].values
                
                # Remove any NaN or extreme values
                valid_mask = ~np.isnan(y_data) & (y_data >= 0) & (y_data <= 1)
                x_data = x_data[valid_mask]
                y_data = y_data[valid_mask]
                
                if len(x_data) > 2:
                    try:
                        # Fit logistic curve
                        # Initial parameter guesses
                        p0 = [0, -1]  # b0, b1
                        
                        # Fit with bounds to ensure reasonable parameters
                        bounds = ([-10, -10], [10, 10])
                        popt, pcov = curve_fit(logistic_function, x_data, y_data, 
                                            p0=p0, bounds=bounds, maxfev=5000)
                        
                        b0, b1 = popt
                        
                        # Calculate subjective value (where P(G) = 0.5)
                        # 0.5 = 1 / (1 + exp(-(b0 + b1*SV)))
                        # ln(1) = -(b0 + b1*SV)
                        # 0 = -(b0 + b1*SV)
                        # SV = -b0/b1
                        if b1 != 0:
                            subjective_value = -b0 / b1
                        else:
                            subjective_value = np.nan
                        
                        # Store results
                        fit_results[gamble_option] = {
                            'b0': b0,
                            'b1': b1,
                            'subjective_value': subjective_value,
                            'gamble_ev': gamble_ev,
                            'r_squared': None  # Will calculate below
                        }
                        
                        # Calculate R-squared
                        y_pred = logistic_function(x_data, b0, b1)
                        ss_res = np.sum((y_data - y_pred) ** 2)
                        ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)
                        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                        fit_results[gamble_option]['r_squared'] = r_squared
                        
                        # Plot data points
                        plt.scatter(x_data, y_data, color=colors[i], s=80, alpha=0.7, 
                                label=f'{gamble_option}')
                        
                        # Plot fitted curve
                        x_smooth = np.linspace(x_data.min() - 0.5, x_data.max() + 0.5, 100)
                        y_smooth = logistic_function(x_smooth, b0, b1)
                        plt.plot(x_smooth, y_smooth, color=colors[i], linewidth=2, alpha=0.8)
                        
                        # Mark subjective value
                        if not np.isnan(subjective_value) and x_data.min() <= subjective_value <= x_data.max():
                            plt.axvline(x=subjective_value, color=colors[i], linestyle='--', alpha=0.5)
                            plt.text(subjective_value, 0.5, f'SV={subjective_value:.2f}', 
                                rotation=90, color=colors[i], fontsize=8)
                        
                        # Add data point annotations
                        for _, row in prob_data.iterrows():
                            if row['sure_amount'] in x_data:
                                plt.annotate(f"{row['n_chose_gamble']:.0f}/{row['n_trials']:.0f}", 
                                        (row['sure_amount'], row['prob_choose_gamble']),
                                        xytext=(5, 5), textcoords='offset points', 
                                        fontsize=7, alpha=0.6)
                        
                        print(f"Logistic fit: b0={b0:.3f}, b1={b1:.3f}, SV={subjective_value:.3f}, R²={r_squared:.3f}")
                        
                    except Exception as e:
                        print(f"Could not fit logistic curve for {gamble_option}: {e}")
                        # Plot raw data without fit
                        plt.scatter(x_data, y_data, color=colors[i], s=80, alpha=0.7, 
                                label=f'{gamble_option} (no fit)')
                else:
                    print(f"Not enough valid data points for {gamble_option}")
        
        plt.xlabel('Guaranteed Amount (Sure Option)', fontsize=12)
        plt.ylabel('Probability of Choosing Gamble', fontsize=12)
        plt.title('Logistic Fits: P(Gamble) vs Guaranteed Amount', fontsize=14, fontweight='bold')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
        plt.grid(True, alpha=0.3)
        plt.ylim(-0.05, 1.05)
        plt.axhline(y=0.5, color='black', linestyle=':', alpha=0.5, label='P(G) = 0.5')
        
        # Plot 2: Logistic fits vs Expected Value difference
        plt.subplot(2, 2, 2)
        
        for i, gamble_option in enumerate(unique_gambles):
            gamble_data = gamble_sure_trials[
                gamble_sure_trials['gamble_option'] == gamble_option
            ]
            
            if len(gamble_data) > 0:
                gamble_ev = gamble_data['gamble_ev'].iloc[0]
                
                prob_data = gamble_data.groupby('sure_amount').agg({
                    'chose_gamble': ['mean', 'count']
                }).round(4)
                prob_data.columns = ['prob_choose_gamble', 'n_trials']
                prob_data = prob_data.reset_index()
                
                # Calculate EV difference (Gamble EV - Sure Amount)
                prob_data['ev_difference'] = gamble_ev - prob_data['sure_amount']
                
                if len(prob_data) > 2:
                    x_data = prob_data['ev_difference'].values
                    y_data = prob_data['prob_choose_gamble'].values
                    
                    valid_mask = ~np.isnan(y_data) & (y_data >= 0) & (y_data <= 1)
                    x_data = x_data[valid_mask]
                    y_data = y_data[valid_mask]
                    
                    if len(x_data) > 2:
                        try:
                            # Fit logistic curve to EV difference
                            popt, _ = curve_fit(logistic_function, x_data, y_data, 
                                            p0=[0, 1], bounds=([-10, -10], [10, 10]), maxfev=5000)
                            b0_ev, b1_ev = popt
                            
                            # Plot data points
                            plt.scatter(x_data, y_data, color=colors[i], s=80, alpha=0.7)
                            
                            # Plot fitted curve
                            x_smooth = np.linspace(x_data.min() - 0.5, x_data.max() + 0.5, 100)
                            y_smooth = logistic_function(x_smooth, b0_ev, b1_ev)
                            plt.plot(x_smooth, y_smooth, color=colors[i], linewidth=2, alpha=0.8,
                                label=f'{gamble_option}')
                            
                        except Exception as e:
                            plt.scatter(x_data, y_data, color=colors[i], s=80, alpha=0.7,
                                    label=f'{gamble_option} (no fit)')
        
        plt.axvline(x=0, color='black', linestyle='--', alpha=0.5, label='Equal EV')
        plt.axhline(y=0.5, color='black', linestyle=':', alpha=0.5)
        plt.xlabel('Expected Value Difference (Gamble EV - Sure Amount)', fontsize=12)
        plt.ylabel('Probability of Choosing Gamble', fontsize=12)
        plt.title('Logistic Fits: P(Gamble) vs EV Difference', fontsize=14)
        plt.legend(fontsize=9)
        plt.grid(True, alpha=0.3)
        plt.ylim(-0.05, 1.05)
        
        # Plot 3: Subjective values vs Expected values
        plt.subplot(2, 2, 3)
        
        if fit_results:
            gamble_evs = []
            subjective_values = []
            labels = []
            
            for i, (gamble_option, results) in enumerate(fit_results.items()):
                if not np.isnan(results['subjective_value']):
                    gamble_evs.append(results['gamble_ev'])
                    subjective_values.append(results['subjective_value'])
                    labels.append(f"G{i+1}")
            
            if len(gamble_evs) > 0:
                plt.scatter(gamble_evs, subjective_values, s=100, alpha=0.7)
                
                # Add labels
                for i, label in enumerate(labels):
                    plt.annotate(label, (gamble_evs[i], subjective_values[i]), 
                            xytext=(5, 5), textcoords='offset points', fontsize=10)
                
                # Plot unity line
                min_val = min(min(gamble_evs), min(subjective_values))
                max_val = max(max(gamble_evs), max(subjective_values))
                plt.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='Unity')
                
                plt.xlabel('Gamble Expected Value', fontsize=12)
                plt.ylabel('Subjective Value (P(G) = 0.5)', fontsize=12)
                plt.title('Subjective vs Expected Values', fontsize=14)
                plt.legend()
                plt.grid(True, alpha=0.3)
        
        # Plot 4: Fit parameters table
        plt.subplot(2, 2, 4)
        plt.axis('off')
        
        if fit_results:
            table_data = []
            for i, (gamble_option, results) in enumerate(fit_results.items()):
                table_data.append([
                    f"G{i+1}",
                    f"{results['b0']:.3f}",
                    f"{results['b1']:.3f}",
                    f"{results['subjective_value']:.2f}" if not np.isnan(results['subjective_value']) else "N/A",
                    f"{results['gamble_ev']:.2f}",
                    f"{results['r_squared']:.3f}" if results['r_squared'] is not None else "N/A"
                ])
            
            table = plt.table(cellText=table_data,
                            colLabels=['Gamble', 'b₀', 'b₁', 'Subj. Value', 'Gamble EV', 'R²'],
                            cellLoc='center',
                            loc='center',
                            bbox=[0, 0, 1, 1])
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 2)
            
            # Style the table
            for i in range(len(table_data) + 1):
                for j in range(6):
                    cell = table[(i, j)]
                    if i == 0:  # Header
                        cell.set_facecolor('#4CAF50')
                        cell.set_text_props(weight='bold', color='white')
                    else:
                        cell.set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
            
            plt.title('Logistic Regression Parameters', fontsize=12, pad=20)
        
        plt.suptitle('Logistic Regression Analysis: Gamble vs Sure Choices', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # Save plot
        plot_path = os.path.join(output_dir, 'logistic_gamble_vs_sure_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"\nLogistic regression analysis plot saved to: {plot_path}")
        
        # Print detailed results
        print("\n" + "="*80)
        print("LOGISTIC REGRESSION RESULTS")
        print("="*80)
        print("Model: log[P(G)/(1-P(G))] = b₀ + b₁ * Sure_Amount")
        print("Subjective Value = -b₀/b₁ (where P(G) = 0.5)")
        print("-"*80)
        
        for i, (gamble_option, results) in enumerate(fit_results.items()):
            print(f"\nGamble Option {i+1}: {gamble_option}")
            print(f"  Expected Value: {results['gamble_ev']:.3f}")
            print(f"  b₀ (intercept): {results['b0']:.3f}")
            print(f"  b₁ (slope):     {results['b1']:.3f}")
            print(f"  Subjective Value: {results['subjective_value']:.3f}")
            print(f"  R²:             {results['r_squared']:.3f}")
            
            # Interpretation
            if results['subjective_value'] > results['gamble_ev']:
                print(f"  → Risk-seeking behavior (SV > EV)")
            elif results['subjective_value'] < results['gamble_ev']:
                print(f"  → Risk-averse behavior (SV < EV)")
            else:
                print(f"  → Risk-neutral behavior (SV ≈ EV)")
        
        return gamble_sure_trials, fit_results

    def identify_unique_subjects_from_images(self, output_dir='subject_analysis'):
        """
        Identify unique subjects from captured trial images using face recognition
        and track which trials each subject appears in
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Load face detection and recognition models
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Try to load face recognition model (requires dlib and face_recognition)
        try:
            import face_recognition
            USE_FACE_RECOGNITION = True
            print("Using face_recognition library for subject identification")
        except ImportError:
            USE_FACE_RECOGNITION = False
            print("face_recognition library not available. Using basic face detection and feature matching.")
        
        # Load picture data from database
        cursor = self.connection.cursor()
        
        # Get all pictures with image data
        query = """
        SELECT picture_id, trial_number, frame_number, image_data, timestamp
        FROM trial_pictures 
        ORDER BY trial_number, frame_number
        """
        cursor.execute(query)
        pictures = cursor.fetchall()
        
        if len(pictures) == 0:
            print("No pictures found in database")
            return None
        
        print(f"Analyzing {len(pictures)} pictures for subject identification...")
        
        # Store face data for each picture
        face_data = []
        valid_pictures = []
        
        # Process each picture
        for i, (picture_id, trial_number, frame_number, image_data, timestamp) in enumerate(pictures):
            if i % 50 == 0:
                print(f"Processing picture {i+1}/{len(pictures)}")
            
            try:
                # Convert blob to image
                image_array = np.frombuffer(image_data, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                
                if image is None:
                    continue
                
                if USE_FACE_RECOGNITION:
                    # Use face_recognition library
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    
                    # Find face locations
                    face_locations = face_recognition.face_locations(rgb_image)
                    
                    if len(face_locations) > 0:
                        # Get face encodings
                        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                        
                        for j, (encoding, location) in enumerate(zip(face_encodings, face_locations)):
                            face_data.append({
                                'picture_id': picture_id,
                                'trial_number': trial_number,
                                'frame_number': frame_number,
                                'timestamp': timestamp,
                                'face_encoding': encoding,
                                'face_location': location,
                                'face_index': j,
                                'method': 'face_recognition'
                            })
                            valid_pictures.append((picture_id, trial_number, frame_number, image))
                
                else:
                    # Use OpenCV face detection with feature extraction
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(50, 50))
                    
                    for j, (x, y, w, h) in enumerate(faces):
                        # Extract face region
                        face_roi = gray[y:y+h, x:x+w]
                        
                        # Resize to standard size for comparison
                        face_roi_resized = cv2.resize(face_roi, (100, 100))
                        
                        # Extract features using histogram
                        hist_features = cv2.calcHist([face_roi_resized], [0], None, [256], [0, 256]).flatten()
                        
                        # Extract LBP features (Local Binary Patterns)
                        lbp_features = self._extract_lbp_features(face_roi_resized)
                        
                        # Combine features
                        combined_features = np.concatenate([hist_features, lbp_features])
                        
                        face_data.append({
                            'picture_id': picture_id,
                            'trial_number': trial_number,
                            'frame_number': frame_number,
                            'timestamp': timestamp,
                            'face_encoding': combined_features,
                            'face_location': (x, y, w, h),
                            'face_index': j,
                            'method': 'opencv_features'
                        })
                        valid_pictures.append((picture_id, trial_number, frame_number, image))
            
            except Exception as e:
                print(f"Error processing picture {picture_id}: {e}")
                continue
        
        if len(face_data) == 0:
            print("No faces detected in any pictures")
            return None
        
        print(f"Found {len(face_data)} face instances across {len(set([f['trial_number'] for f in face_data]))} trials")
        
        # Cluster faces to identify unique subjects
        face_encodings = np.array([face['face_encoding'] for face in face_data])
        
        if USE_FACE_RECOGNITION:
            # Use face_recognition distance metric
            distances = pairwise_distances(face_encodings, metric='euclidean')
            # Use DBSCAN clustering
            clustering = DBSCAN(eps=0.6, min_samples=2, metric='precomputed')
            cluster_labels = clustering.fit_predict(distances)
        else:
            # Use cosine similarity for feature vectors
            clustering = DBSCAN(eps=0.3, min_samples=2, metric='cosine')
            cluster_labels = clustering.fit_predict(face_encodings)
        
        # Assign cluster labels to face data
        for i, face in enumerate(face_data):
            face['subject_id'] = cluster_labels[i]
        
        # Analyze results
        unique_subjects = set(cluster_labels)
        if -1 in unique_subjects:
            unique_subjects.remove(-1)  # Remove noise cluster
        
        print(f"Identified {len(unique_subjects)} unique subjects")
        print(f"Number of unclassified faces (noise): {sum(1 for label in cluster_labels if label == -1)}")
        
        # Create subject analysis
        subject_analysis = {}
        
        for subject_id in unique_subjects:
            subject_faces = [face for face in face_data if face['subject_id'] == subject_id]
            
            # Get trials for this subject
            subject_trials = sorted(set([face['trial_number'] for face in subject_faces]))
            
            # Calculate statistics
            total_appearances = len(subject_faces)
            trials_present = len(subject_trials)
            
            # Get time range
            timestamps = [face['timestamp'] for face in subject_faces]
            time_range = (min(timestamps), max(timestamps))
            
            subject_analysis[subject_id] = {
                'total_face_detections': total_appearances,
                'trials_present': subject_trials,
                'num_trials': trials_present,
                'time_range': time_range,
                'faces': subject_faces
            }
        
        # Create visualizations
        self._create_subject_analysis_plots(subject_analysis, face_data, valid_pictures, output_dir)
        
        # Print detailed analysis
        print("\n" + "="*80)
        print("SUBJECT IDENTIFICATION ANALYSIS")
        print("="*80)
        
        for subject_id in sorted(unique_subjects):
            analysis = subject_analysis[subject_id]
            print(f"\nSubject {subject_id}:")
            print(f"  Total face detections: {analysis['total_face_detections']}")
            print(f"  Number of trials present: {analysis['num_trials']}")
            print(f"  Trials: {analysis['trials_present']}")
            print(f"  Time range: {analysis['time_range'][0]} - {analysis['time_range'][1]} ms")
            
            # Calculate trial participation rate
            if hasattr(self, 'trial_data') and self.trial_data is not None:
                total_trials = len(self.trial_data)
                participation_rate = (analysis['num_trials'] / total_trials) * 100
                print(f"  Participation rate: {participation_rate:.1f}% ({analysis['num_trials']}/{total_trials} trials)")
        
        # Analyze trial overlap between subjects
        print(f"\n--- TRIAL OVERLAP ANALYSIS ---")
        subject_ids = sorted(unique_subjects)
        
        for i, subj1 in enumerate(subject_ids):
            for subj2 in subject_ids[i+1:]:
                trials1 = set(subject_analysis[subj1]['trials_present'])
                trials2 = set(subject_analysis[subj2]['trials_present'])
                
                overlap = trials1.intersection(trials2)
                if len(overlap) > 0:
                    print(f"Subjects {subj1} and {subj2} both present in {len(overlap)} trials: {sorted(overlap)}")

        # Create summary table
        self._create_subject_summary_table(subject_analysis, output_dir)
        
        return subject_analysis, face_data

    def _create_subject_analysis_plots(self, subject_analysis, face_data, valid_pictures, output_dir):
        """Create visualization plots for subject analysis including example images"""
        
        # Create a mapping from picture_id to image
        picture_dict = {pic_id: img for pic_id, trial, frame, img in valid_pictures}
        
        # Calculate number of subjects for layout
        n_subjects = len(subject_analysis)
        if n_subjects == 0:
            return
        
        # Create main analysis figure
        fig = plt.figure(figsize=(20, 16))
        
        # Plot 1: Subject presence across trials (top left)
        ax1 = plt.subplot(3, 3, 1)
        
        colors = plt.cm.tab10(np.linspace(0, 1, n_subjects))
        
        for i, (subject_id, analysis) in enumerate(subject_analysis.items()):
            trials = analysis['trials_present']
            y_pos = [subject_id] * len(trials)
            ax1.scatter(trials, y_pos, alpha=0.7, s=50, color=colors[i], 
                    label=f'Subject {subject_id}')
        
        ax1.set_xlabel('Trial Number')
        ax1.set_ylabel('Subject ID')
        ax1.set_title('Subject Presence Across Trials')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Subject participation summary (top middle)
        ax2 = plt.subplot(3, 3, 2)
        
        subject_ids = list(subject_analysis.keys())
        trial_counts = [analysis['num_trials'] for analysis in subject_analysis.values()]
        detection_counts = [analysis['total_face_detections'] for analysis in subject_analysis.values()]
        
        x = np.arange(len(subject_ids))
        width = 0.35
        
        ax2.bar(x - width/2, trial_counts, width, label='Trials Present', alpha=0.7, color='skyblue')
        ax2.bar(x + width/2, detection_counts, width, label='Total Detections', alpha=0.7, color='lightcoral')
        
        ax2.set_xlabel('Subject ID')
        ax2.set_ylabel('Count')
        ax2.set_title('Subject Participation Summary')
        ax2.set_xticks(x)
        ax2.set_xticklabels([f'Subject {sid}' for sid in subject_ids])
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Trial overlap heatmap (top right)
        ax3 = plt.subplot(3, 3, 3)
        
        if len(subject_ids) > 1:
            overlap_matrix = np.zeros((len(subject_ids), len(subject_ids)))
            
            for i, subj1 in enumerate(subject_ids):
                for j, subj2 in enumerate(subject_ids):
                    if i != j:
                        trials1 = set(subject_analysis[subj1]['trials_present'])
                        trials2 = set(subject_analysis[subj2]['trials_present'])
                        overlap = len(trials1.intersection(trials2))
                        overlap_matrix[i, j] = overlap
                    else:
                        overlap_matrix[i, j] = subject_analysis[subj1]['num_trials']
            
            im = ax3.imshow(overlap_matrix, cmap='Blues')
            ax3.set_xticks(range(len(subject_ids)))
            ax3.set_yticks(range(len(subject_ids)))
            ax3.set_xticklabels([f'S{sid}' for sid in subject_ids])
            ax3.set_yticklabels([f'S{sid}' for sid in subject_ids])
            ax3.set_title('Trial Overlap Between Subjects')
            
            # Add text annotations
            for i in range(len(subject_ids)):
                for j in range(len(subject_ids)):
                    ax3.text(j, i, f'{int(overlap_matrix[i, j])}', 
                            ha='center', va='center')
            
            plt.colorbar(im, ax=ax3)
        else:
            ax3.text(0.5, 0.5, 'Only one subject\nidentified', ha='center', va='center', 
                    transform=ax3.transAxes, fontsize=12)
            ax3.set_title('Trial Overlap Between Subjects')
        
        # Plot 4: Detection timeline (middle left)
        ax4 = plt.subplot(3, 3, 4)
        
        for i, (subject_id, analysis) in enumerate(subject_analysis.items()):
            timestamps = [face['timestamp'] for face in analysis['faces']]
            
            ax4.scatter(timestamps, [subject_id] * len(timestamps), 
                    alpha=0.6, s=30, color=colors[i], label=f'Subject {subject_id}')
        
        ax4.set_xlabel('Timestamp (ms)')
        ax4.set_ylabel('Subject ID')
        ax4.set_title('Detection Timeline')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # Plot 5: Trial range visualization (middle middle)
        ax5 = plt.subplot(3, 3, 5)
        
        for i, (subject_id, analysis) in enumerate(subject_analysis.items()):
            trials = analysis['trials_present']
            if len(trials) > 0:
                min_trial = min(trials)
                max_trial = max(trials)
                
                # Draw range bar
                ax5.barh(subject_id, max_trial - min_trial + 1, left=min_trial, 
                        alpha=0.6, color=colors[i], height=0.6)
                
                # Add text annotation
                ax5.text(min_trial + (max_trial - min_trial) / 2, subject_id, 
                        f'{min_trial}-{max_trial}', ha='center', va='center', 
                        fontweight='bold', fontsize=10)
        
        ax5.set_xlabel('Trial Number')
        ax5.set_ylabel('Subject ID')
        ax5.set_title('Trial Range for Each Subject')
        ax5.grid(True, alpha=0.3)
        
        # Plots 6-9: Example face images for each subject
        available_positions = [(3, 3, 6), (3, 3, 7), (3, 3, 8), (3, 3, 9)]
        
        for i, (subject_id, analysis) in enumerate(subject_analysis.items()):
            if i >= len(available_positions):
                break  # Only show first 4 subjects in this layout
                
            ax_pos = available_positions[i]
            ax = plt.subplot(*ax_pos)
            
            # Get the best quality face image for this subject
            best_face = None
            best_size = 0
            
            for face_info in analysis['faces']:
                picture_id = face_info['picture_id']
                
                if picture_id in picture_dict:
                    image = picture_dict[picture_id]
                    
                    # Extract face region
                    if face_info['method'] == 'face_recognition':
                        top, right, bottom, left = face_info['face_location']
                        face_crop = image[top:bottom, left:right]
                    else:
                        x, y, w, h = face_info['face_location']
                        face_crop = image[y:y+h, x:x+w]
                    
                    # Check if this is the largest/best quality face so far
                    face_size = face_crop.shape[0] * face_crop.shape[1]
                    if face_size > best_size:
                        best_size = face_size
                        best_face = {
                            'image': face_crop,
                            'trial': face_info['trial_number'],
                            'frame': face_info['frame_number']
                        }
            
            if best_face is not None:
                # Display the face image
                face_rgb = cv2.cvtColor(best_face['image'], cv2.COLOR_BGR2RGB)
                ax.imshow(face_rgb)
                ax.set_title(f'Subject {subject_id}\nTrial {best_face["trial"]}, Frame {best_face["frame"]}', 
                            fontsize=10, fontweight='bold')
                ax.axis('off')
                
                # Add border with subject color
                for spine in ax.spines.values():
                    spine.set_edgecolor(colors[i])
                    spine.set_linewidth(3)
            else:
                ax.text(0.5, 0.5, f'Subject {subject_id}\nNo image available', 
                    ha='center', va='center', transform=ax.transAxes, fontsize=10)
                ax.set_title(f'Subject {subject_id}', fontsize=10, fontweight='bold')
                ax.axis('off')
        
        plt.suptitle('Subject Identification Analysis', fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # Save main analysis plot
        plot_path = os.path.join(output_dir, 'subject_identification_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        # Create a separate detailed subject gallery if there are many subjects
        if n_subjects > 4:
            self._create_subject_gallery(subject_analysis, picture_dict, colors, output_dir)
        
        print(f"Subject analysis plots saved to: {plot_path}")

    def _create_subject_gallery(self, subject_analysis, picture_dict, colors, output_dir):
        """Create a detailed gallery showing all subjects with their information"""
        
        n_subjects = len(subject_analysis)
        
        # Calculate grid layout
        cols = min(4, n_subjects)
        rows = (n_subjects + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 6*rows))
        if rows == 1 and cols == 1:
            axes = [axes]
        elif rows == 1 or cols == 1:
            axes = axes.flatten()
        else:
            axes = axes.flatten()
        
        for i, (subject_id, analysis) in enumerate(subject_analysis.items()):
            ax = axes[i]
            
            # Get the best quality face image for this subject
            best_face = None
            best_size = 0
            
            for face_info in analysis['faces']:
                picture_id = face_info['picture_id']
                
                if picture_id in picture_dict:
                    image = picture_dict[picture_id]
                    
                    # Extract face region
                    if face_info['method'] == 'face_recognition':
                        top, right, bottom, left = face_info['face_location']
                        face_crop = image[top:bottom, left:right]
                    else:
                        x, y, w, h = face_info['face_location']
                        face_crop = image[y:y+h, x:x+w]
                    
                    # Check if this is the largest/best quality face so far
                    face_size = face_crop.shape[0] * face_crop.shape[1]
                    if face_size > best_size:
                        best_size = face_size
                        best_face = {
                            'image': face_crop,
                            'trial': face_info['trial_number'],
                            'frame': face_info['frame_number']
                        }
            
            if best_face is not None:
                # Display the face image
                face_rgb = cv2.cvtColor(best_face['image'], cv2.COLOR_BGR2RGB)
                ax.imshow(face_rgb)
                
                # Create detailed title with statistics
                trials = analysis['trials_present']
                trial_range = f"{min(trials)}-{max(trials)}" if len(trials) > 1 else str(trials[0])
                
                title = (f'Subject {subject_id}\n'
                        f'Trials: {trial_range}\n'
                        f'Present in {analysis["num_trials"]} trials\n'
                        f'{analysis["total_face_detections"]} detections')
                
                ax.set_title(title, fontsize=10, fontweight='bold')
                ax.axis('off')
                
                # Add colored border
                for spine in ax.spines.values():
                    spine.set_edgecolor(colors[i % len(colors)])
                    spine.set_linewidth(3)
            else:
                trials = analysis['trials_present']
                trial_range = f"{min(trials)}-{max(trials)}" if len(trials) > 1 else str(trials[0])
                
                ax.text(0.5, 0.5, 
                    f'Subject {subject_id}\n'
                    f'Trials: {trial_range}\n'
                    f'Present in {analysis["num_trials"]} trials\n'
                    f'{analysis["total_face_detections"]} detections\n\n'
                    f'No image available', 
                    ha='center', va='center', transform=ax.transAxes, 
                    fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
                ax.set_title(f'Subject {subject_id}', fontsize=12, fontweight='bold')
                ax.axis('off')
        
        # Hide unused subplots
        for i in range(n_subjects, len(axes)):
            axes[i].axis('off')
        
        plt.suptitle('Complete Subject Gallery', fontsize=16, fontweight='bold')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # Save gallery plot
        gallery_path = os.path.join(output_dir, 'subject_gallery.png')
        plt.savefig(gallery_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Subject gallery saved to: {gallery_path}")

    def _create_subject_summary_table(self, subject_analysis, output_dir):
        """Create a summary table of all subjects and their trial participation"""
        
        # Create summary table figure
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.axis('tight')
        ax.axis('off')
        
        # Prepare table data
        table_data = []
        headers = ['Subject ID', 'Trial Range', 'Trials Present', 'Total Detections', 
                'First Detection (ms)', 'Last Detection (ms)', 'Participation Rate (%)']
        
        # Calculate total trials if trial_data is available
        total_trials = len(self.trial_data) if hasattr(self, 'trial_data') and self.trial_data is not None else None
        
        for subject_id, analysis in sorted(subject_analysis.items()):
            trials = analysis['trials_present']
            trial_range = f"{min(trials)}-{max(trials)}" if len(trials) > 1 else str(trials[0])
            
            # Calculate participation rate
            if total_trials:
                participation_rate = (analysis['num_trials'] / total_trials) * 100
                participation_str = f"{participation_rate:.1f}%"
            else:
                participation_str = "N/A"
            
            # Get time range
            timestamps = [face['timestamp'] for face in analysis['faces']]
            first_detection = min(timestamps)
            last_detection = max(timestamps)
            
            table_data.append([
                f"Subject {subject_id}",
                trial_range,
                str(analysis['num_trials']),
                str(analysis['total_face_detections']),
                str(first_detection),
                str(last_detection),
                participation_str
            ])
        
        # Create table
        table = ax.table(cellText=table_data,
                        colLabels=headers,
                        cellLoc='center',
                        loc='center',
                        bbox=[0, 0, 1, 1])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # Style the table
        for i in range(len(table_data) + 1):
            for j in range(len(headers)):
                cell = table[(i, j)]
                if i == 0:  # Header
                    cell.set_facecolor('#4CAF50')
                    cell.set_text_props(weight='bold', color='white')
                else:
                    cell.set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
        
        plt.title('Subject Participation Summary Table', fontsize=14, fontweight='bold', pad=20)
        
        # Save table
        table_path = os.path.join(output_dir, 'subject_summary_table.png')
        plt.savefig(table_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Subject summary table saved to: {table_path}")

    def _extract_lbp_features(self, image, radius=1, n_points=8):
        """Extract Local Binary Pattern features from face image"""
        def local_binary_pattern(image, radius, n_points):
            # Simple LBP implementation
            h, w = image.shape
            lbp = np.zeros_like(image)
            
            for i in range(radius, h - radius):
                for j in range(radius, w - radius):
                    center = image[i, j]
                    binary_string = ''
                    
                    # Sample points around the center
                    for k in range(n_points):
                        angle = 2 * np.pi * k / n_points
                        x = int(i + radius * np.cos(angle))
                        y = int(j + radius * np.sin(angle))
                        
                        if 0 <= x < h and 0 <= y < w:
                            binary_string += '1' if image[x, y] >= center else '0'
                        else:
                            binary_string += '0'
                    
                    lbp[i, j] = int(binary_string, 2)
            
            return lbp
        
        lbp_image = local_binary_pattern(image, radius, n_points)
        
        # Calculate histogram of LBP values
        hist, _ = np.histogram(lbp_image.flatten(), bins=2**n_points, range=(0, 2**n_points))
        
        # Normalize histogram
        hist = hist.astype(float)
        hist /= (hist.sum() + 1e-7)
        
        return hist

    def _create_subject_analysis_plots(self, subject_analysis, face_data, valid_pictures, output_dir):
        """Create visualization plots for subject analysis"""
        
        # Plot 1: Subject presence across trials
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Trial participation timeline
        ax1 = axes[0, 0]
        
        for subject_id, analysis in subject_analysis.items():
            trials = analysis['trials_present']
            y_pos = [subject_id] * len(trials)
            ax1.scatter(trials, y_pos, alpha=0.7, s=50, label=f'Subject {subject_id}')
        
        ax1.set_xlabel('Trial Number')
        ax1.set_ylabel('Subject ID')
        ax1.set_title('Subject Presence Across Trials')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Subject participation summary
        ax2 = axes[0, 1]
        
        subject_ids = list(subject_analysis.keys())
        trial_counts = [analysis['num_trials'] for analysis in subject_analysis.values()]
        detection_counts = [analysis['total_face_detections'] for analysis in subject_analysis.values()]
        
        x = np.arange(len(subject_ids))
        width = 0.35
        
        ax2.bar(x - width/2, trial_counts, width, label='Trials Present', alpha=0.7)
        ax2.bar(x + width/2, detection_counts, width, label='Total Detections', alpha=0.7)
        
        ax2.set_xlabel('Subject ID')
        ax2.set_ylabel('Count')
        ax2.set_title('Subject Participation Summary')
        ax2.set_xticks(x)
        ax2.set_xticklabels([f'Subject {sid}' for sid in subject_ids])
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Trial overlap heatmap
        ax3 = axes[1, 0]
        
        if len(subject_ids) > 1:
            overlap_matrix = np.zeros((len(subject_ids), len(subject_ids)))
            
            for i, subj1 in enumerate(subject_ids):
                for j, subj2 in enumerate(subject_ids):
                    if i != j:
                        trials1 = set(subject_analysis[subj1]['trials_present'])
                        trials2 = set(subject_analysis[subj2]['trials_present'])
                        overlap = len(trials1.intersection(trials2))
                        overlap_matrix[i, j] = overlap
                    else:
                        overlap_matrix[i, j] = subject_analysis[subj1]['num_trials']
            
            im = ax3.imshow(overlap_matrix, cmap='Blues')
            ax3.set_xticks(range(len(subject_ids)))
            ax3.set_yticks(range(len(subject_ids)))
            ax3.set_xticklabels([f'S{sid}' for sid in subject_ids])
            ax3.set_yticklabels([f'S{sid}' for sid in subject_ids])
            ax3.set_title('Trial Overlap Between Subjects')
            
            # Add text annotations
            for i in range(len(subject_ids)):
                for j in range(len(subject_ids)):
                    ax3.text(j, i, f'{int(overlap_matrix[i, j])}', 
                            ha='center', va='center')
            
            plt.colorbar(im, ax=ax3)
        
        # Detection timeline
        ax4 = axes[1, 1]
        
        for subject_id, analysis in subject_analysis.items():
            timestamps = [face['timestamp'] for face in analysis['faces']]
            trials = [face['trial_number'] for face in analysis['faces']]
            
            ax4.scatter(timestamps, [subject_id] * len(timestamps), 
                    alpha=0.6, s=30, label=f'Subject {subject_id}')
        
        ax4.set_xlabel('Timestamp (ms)')
        ax4.set_ylabel('Subject ID')
        ax4.set_title('Detection Timeline')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        plot_path = os.path.join(output_dir, 'subject_identification_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Subject analysis plots saved to: {plot_path}")
        
        # Save sample face images for each subject
        self._save_sample_faces(subject_analysis, valid_pictures, output_dir)

    def analyze_gamble_vs_gamble_choices(self, output_dir='plots'):
        """
        Analyze relative preferences when both options are gambles (pWin1 < 1 and pWin2 < 1)
        """
        if self.trial_data is None:
            self.load_trial_data()
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Filter for trials where both options are gambles
        gamble_gamble_trials = self.trial_data[
            (self.trial_data['pWin1'] < 1.0) & 
            (self.trial_data['pWin1'] > 0.0) &
            (self.trial_data['pWin2'] < 1.0) & 
            (self.trial_data['pWin2'] > 0.0)
        ].copy()
        
        if len(gamble_gamble_trials) == 0:
            print("No gamble vs gamble trials found in the data")
            return
        
        print(f"Analyzing {len(gamble_gamble_trials)} gamble vs gamble trials")
        
        # Calculate expected values for both options
        gamble_gamble_trials['ev1'] = (
            gamble_gamble_trials['win_Amount1'] * gamble_gamble_trials['pWin1'] +
            gamble_gamble_trials['lose_Amount1'] * (1 - gamble_gamble_trials['pWin1'])
        )
        
        gamble_gamble_trials['ev2'] = (
            gamble_gamble_trials['win_Amount2'] * gamble_gamble_trials['pWin2'] +
            gamble_gamble_trials['lose_Amount2'] * (1 - gamble_gamble_trials['pWin2'])
        )
        
        # Calculate EV difference (Option 1 EV - Option 2 EV)
        gamble_gamble_trials['ev_difference'] = gamble_gamble_trials['ev1'] - gamble_gamble_trials['ev2']
        
        # Create gamble option identifiers
        gamble_gamble_trials['option1_id'] = (
            'Win:' + gamble_gamble_trials['win_Amount1'].astype(str) + 
            '/Lose:' + gamble_gamble_trials['lose_Amount1'].astype(str) + 
            '/P:' + gamble_gamble_trials['pWin1'].astype(str)
        )
        
        gamble_gamble_trials['option2_id'] = (
            'Win:' + gamble_gamble_trials['win_Amount2'].astype(str) + 
            '/Lose:' + gamble_gamble_trials['lose_Amount2'].astype(str) + 
            '/P:' + gamble_gamble_trials['pWin2'].astype(str)
        )
        
        # Determine which option was chosen
        # If options_spacial_config matches choice, option 1 was chosen
        gamble_gamble_trials['chose_option1'] = (
            gamble_gamble_trials['options_spacial_config'] == gamble_gamble_trials['choice']
        )
        
        # Create comprehensive analysis figure
        fig = plt.figure(figsize=(20, 16))
        
        # Plot 1: Choice probability vs EV difference
        ax1 = plt.subplot(3, 3, 1)
        
        # Group by EV difference and calculate choice probability
        ev_bins = np.linspace(gamble_gamble_trials['ev_difference'].min(), 
                            gamble_gamble_trials['ev_difference'].max(), 10)
        gamble_gamble_trials['ev_bin'] = pd.cut(gamble_gamble_trials['ev_difference'], ev_bins)
        
        prob_by_ev = gamble_gamble_trials.groupby('ev_bin').agg({
            'chose_option1': ['mean', 'count']
        }).round(3)
        prob_by_ev.columns = ['prob_choose_option1', 'n_trials']
        prob_by_ev = prob_by_ev.reset_index()
        
        # Get bin centers for plotting
        prob_by_ev['ev_center'] = prob_by_ev['ev_bin'].apply(lambda x: x.mid)
        
        # Plot with error bars
        ax1.scatter(prob_by_ev['ev_center'], prob_by_ev['prob_choose_option1'], 
                s=prob_by_ev['n_trials']*10, alpha=0.7, c='blue')
        
        # Fit logistic regression
        from scipy.optimize import curve_fit
        
        def logistic_function(x, b0, b1):
            return 1 / (1 + np.exp(-(b0 + b1 * x)))
        
        try:
            valid_data = prob_by_ev.dropna()
            if len(valid_data) > 2:
                popt, _ = curve_fit(logistic_function, 
                                valid_data['ev_center'], 
                                valid_data['prob_choose_option1'],
                                p0=[0, 1], maxfev=5000)
                
                b0, b1 = popt
                
                # Plot fitted curve
                x_smooth = np.linspace(prob_by_ev['ev_center'].min(), 
                                    prob_by_ev['ev_center'].max(), 100)
                y_smooth = logistic_function(x_smooth, b0, b1)
                ax1.plot(x_smooth, y_smooth, 'r-', linewidth=2, alpha=0.8, 
                        label=f'Logistic fit: b₀={b0:.3f}, b₁={b1:.3f}')
                
                # Calculate indifference point (where P = 0.5)
                indifference_point = -b0 / b1 if b1 != 0 else 0
                ax1.axvline(x=indifference_point, color='red', linestyle='--', alpha=0.5,
                        label=f'Indifference: EV_diff={indifference_point:.3f}')
        
        except Exception as e:
            print(f"Could not fit logistic curve: {e}")
        
        ax1.axvline(x=0, color='black', linestyle=':', alpha=0.5, label='Equal EV')
        ax1.axhline(y=0.5, color='black', linestyle=':', alpha=0.5, label='Random choice')
        ax1.set_xlabel('EV Difference (Option 1 - Option 2)')
        ax1.set_ylabel('Probability of Choosing Option 1')
        ax1.set_title('Choice Preference vs Expected Value Difference')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 1)
        
        # Plot 2: Risk preference analysis
        ax2 = plt.subplot(3, 3, 2)
        
        # Calculate variance for each option
        gamble_gamble_trials['var1'] = (
            gamble_gamble_trials['pWin1'] * (gamble_gamble_trials['win_Amount1'] - gamble_gamble_trials['ev1'])**2 +
            (1 - gamble_gamble_trials['pWin1']) * (gamble_gamble_trials['lose_Amount1'] - gamble_gamble_trials['ev1'])**2
        )
        
        gamble_gamble_trials['var2'] = (
            gamble_gamble_trials['pWin2'] * (gamble_gamble_trials['win_Amount2'] - gamble_gamble_trials['ev2'])**2 +
            (1 - gamble_gamble_trials['pWin2']) * (gamble_gamble_trials['lose_Amount2'] - gamble_gamble_trials['ev2'])**2
        )
        
        # Variance difference (Option 1 - Option 2)
        gamble_gamble_trials['var_difference'] = gamble_gamble_trials['var1'] - gamble_gamble_trials['var2']
        
        # Group by variance difference
        var_bins = np.linspace(gamble_gamble_trials['var_difference'].min(), 
                            gamble_gamble_trials['var_difference'].max(), 8)
        gamble_gamble_trials['var_bin'] = pd.cut(gamble_gamble_trials['var_difference'], var_bins)
        
        prob_by_var = gamble_gamble_trials.groupby('var_bin').agg({
            'chose_option1': ['mean', 'count']
        }).round(3)
        prob_by_var.columns = ['prob_choose_option1', 'n_trials']
        prob_by_var = prob_by_var.reset_index()
        prob_by_var['var_center'] = prob_by_var['var_bin'].apply(lambda x: x.mid)
        
        ax2.scatter(prob_by_var['var_center'], prob_by_var['prob_choose_option1'], 
                s=prob_by_var['n_trials']*10, alpha=0.7, c='green')
        
        ax2.axvline(x=0, color='black', linestyle=':', alpha=0.5, label='Equal variance')
        ax2.axhline(y=0.5, color='black', linestyle=':', alpha=0.5, label='Random choice')
        ax2.set_xlabel('Variance Difference (Option 1 - Option 2)')
        ax2.set_ylabel('Probability of Choosing Option 1')
        ax2.set_title('Risk Preference: Choice vs Variance Difference')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 1)
        
        # Plot 3: Probability preference analysis
        ax3 = plt.subplot(3, 3, 3)
        
        # Probability difference
        gamble_gamble_trials['prob_difference'] = gamble_gamble_trials['pWin1'] - gamble_gamble_trials['pWin2']
        
        prob_bins = np.linspace(gamble_gamble_trials['prob_difference'].min(), 
                            gamble_gamble_trials['prob_difference'].max(), 8)
        gamble_gamble_trials['prob_bin'] = pd.cut(gamble_gamble_trials['prob_difference'], prob_bins)
        
        prob_by_prob = gamble_gamble_trials.groupby('prob_bin').agg({
            'chose_option1': ['mean', 'count']
        }).round(3)
        prob_by_prob.columns = ['prob_choose_option1', 'n_trials']
        prob_by_prob = prob_by_prob.reset_index()
        prob_by_prob['prob_center'] = prob_by_prob['prob_bin'].apply(lambda x: x.mid)
        
        ax3.scatter(prob_by_prob['prob_center'], prob_by_prob['prob_choose_option1'], 
                s=prob_by_prob['n_trials']*10, alpha=0.7, c='orange')
        
        ax3.axvline(x=0, color='black', linestyle=':', alpha=0.5, label='Equal probability')
        ax3.axhline(y=0.5, color='black', linestyle=':', alpha=0.5, label='Random choice')
        ax3.set_xlabel('Probability Difference (pWin1 - pWin2)')
        ax3.set_ylabel('Probability of Choosing Option 1')
        ax3.set_title('Probability Preference Analysis')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(0, 1)
        
        # Plot 4: Choice consistency over trials
        ax4 = plt.subplot(3, 3, 4)
        
        # Rolling average of choosing higher EV option
        gamble_gamble_trials_sorted = gamble_gamble_trials.sort_values('trial_number')
        gamble_gamble_trials_sorted['chose_higher_ev'] = (
            (gamble_gamble_trials_sorted['ev_difference'] > 0) & 
            (gamble_gamble_trials_sorted['chose_option1']) |
            (gamble_gamble_trials_sorted['ev_difference'] < 0) & 
            (~gamble_gamble_trials_sorted['chose_option1'])
        )
        
        window_size = min(20, len(gamble_gamble_trials_sorted) // 5)
        if window_size > 0:
            rolling_optimal = gamble_gamble_trials_sorted['chose_higher_ev'].rolling(
                window=window_size, min_periods=1).mean()
            
            ax4.plot(range(len(rolling_optimal)), rolling_optimal, 'b-', linewidth=2, alpha=0.7)
            ax4.axhline(y=0.5, color='black', linestyle=':', alpha=0.5, label='Random choice')
            ax4.set_xlabel('Trial Sequence')
            ax4.set_ylabel('Proportion Choosing Higher EV')
            ax4.set_title('Optimal Choice Consistency Over Time')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            ax4.set_ylim(0, 1)
        
        # Plot 5: EV vs Variance scatter
        ax5 = plt.subplot(3, 3, 5)
        
        # Create scatter plot showing all option pairs
        option1_points = ax5.scatter(gamble_gamble_trials['ev1'], gamble_gamble_trials['var1'], 
                                    alpha=0.6, c='blue', s=30, label='Option 1')
        option2_points = ax5.scatter(gamble_gamble_trials['ev2'], gamble_gamble_trials['var2'], 
                                    alpha=0.6, c='red', s=30, label='Option 2')
        
        ax5.set_xlabel('Expected Value')
        ax5.set_ylabel('Variance')
        ax5.set_title('Risk-Return Profile of All Options')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # Plot 6: Unique gamble pair analysis
        ax6 = plt.subplot(3, 3, 6)
        
        # Create gamble pair identifier
        gamble_gamble_trials['pair_id'] = (
            gamble_gamble_trials['option1_id'] + ' vs ' + gamble_gamble_trials['option2_id']
        )
        
        # Get most common pairs
        pair_counts = gamble_gamble_trials['pair_id'].value_counts().head(10)
        
        if len(pair_counts) > 0:
            pair_prefs = []
            pair_labels = []
            
            for pair_id in pair_counts.index[:5]:  # Top 5 pairs
                pair_data = gamble_gamble_trials[gamble_gamble_trials['pair_id'] == pair_id]
                pref = pair_data['chose_option1'].mean()
                pair_prefs.append(pref)
                pair_labels.append(f"Pair {len(pair_labels)+1}")
            
            bars = ax6.bar(range(len(pair_prefs)), pair_prefs, alpha=0.7, 
                        color=['blue' if p > 0.5 else 'red' for p in pair_prefs])
            
            ax6.axhline(y=0.5, color='black', linestyle=':', alpha=0.5, label='Random choice')
            ax6.set_xlabel('Gamble Pair')
            ax6.set_ylabel('Probability of Choosing Option 1')
            ax6.set_title('Preferences for Most Common Gamble Pairs')
            ax6.set_xticks(range(len(pair_labels)))
            ax6.set_xticklabels(pair_labels, rotation=45)
            ax6.legend()
            ax6.grid(True, alpha=0.3)
            ax6.set_ylim(0, 1)
        
        # Plot 7: Summary statistics table
        ax7 = plt.subplot(3, 3, 7)
        ax7.axis('off')
        
        # Calculate summary statistics
        overall_stats = {
            'Total Trials': len(gamble_gamble_trials),
            'Chose Higher EV': f"{(gamble_gamble_trials['chose_higher_ev'].mean()*100):.1f}%",
            'Mean EV Diff': f"{gamble_gamble_trials['ev_difference'].mean():.3f}",
            'EV Sensitivity': f"{b1:.3f}" if 'b1' in locals() else "N/A",
            'Indifference Point': f"{indifference_point:.3f}" if 'indifference_point' in locals() else "N/A"
        }
        
        table_data = [[key, value] for key, value in overall_stats.items()]
        
        table = ax7.table(cellText=table_data,
                        colLabels=['Metric', 'Value'],
                        cellLoc='left',
                        loc='center',
                        bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 2)
        
        # Style the table
        for i in range(len(table_data) + 1):
            for j in range(2):
                cell = table[(i, j)]
                if i == 0:  # Header
                    cell.set_facecolor('#4CAF50')
                    cell.set_text_props(weight='bold', color='white')
                else:
                    cell.set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
        
        ax7.set_title('Summary Statistics', fontsize=12, pad=20)
        
        # Plot 8: Reaction time analysis
        ax8 = plt.subplot(3, 3, 8)
        
        if 'ts_button_press' in gamble_gamble_trials.columns and 'ts_stimuli_on' in gamble_gamble_trials.columns:
            reaction_times = (gamble_gamble_trials['ts_button_press'] - 
                            gamble_gamble_trials['ts_stimuli_on'])
            reaction_times = reaction_times[(reaction_times > 0) & (reaction_times < 10000)]
            
            if len(reaction_times) > 0:
                # Compare reaction times for different choice types
                rt_optimal = reaction_times[gamble_gamble_trials['chose_higher_ev']]
                rt_suboptimal = reaction_times[~gamble_gamble_trials['chose_higher_ev']]
                
                ax8.hist(rt_optimal, bins=20, alpha=0.6, label='Chose Higher EV', color='blue')
                ax8.hist(rt_suboptimal, bins=20, alpha=0.6, label='Chose Lower EV', color='red')
                
                ax8.set_xlabel('Reaction Time (ms)')
                ax8.set_ylabel('Frequency')
                ax8.set_title('Reaction Times by Choice Quality')
                ax8.legend()
                ax8.grid(True, alpha=0.3)
        
        # Plot 9: Learning curve
        ax9 = plt.subplot(3, 3, 9)
        
        if len(gamble_gamble_trials_sorted) > 10:
            # Divide trials into blocks
            n_blocks = 5
            block_size = len(gamble_gamble_trials_sorted) // n_blocks
            
            block_performance = []
            block_labels = []
            
            for i in range(n_blocks):
                start_idx = i * block_size
                end_idx = (i + 1) * block_size if i < n_blocks - 1 else len(gamble_gamble_trials_sorted)
                
                block_data = gamble_gamble_trials_sorted.iloc[start_idx:end_idx]
                performance = block_data['chose_higher_ev'].mean()
                
                block_performance.append(performance)
                block_labels.append(f'Block {i+1}')
            
            ax9.plot(range(len(block_performance)), block_performance, 'o-', linewidth=2, markersize=8)
            ax9.axhline(y=0.5, color='black', linestyle=':', alpha=0.5, label='Random choice')
            ax9.set_xlabel('Trial Block')
            ax9.set_ylabel('Proportion Optimal Choices')
            ax9.set_title('Learning Curve Across Session')
            ax9.set_xticks(range(len(block_labels)))
            ax9.set_xticklabels(block_labels)
            ax9.legend()
            ax9.grid(True, alpha=0.3)
            ax9.set_ylim(0, 1)
        
        plt.suptitle('Gamble vs Gamble Choice Analysis', fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # Save plot
        plot_path = os.path.join(output_dir, 'gamble_vs_gamble_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"\nGamble vs Gamble analysis plot saved to: {plot_path}")
        
        # Print detailed analysis
        print("\n" + "="*80)
        print("GAMBLE VS GAMBLE CHOICE ANALYSIS")
        print("="*80)
        
        print(f"Total gamble vs gamble trials: {len(gamble_gamble_trials)}")
        print(f"Proportion choosing higher EV option: {gamble_gamble_trials['chose_higher_ev'].mean():.3f}")
        
        if 'b1' in locals():
            print(f"EV sensitivity (logistic slope): {b1:.3f}")
            if b1 > 0:
                print("  → Positive EV sensitivity (prefers higher expected value)")
            else:
                print("  → Negative EV sensitivity (unusual - may prefer lower expected value)")
        
        if 'indifference_point' in locals():
            print(f"Indifference point: {indifference_point:.3f}")
            if abs(indifference_point) < 0.1:
                print("  → Nearly unbiased choice behavior")
            elif indifference_point > 0:
                print("  → Slight bias toward Option 2")
            else:
                print("  → Slight bias toward Option 1")
        
        # Risk preference analysis
        var_sensitivity = gamble_gamble_trials[['var_difference', 'chose_option1']].corr().iloc[0,1]
        print(f"Variance sensitivity correlation: {var_sensitivity:.3f}")
        if var_sensitivity > 0.1:
            print("  → Risk-seeking behavior (prefers higher variance)")
        elif var_sensitivity < -0.1:
            print("  → Risk-averse behavior (avoids higher variance)")
        else:
            print("  → Risk-neutral behavior")
        
        return gamble_gamble_trials

    def _save_sample_faces(self, subject_analysis, valid_pictures, output_dir):
        """Save sample face images for each identified subject"""
        
        faces_dir = os.path.join(output_dir, 'sample_faces')
        if not os.path.exists(faces_dir):
            os.makedirs(faces_dir)
        
        # Create a mapping from picture_id to image
        picture_dict = {pic_id: img for pic_id, trial, frame, img in valid_pictures}
        
        for subject_id, analysis in subject_analysis.items():
            subject_dir = os.path.join(faces_dir, f'subject_{subject_id}')
            if not os.path.exists(subject_dir):
                os.makedirs(subject_dir)
            
            # Get a few sample faces for this subject
            sample_faces = analysis['faces'][:5]  # First 5 detections
            
            for i, face_info in enumerate(sample_faces):
                picture_id = face_info['picture_id']
                
                if picture_id in picture_dict:
                    image = picture_dict[picture_id]
                    
                    # Extract face region
                    if face_info['method'] == 'face_recognition':
                        top, right, bottom, left = face_info['face_location']
                        face_crop = image[top:bottom, left:right]
                    else:
                        x, y, w, h = face_info['face_location']
                        face_crop = image[y:y+h, x:x+w]
                    
                    # Save face crop
                    filename = f"face_{i+1}_trial_{face_info['trial_number']}_frame_{face_info['frame_number']}.jpg"
                    filepath = os.path.join(subject_dir, filename)
                    cv2.imwrite(filepath, face_crop)
        
        print(f"Sample face images saved to: {faces_dir}")

    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("Database connection closed")

def show_gui_message(title, message, message_type="info"):
    """Show GUI message box if available"""
    if GUI_AVAILABLE:
        root = tk.Tk()
        root.withdraw()
        
        if message_type == "error":
            messagebox.showerror(title, message)
        elif message_type == "warning":
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)
            
        root.destroy()
    else:
        print(f"{title}: {message}")

def get_command_line_args():
    """Parse command line arguments"""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return None

def main():
    """Main function with GUI file selection"""
    
    print("=== Gambling Experiment Database Analyzer ===")
    
    # Check for command line argument first
    db_path = get_command_line_args()
    
    if db_path:
        print(f"Using database from command line: {db_path}")
    else:
        print("No database path provided. Opening file selector...")
    
    try:
        # Create analyzer (will open GUI if no path provided)
        analyzer = GamblingExperimentAnalyzer(db_path)
        
        # Get database information
        print("\n=== DATABASE INFORMATION ===")
        analyzer.get_database_info()
        
        # Load data
        print("\n=== LOADING DATA ===")
        trial_data = analyzer.load_trial_data()
        picture_data = analyzer.load_picture_data()
        
        if trial_data is not None:
            print("\n=== GAMBLE VS SURE CHOICE ANALYSIS ===")
            gamble_data = analyzer.analyze_gamble_vs_sure_choices()

##        if trial_data is not None:
##            print("\n=== GAMBLE VS GAMBLE CHOICE ANALYSIS ===")
##            gamble_gamble_data = analyzer.analyze_gamble_vs_gamble_choices()

        # Display basic info
        if trial_data is not None:
            print(f"\nTrial data shape: {trial_data.shape}")
            print(f"Columns: {list(trial_data.columns)}")
            print("\nFirst few rows:")
            print(trial_data.head())
        
        if picture_data is not None:
            print(f"\nPicture data shape: {picture_data.shape}")
            if len(picture_data) > 0:
                print(f"Pictures per trial: {picture_data.groupby('trial_number').size().describe()}")
        
        if picture_data is not None and len(picture_data) > 0:
            print("\n=== SUBJECT IDENTIFICATION FROM IMAGES ===")
            subject_analysis, face_data = analyzer.identify_unique_subjects_from_images()

        # Generate summary
        print("\n=== TRIAL SUMMARY ===")
        summary = analyzer.get_trial_summary()
        for key, value in summary.items():
            print(f"{key}: {value}")
        
        # Export data
        print("\n=== EXPORTING DATA ===")
        analyzer.export_to_csv()
        analyzer.export_to_numpy()
        
        # Extract some pictures (first 3 trials as example)
        if picture_data is not None and len(picture_data) > 0:
            print("\n=== EXTRACTING SAMPLE PICTURES ===")
            sample_trials = picture_data['trial_number'].unique()[:3]
            analyzer.extract_pictures(trial_numbers=sample_trials.tolist())
        
        # Create visualizations
        if trial_data is not None:
            print("\n=== CREATING VISUALIZATIONS ===")
            analyzer.create_visualizations()
        
        # Performance analysis
        print("\n=== PERFORMANCE ANALYSIS ===")
        performance = analyzer.analyze_performance_over_time()
        if 'reaction_time_trend' in performance:
            print(f"Mean reaction time: {performance['reaction_time_trend'].mean():.2f} ms")
            print(f"Reaction time std: {performance['reaction_time_trend'].std():.2f} ms")
        
        # Close connection
        analyzer.close_connection()
        
        print("\n=== ANALYSIS COMPLETE ===")
        print("Check the 'exported_data', 'extracted_pictures', and 'plots' directories for output files.")
        
        # Show completion message
        show_gui_message("Analysis Complete", 
                        "Database analysis completed successfully!\n\nOutput files saved to:\n"
                        "- exported_data/\n- extracted_pictures/\n- plots/")
        
    except FileNotFoundError as e:
        error_msg = f"Database file not found: {e}"
        print(error_msg)
        show_gui_message("File Not Found", error_msg, "error")
        
    except ValueError as e:
        if "No database file selected" in str(e):
            print("No database file selected. Exiting.")
            show_gui_message("No File Selected", "No database file was selected. Analysis cancelled.", "warning")
        else:
            print(f"Error: {e}")
            show_gui_message("Error", str(e), "error")
        
    except Exception as e:
        error_msg = f"Error during analysis: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        show_gui_message("Analysis Error", error_msg, "error")

# Standalone functions for quick data access
def quick_load_trials(db_path=None):
    """Quickly load trial data into pandas DataFrame"""
    if db_path is None:
        analyzer = GamblingExperimentAnalyzer()
        db_path = analyzer.db_path
        analyzer.close_connection()
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM trial_data ORDER BY trial_number", conn)
    conn.close()
    return df

def quick_load_pictures_metadata(db_path=None):
    """Quickly load picture metadata"""
    if db_path is None:
        analyzer = GamblingExperimentAnalyzer()
        db_path = analyzer.db_path
        analyzer.close_connection()
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("""
        SELECT picture_id, trial_number, timestamp, frame_number, 
               image_width, image_height 
        FROM trial_pictures 
        ORDER BY trial_number, frame_number
    """, conn)
    conn.close()
    return df

if __name__ == "__main__":
    main()
