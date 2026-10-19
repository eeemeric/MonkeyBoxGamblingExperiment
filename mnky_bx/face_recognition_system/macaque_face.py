# -*- coding: utf-8 -*-
"""
macaque_face.py -- macaque face detection and identification for mnky_bx.

Why: OpenCV's haarcascade_frontalface_default.xml (used by the original
MonkeyBoxGamblingExperiment.py) and dlib/face_recognition are trained on HUMAN
faces and do not reliably detect macaque faces. This module uses the
macaque-specific LBP cascades published with Witham (2018, J Neurosci Methods
300:157-165; https://github.com/clwitham/MacaqueFaces, MIT license, see
models/LICENSE_MacaqueFaces.md): a frontal-face cascade, plus eye and nose
cascades used to verify each candidate face.

Pieces
  FaceDetector    detect(frame_bgr) -> [(x, y, w, h), ...], same format as
                  cv2.CascadeClassifier.detectMultiScale, largest face first.
                  species='macaque' for the animals, 'human' for the human pilot.
  FaceConfirmer   True once a face is present in `required` of the last
                  `window` frames, so one false detection cannot start a trial.
  FaceIdentifier  Which subject is it? Uniform-LBP block histograms + shrinkage
                  LDA (after Witham 2018). Labels are subject IDs such as
                  'subject_id_01'; low-confidence predictions -> 'unknown'.

Helpers for the mnky_bx directory layout (see subjects/README.md)
  load_subject_crops(subjects_dir)   enrollment crops from
                                     subjects/<subject_id>/face_images/*.jpg
  annotate_session(session_dir, ...) runs detection (+ identification) on
                                     session_XXX/trial_images/trial_*/frame_*.jpg
                                     and writes session_XXX/recognition_log.json
  trial_identities(log)              one identity per trial (majority vote)
  annotate_legacy_database(db, ...)  same, for SQLite files written by the
                                     original script (trial_pictures table)

Dependencies: opencv-python, numpy, scikit-image, scikit-learn.

Benchmark on Witham's public data (tools/evaluate_face_pipeline.py):
  - human Haar cascade: 0 of 64 detections were monkey faces
  - macaque cascade: precision 84% (76/91); with eye/nose verification 100%
    (31/31), but verification also rejects more than half of the true faces,
    so `verify` / `min_neighbors` should be tuned on the box's own images
  - identification, held-out images: two animals 96-99% with 10-50 training
    images each; 34 animals 85-95%
"""
import json
import os
import pickle
import sqlite3
from collections import Counter, deque
from pathlib import Path

import cv2
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent / "models"
HUMAN_CASCADE = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
UNKNOWN = "unknown"


def _load_cascade(path):
    c = cv2.CascadeClassifier(str(path))
    if c.empty():
        raise FileNotFoundError(f"Could not load cascade: {path}")
    return c


def _gray(img):
    return img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------
class FaceDetector:
    """Detect faces in a frame.

    species        'macaque' (Witham 2018 LBP cascade) or 'human' (OpenCV Haar),
                   so the same code path serves the human pilot and the animals.
    verify         macaque only: keep a candidate face only if a nose and at
                   least one eye are found inside it (Witham's face+eyes+nose rule).
    scale          frames are downscaled by this factor before detection, which
                   keeps detection fast enough for a Raspberry Pi.
    min_face       smallest face to report, in pixels of the ORIGINAL frame.
    min_neighbors  cascade merge threshold; default 8 for macaque (Witham 2018)
                   and 5 for human (the original script's value).
    """

    def __init__(self, species="macaque", model_dir=MODEL_DIR, verify=True,
                 scale=0.5, min_face=60, scale_factor=1.1, min_neighbors=None):
        if species not in ("macaque", "human"):
            raise ValueError("species must be 'macaque' or 'human'")
        model_dir = Path(model_dir)
        self.species = species
        self.verify = verify and species == "macaque"
        self.scale = scale
        self.min_face = min_face
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors if min_neighbors is not None else (8 if species == "macaque" else 5)
        if species == "macaque":
            self.face = _load_cascade(model_dir / "MacaqueFrontalFaceModel.xml")
            if self.verify:
                self.eye = _load_cascade(model_dir / "MacaqueSingleEyeModel.xml")
                self.nose = _load_cascade(model_dir / "MacaqueNoseModel.xml")
        else:
            self.face = _load_cascade(HUMAN_CASCADE)

    def _verify_face(self, crop_gray):
        """Witham's rule: a real face contains eyes and a nose."""
        c = cv2.resize(crop_gray, (100, 100))
        eyes = self.eye.detectMultiScale(c[:60, :], 1.1, 1, minSize=(12, 7), maxSize=(45, 30))
        noses = self.nose.detectMultiScale(c[25:, 20:80], 1.1, 1, minSize=(14, 28))
        return len(eyes) > 0 and len(noses) > 0

    def detect(self, frame):
        """Return a list of (x, y, w, h) boxes in original-frame pixels, largest first."""
        gray = cv2.equalizeHist(_gray(frame))
        small = cv2.resize(gray, None, fx=self.scale, fy=self.scale) if self.scale != 1 else gray
        m = max(int(self.min_face * self.scale), 24)
        boxes = self.face.detectMultiScale(small, scaleFactor=self.scale_factor,
                                           minNeighbors=self.min_neighbors, minSize=(m, m))
        out = []
        for (x, y, w, h) in boxes:
            X, Y, W, H = (int(round(v / self.scale)) for v in (x, y, w, h))
            if self.verify and not self._verify_face(gray[Y:Y + H, X:X + W]):
                continue
            out.append((X, Y, W, H))
        out.sort(key=lambda b: b[2] * b[3], reverse=True)
        return out


class FaceConfirmer:
    """Confirm a face only when it is present in `required` of the last `window` frames."""

    def __init__(self, required=3, window=5):
        if required > window:
            raise ValueError("required must be <= window")
        self.required = required
        self.history = deque(maxlen=window)

    def update(self, n_faces):
        self.history.append(n_faces > 0)
        return sum(self.history) >= self.required

    def reset(self):
        self.history.clear()


# --------------------------------------------------------------------------
# Identification
# --------------------------------------------------------------------------
class FaceIdentifier:
    """Identify individuals from face crops.

    Features: the crop is resized to size x size, histogram-equalized, divided
    into grid x grid blocks, and a 59-bin uniform LBP histogram is computed per
    block (5 x 5 x 59 = 1,475 features, as in Witham 2018). Classifier: linear
    discriminant analysis with automatic shrinkage. Predictions whose posterior
    probability is below `reject_prob` are returned as 'unknown'. The posterior
    is the LDA model's own estimate, not a calibrated probability; check the
    threshold against labeled images from the box.
    """

    def __init__(self, grid=5, size=100, reject_prob=0.6):
        self.grid, self.size, self.reject_prob = grid, size, reject_prob
        self.clf = None

    def features(self, crop):
        from skimage.feature import local_binary_pattern
        g = cv2.equalizeHist(cv2.resize(_gray(crop), (self.size, self.size)))
        lbp = local_binary_pattern(g, P=8, R=1, method="nri_uniform")  # 59 codes
        b = self.size // self.grid
        feats = []
        for i in range(self.grid):
            for j in range(self.grid):
                h, _ = np.histogram(lbp[i * b:(i + 1) * b, j * b:(j + 1) * b], bins=59, range=(0, 59))
                feats.append(h / (h.sum() + 1e-9))
        return np.concatenate(feats)

    def fit(self, crops, labels):
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        if len(set(labels)) < 2:
            raise ValueError("need face crops from at least two subjects")
        X = np.array([self.features(c) for c in crops])
        self.clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto").fit(X, list(labels))
        return self

    @property
    def subjects(self):
        return [] if self.clf is None else [str(c) for c in self.clf.classes_]

    def predict(self, crops):
        """Return (labels, max posterior) for a list of crops."""
        if self.clf is None:
            raise RuntimeError("FaceIdentifier is not trained; call fit() or load()")
        if len(crops) == 0:
            return [], np.array([])
        P = self.clf.predict_proba(np.array([self.features(c) for c in crops]))
        best = P.argmax(1)
        labels = [str(self.clf.classes_[k]) if P[i, k] >= self.reject_prob else UNKNOWN
                  for i, k in enumerate(best)]
        return labels, P.max(1)

    def save(self, path):
        with open(path, "wb") as f:
            pickle.dump(self.__dict__, f)

    @classmethod
    def load(cls, path):
        """Load a model saved with save(). Only load files you created (pickle)."""
        obj = cls()
        with open(path, "rb") as f:
            obj.__dict__.update(pickle.load(f))
        return obj


# --------------------------------------------------------------------------
# mnky_bx directory layout helpers
# --------------------------------------------------------------------------
IMAGE_EXT = (".jpg", ".jpeg", ".png")


def load_subject_crops(subjects_dir, folder="face_images"):
    """Read enrollment crops from subjects/<subject_id>/<folder>/*.jpg.

    Returns (crops, labels); subjects without images, and not_recognized/,
    are skipped.
    """
    crops, labels = [], []
    for sdir in sorted(Path(subjects_dir).iterdir()):
        if not sdir.is_dir() or sdir.name == "not_recognized":
            continue
        for f in sorted((sdir / folder).glob("*")) if (sdir / folder).is_dir() else []:
            if f.suffix.lower() in IMAGE_EXT:
                img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    crops.append(img)
                    labels.append(sdir.name)
    return crops, labels


def annotate_session(session_dir, detector=None, identifier=None, save_unrecognized_to=None):
    """Detect (and optionally identify) faces in every frame of a session.

    Reads  session_dir/trial_images/<trial>/<frame>.jpg
    Writes session_dir/recognition_log.json: one entry per frame,
           {"trial", "frame", "faces": [{"x","y","w","h","identity","prob"}]}
    If save_unrecognized_to is given (e.g. subjects/not_recognized/face_images),
    crops identified as 'unknown' are written there for later clustering.
    Returns the log as a list.
    """
    detector = detector or FaceDetector()
    session_dir = Path(session_dir)
    if save_unrecognized_to is not None:
        Path(save_unrecognized_to).mkdir(parents=True, exist_ok=True)
    log = []
    for tdir in sorted((session_dir / "trial_images").glob("*")):
        if not tdir.is_dir():
            continue
        for f in sorted(tdir.iterdir()):
            if f.suffix.lower() not in IMAGE_EXT:
                continue
            img = cv2.imread(str(f))
            if img is None:
                continue
            boxes = detector.detect(img)
            crops = [img[y:y + h, x:x + w] for (x, y, w, h) in boxes]
            ids, probs = identifier.predict(crops) if identifier is not None and crops else ([], [])
            faces = []
            for k, (x, y, w, h) in enumerate(boxes):
                ident = ids[k] if ids else None
                faces.append(dict(x=int(x), y=int(y), w=int(w), h=int(h), identity=ident,
                                  prob=float(probs[k]) if ids else None))
                if ident == UNKNOWN and save_unrecognized_to is not None:
                    name = f"{session_dir.name}_{tdir.name}_{f.stem}_{k}.jpg"
                    cv2.imwrite(str(Path(save_unrecognized_to) / name), crops[k])
            log.append(dict(trial=tdir.name, frame=f.name, faces=faces))
    with open(session_dir / "recognition_log.json", "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2)
    return log


def trial_identities(log, min_fraction=0.6):
    """One identity per trial from a recognition log (list, or path to the JSON).

    Uses the largest face in each frame; a trial is assigned only if at least
    `min_fraction` of its identified frames agree, otherwise 'unassigned'.
    """
    if isinstance(log, (str, os.PathLike)):
        with open(log, encoding="utf-8") as fh:
            log = json.load(fh)
    by_trial = {}
    for entry in log:
        if entry["faces"] and entry["faces"][0]["identity"] not in (None, UNKNOWN):
            by_trial.setdefault(entry["trial"], []).append(entry["faces"][0]["identity"])
    out = {}
    for trial, ids in by_trial.items():
        ident, n = Counter(ids).most_common(1)[0]
        out[trial] = ident if n / len(ids) >= min_fraction else "unassigned"
    return out


def annotate_legacy_database(db_path, detector=None, identifier=None, overwrite=False):
    """Same as annotate_session, for SQLite files from the original script.

    Reads the trial_pictures table (JPEG blobs) and writes a new trial_faces
    table (picture_id, trial_number, frame_number, face_index, x, y, w, h,
    identity, id_prob). Existing tables are not modified. Returns faces stored.
    """
    detector = detector or FaceDetector()
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    if overwrite:
        cur.execute("DROP TABLE IF EXISTS trial_faces")
    cur.execute("""CREATE TABLE IF NOT EXISTS trial_faces (
        picture_id INTEGER, trial_number INTEGER, frame_number INTEGER,
        face_index INTEGER, x INTEGER, y INTEGER, w INTEGER, h INTEGER,
        identity TEXT, id_prob REAL)""")
    done = {r[0] for r in cur.execute("SELECT DISTINCT picture_id FROM trial_faces")}
    rows = cur.execute("SELECT picture_id, trial_number, frame_number, image_data "
                       "FROM trial_pictures").fetchall()
    n = 0
    for pid, trial, frame_no, blob in rows:
        if pid in done:
            continue
        img = cv2.imdecode(np.frombuffer(blob, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        boxes = detector.detect(img)
        ids, probs = ([], [])
        if identifier is not None and boxes:
            ids, probs = identifier.predict([img[y:y + h, x:x + w] for (x, y, w, h) in boxes])
        for k, (x, y, w, h) in enumerate(boxes):
            cur.execute("INSERT INTO trial_faces VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (pid, trial, frame_no, k, int(x), int(y), int(w), int(h),
                         ids[k] if ids else None, float(probs[k]) if ids else None))
            n += 1
    con.commit()
    con.close()
    return n
