# Subjects Directory

    Each subject has their own directory:

    subjects/
    ├── not_recognized/          # Unrecognized faces from trials
    │   ├── raw_images/          # Original video frames
    │   ├── face_images/         # Detected face crops
    │   ├── embeddings/          # Face embeddings (for clustering)
    │   └── clustering_results.json
    │
    ├── subject_id_01/           # Individual subject
    │   ├── metadata.json        # Subject info (species, weight, etc.)
    │   ├── face_encodings/      # Face embeddings for recognition
    │   ├── gambling_experiment/
    │   │   ├── session_001/     # First session
    │   │   ├── session_002/
    │   │   └── session_archive/ # Older sessions
    │   └── blackjack/
    │       ├── session_001/
    │       └── session_archive/
    │
    └── subject_id_02/ through subject_id_{num_subjects:02d}/

    ## Session Directory Structure

    session_001/
    ├── database.db              # SQLite database (trial data, frame metadata)
    ├── trial_images/            # JPEG frames from trial videos
    │   ├── trial_001/
    │   │   ├── frame_001.jpg
    │   │   └── frame_002.jpg
    │   └── trial_002/
    ├── trial_videos/            # Encoded video files (optional)
    │   ├── trial_001.h265
    │   └── trial_002.h265
    ├── recognition_log.json     # Face recognition results per frame
    └── session_log.txt          # Event log with timestamps

    ## Session Directory Structure Explanation

    session_001/
    ├── database.db              # SQLite database (trial data, frame metadata)
    ├── trial_images/            # JPEG frames from trial videos
    │   ├── trial_001/
    │   │   ├── frame_001.jpg
    │   │   └── frame_002.jpg
    │   └── trial_002/
    ├── trial_videos/            # Encoded video files (optional)
    │   ├── trial_001.h265
    │   └── trial_002.h265
    ├── recognition_log.json     # Face recognition results per frame
    └── session_log.txt          # Event log with timestamps


    ## Subject Metadata
    Each subject's `metadata.json` contains:

    - Enrollment date
    - Demographics (species, sex, weight)
    - Face recognition statistics
    - Experiment history
    ## Face Recognition
    - Faces captured during trials are stored in trial_images/
    - Recognized: Subject ID + confidence score logged
    - Unrecognized: Stored in subjects/not_recognized/
    - Can cluster unrecognized faces to identify new subjects

    See face_recognition_system/ for details.
    