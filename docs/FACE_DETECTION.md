# Macaque face detection and identification

`mnky_bx/face_recognition_system/macaque_face.py` detects macaque faces in camera frames and identifies which enrolled subject they belong to. It replaces the human face detector in the original script (`docs/original_scripts/MonkeyBoxGamblingExperiment.py`), which uses OpenCV's `haarcascade_frontalface_default.xml`. That cascade, like dlib/`face_recognition`, is trained on human faces and does not find monkey faces.

The module is self-contained. It does not change any existing file, and it does not fill in the `recognition_engine.py`, `camera_system.py` or `face_encoder.py` stubs. It can be wired into them once their interfaces are settled.

## What is in this branch

| Path | Purpose |
|---|---|
| `mnky_bx/face_recognition_system/macaque_face.py` | `FaceDetector`, `FaceConfirmer`, `FaceIdentifier` and the session-folder helpers |
| `mnky_bx/face_recognition_system/models/` | Macaque face, eye and nose cascades from Witham (2018), MIT license (`LICENSE_MacaqueFaces.md`) |
| `tests/test_face_recognition.py` | Unit tests |
| `tools/evaluate_face_pipeline.py` | Benchmark on the public MacaqueFaces data |

## Install

```bash
pip install opencv-python numpy scikit-image scikit-learn
```

## How it works

1. **Detection:** `FaceDetector(species="macaque")` runs Witham's LBP frontal-face cascade on a downscaled frame. With `verify=True`, a candidate counts as a face only if an eye and a nose are also found inside it. `species="human"` uses the OpenCV human cascade, so the same code works for the human pilot.
2. **Confirmation:** `FaceConfirmer(required=3, window=5)` returns `True` only once a face has appeared in 3 of the last 5 frames, so one false detection cannot start a trial.
3. **Identification:** `FaceIdentifier` computes uniform local-binary-pattern histograms (5 x 5 blocks x 59 bins = 1,475 features, as in Witham 2018) and classifies them with shrinkage LDA. Its labels are subject IDs (`subject_id_01`, ...). A prediction whose posterior is below `reject_prob` (default 0.6) is returned as `unknown`. The posterior is the model's own estimate, not a calibrated probability.

## Usage

### Live: gate trials on a confirmed face

```python
from mnky_bx.face_recognition_system.macaque_face import FaceDetector, FaceConfirmer

detector = FaceDetector(species="macaque")      # "human" for the human pilot
confirm = FaceConfirmer(required=3, window=5)

while running:
    frame = camera.read()                        # BGR or grayscale numpy array
    faces = detector.detect(frame)               # [(x, y, w, h), ...], largest first
    if confirm.update(len(faces)):
        confirm.reset()
        run_trial()
```

### Enrollment: train the identifier

Put face crops of each animal in `subjects/<subject_id>/face_images/`, as `.jpg` or `.png`. `not_recognized/` is skipped. Then run:

```python
from mnky_bx.face_recognition_system.macaque_face import FaceIdentifier, load_subject_crops

crops, labels = load_subject_crops("subjects")
FaceIdentifier().fit(crops, labels).save("subjects/face_identifier.pkl")
```

On the public data, 25–50 crops per animal gave 98–99% accuracy for two animals.

### Offline: label a session

```python
from mnky_bx.face_recognition_system.macaque_face import (
    FaceIdentifier, annotate_session, trial_identities)

ident = FaceIdentifier.load("subjects/face_identifier.pkl")
annotate_session("subjects/subject_id_01/gambling_experiment/session_001",
                 identifier=ident,
                 save_unrecognized_to="subjects/not_recognized/face_images")
print(trial_identities("subjects/subject_id_01/gambling_experiment/session_001/recognition_log.json"))
```

`annotate_session` reads `trial_images/<trial>/<frame>.jpg` and writes `recognition_log.json`, with one entry per frame:

```json
{"trial": "trial_001", "frame": "frame_001.jpg",
 "faces": [{"x": 212, "y": 98, "w": 160, "h": 160, "identity": "subject_id_01", "prob": 0.97}]}
```

`trial_identities` assigns each trial the identity of the largest face in at least 60% of its identified frames. Otherwise it returns `unassigned` for that trial.

For SQLite files from the original script, `annotate_legacy_database(db_path, identifier=...)` reads the `trial_pictures` table and writes a new `trial_faces` table. It leaves the existing tables untouched.

## Benchmark (public MacaqueFaces data)

`python tools/evaluate_face_pipeline.py --mf MacaqueFaces --false-positives 34,37,44,52,55,56,58,60,70,71,72,74,75,77,90`

**Detection** was run on Witham's test video of six rhesus monkeys, sampled at 2 fps (61 frames). Precision is the share of detections that were real faces.

| Detector | Detections | Precision |
|---|---|---|
| Human Haar cascade (original script) | 64 | 0% |
| Macaque cascade | 91 | 84% (76/91) |
| Macaque cascade + eye/nose check | 31 | 100% (31/31) |

The eye/nose check removes false positives, but it also rejects more than half of the true faces. Tune `verify` and `min_neighbors` on the box's own frames.

**Identification** used 34 animals, with training and test images held out from each other:

| Training images per animal | Two animals (mean of 100 random pairs) | All 34 animals |
|---|---|---|
| 10 | 96.1% | 84.5% |
| 25 | 98.1% | 91.2% |
| 50 | 98.8% | 94.5% |

## Tests

```bash
pytest --noconftest tests/test_face_recognition.py -v
MACAQUEFACES_DIR=/path/to/MacaqueFaces pytest --noconftest tests/test_face_recognition.py -v   # adds a real-image check
```

`--noconftest` is needed for now because `tests/conftest.py` imports `mnky_bx.hardware.mock_controller`, which does not import yet.

## Not done yet

- **Untested on the box's own camera.** Witham's cascades were trained on video of breeding groups. Check detection on the Arducam's 640 x 480 frames, and tune `verify`, `min_neighbors` and `min_face`.
- **Untested on a Raspberry Pi.** Detection took about 85 ms per 1080p frame on a desktop. 640 x 480 frames at `scale=0.5` have about 25x fewer pixels, but measure it on the Pi.
- **Identifier needs real crops.** Train it on crops of our own animals, and check the 0.6 threshold against frames where we know which animal it is.
