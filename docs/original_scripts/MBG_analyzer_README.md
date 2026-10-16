# Gambling Experiment Database Analyzer - Detailed Code Summary

## Overview
This is a comprehensive Python-based analysis system for a **Monkey Box Gambling Experiment** - a behavioral neuroscience research platform designed to study decision-making, risk assessment, and gambling behavior in laboratory primates. The system imports data from SQLite databases, performs statistical analyses, creates visualizations, and identifies unique subjects from captured images.

## System Architecture

### Core Components

#### 1. **GamblingExperimentAnalyzer Class**
The main analysis engine that handles all database operations and analysis functions.

**Key Attributes:**
- `db_path`: Path to SQLite database file
- `connection`: Database connection object
- `trial_data`: Pandas DataFrame containing trial information
- `picture_data`: Pandas DataFrame containing image metadata

**Core Methods:**
- Database connection and information retrieval
- Data loading and export functionality
- Statistical analysis and visualization
- Subject identification from images

#### 2. **Database Schema**
The system works with two main database tables:

**trial_data table:**
```sql
- trial_number: Unique trial identifier
- trial_type: Type of trial (choice_sure, choice_gamble_sure, etc.)
- win_Amount1/2: Reward amounts for each option
- lose_Amount1/2: Loss amounts for each option
- pWin1/2: Probability of winning for each option
- options_spacial_config: Spatial arrangement of choices
- choice: Subject's actual choice
- reward_magnitude: Actual reward delivered
- Multiple timestamps: Motion detection, face detection, stimuli onset, response, etc.
```

**trial_pictures table:**
```sql
- picture_id: Unique image identifier
- trial_number: Associated trial
- timestamp: When image was captured
- frame_number: Sequence number within trial
- image_data: BLOB containing JPEG image data
- image_width/height: Image dimensions
```

## Major Analysis Functions

### 1. **Basic Data Import and Export**

**`load_trial_data()`**
- Imports trial data from SQLite into Pandas DataFrame
- Handles missing values and data type conversions
- Provides summary statistics

**`load_picture_data()`**
- Loads image metadata (excluding BLOB data for memory efficiency)
- Links pictures to specific trials and timepoints

**Export Functions:**
- `export_to_csv()`: Exports data to CSV format
- `export_to_numpy()`: Saves data as NumPy arrays
- `extract_pictures()`: Converts BLOB data back to image files

### 2. **Statistical Analysis**

**`get_trial_summary()`**
Generates comprehensive summary statistics:
- Total and completed trials
- Choice distribution across options
- Trial type breakdown
- Reward magnitude distribution
- Reaction time analysis (button press - stimulus onset)
- Session duration calculations

**`analyze_performance_over_time()`**
Tracks behavioral changes across the session:
- Rolling averages of choice preferences
- Reaction time trends
- Learning curve analysis

### 3. **Advanced Gambling Behavior Analysis**

**`analyze_gamble_vs_sure_choices()`**
The most sophisticated analysis function, specifically designed for 'choice gamble sure' trials:

**Core Functionality:**
- Filters trials where subjects choose between guaranteed rewards and probabilistic gambles
- Identifies unique gamble options (win amount, lose amount, probability)
- Fits logistic regression models to choice behavior

**Mathematical Model:**
```
log[P(G)/(1-P(G))] = b₀ + b₁ × Sure_Amount
```
Where:
- P(G) = Probability of choosing gamble
- b₀ = Intercept parameter
- b₁ = Slope parameter
- Subjective Value = -b₀/b₁ (where P(G) = 0.5)

**Key Outputs:**
1. **Logistic Curves**: Probability of gambling vs guaranteed amount
2. **Expected Value Analysis**: Compares choices to economic predictions
3. **Risk Assessment**: Determines if behavior is risk-seeking, risk-averse, or risk-neutral
4. **Model Quality**: R² values for fit assessment
5. **Subjective Valuation**: Estimates the guaranteed amount equivalent to each gamble

**Visualizations Created:**
- Logistic fits vs guaranteed amounts
- Logistic fits vs expected value differences
- Subjective vs expected value comparison
- Choice probability heatmaps
- Model parameter tables
- Choice consistency over trials

### 4. **Subject Identification System**

**`identify_unique_subjects_from_images()`**
Advanced computer vision pipeline for identifying individual subjects:

**Technical Approach:**
- **Face Detection**: Uses OpenCV Haar cascades or face_recognition library
- **Feature Extraction**: 
  - Option 1: face_recognition library encodings (128-dimensional vectors)
  - Option 2: Combined histogram + Local Binary Pattern (LBP) features
- **Clustering**: DBSCAN algorithm to group similar faces
- **Subject Tracking**: Maps each cluster to specific trials and timepoints

**Key Capabilities:**
- Handles multiple subjects in single sessions
- Tracks subject participation across trials
- Identifies trial overlap between subjects
- Extracts highest quality face images for each subject

**Outputs:**
- Subject participation timelines
- Trial range visualizations
- Example face images for each subject
- Overlap analysis between subjects
- Participation rate calculations

## Visualization System

### 1. **Main Analysis Plots**
- **Choice Distribution**: Bar charts of behavioral choices
- **Reward Analysis**: Distribution of reward magnitudes
- **Reaction Times**: Histograms and trend analysis
- **Trial Types**: Pie charts of experimental conditions

### 2. **Gambling Analysis Visualizations**
- **6-Panel Comprehensive Figure**: 
  - Logistic regression curves
  - Expected value comparisons
  - Subjective value analysis
  - Choice probability heatmaps
  - Parameter tables
  - Temporal consistency plots

### 3. **Subject Identification Plots**
- **Multi-panel Analysis Figure**:
  - Subject presence across trials
  - Participation summaries
  - Trial overlap heatmaps
  - Detection timelines
  - Trial range bars
  - Example face images

## User Interface Features

### 1. **GUI File Selection**
- Automatic file dialog when no database path provided
- Native OS file picker with appropriate filters
- Fallback to command-line operation if GUI unavailable
- Error handling with popup messages

### 2. **Command Line Support**
```bash
# With file path
python analyzer.py "path/to/database.db"

# GUI file selection
python analyzer.py
```

### 3. **Progress Reporting**
- Real-time status updates during analysis
- Progress indicators for long-running operations
- Detailed error reporting and debugging information

## Technical Requirements

### Dependencies
```python
# Core data analysis
pandas, numpy, matplotlib, seaborn

# Computer vision
opencv-python, scikit-learn

# Optional enhanced face recognition
face_recognition, dlib

# GUI support
tkinter (usually included with Python)

# Statistical analysis
scipy
```

### Performance Considerations
- **Memory Efficient**: Loads image metadata separately from BLOB data
- **Chunked Processing**: Handles large datasets in manageable pieces
- **Caching**: Stores processed results to avoid recomputation
- **Parallel Processing**: Threading support for computer vision operations

## Research Applications

### 1. **Behavioral Economics**
- Risk preference assessment
- Decision-making under uncertainty
- Temporal discounting analysis
- Learning and adaptation studies

### 2. **Comparative Psychology**
- Cross-species decision-making comparisons
- Individual difference analysis
- Social influence studies (when multiple subjects present)

### 3. **Neuroscience Research**
- Behavioral phenotyping for genetic studies
- Pharmacological intervention effects
- Neural circuit manipulation outcomes
- Developmental trajectory analysis

## Data Security and Integrity

### 1. **Database Handling**
- Robust connection management
- Transaction safety
- Error recovery mechanisms
- Data validation checks

### 2. **File Management**
- Organized output directory structure
- Automatic backup of analysis results
- Version control friendly formats
- Cross-platform compatibility

## Extensibility

### 1. **Modular Design**
- Easy to add new analysis functions
- Pluggable visualization components
- Configurable parameters
- Custom export formats

### 2. **Integration Capabilities**
- Compatible with existing neuroscience pipelines
- Export formats suitable for statistical software (R, MATLAB, etc.)
- API-friendly structure for automation

## Output Products

### 1. **Data Files**
- CSV exports for spreadsheet analysis
- NumPy arrays for computational work
- Extracted images for manual review
- JSON metadata for web applications

### 2. **Visualizations**
- High-resolution publication-ready figures
- Interactive plots for data exploration
- Summary dashboards for quick assessment
- Custom reports for specific research questions

### 3. **Statistical Reports**
- Detailed parameter estimates
- Model fit statistics
- Behavioral interpretations
- Recommendations for further analysis

This comprehensive system provides researchers with a complete toolkit for analyzing complex behavioral data from gambling experiments, combining rigorous statistical analysis with advanced computer vision techniques to extract maximum insight from experimental sessions.