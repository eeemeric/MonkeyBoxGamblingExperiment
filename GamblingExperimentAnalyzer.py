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