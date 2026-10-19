# tests/test_face_recognition.py
"""
Tests for mnky_bx.face_recognition_system.macaque_face

Run (the shared conftest.py currently imports mock hardware that is still
being written, so skip it for these tests):
    pytest --noconftest tests/test_face_recognition.py -v

Optional check on real macaque images (Witham 2018 MacaqueFaces data):
    MACAQUEFACES_DIR=/path/to/MacaqueFaces pytest --noconftest tests/test_face_recognition.py -v
"""
import json
import os
import sqlite3
from pathlib import Path

import cv2
import numpy as np
import pytest

from mnky_bx.face_recognition_system.macaque_face import (
    UNKNOWN, FaceConfirmer, FaceDetector, FaceIdentifier, annotate_legacy_database,
    annotate_session, load_subject_crops, trial_identities)


# ---------------------------------------------------------------- helpers
def texture(seed, n=20, size=100):
    """n noisy variants of one random texture; different seeds = different 'subjects'."""
    rng = np.random.default_rng(seed)
    base = cv2.GaussianBlur(rng.integers(0, 256, (size, size)).astype(np.uint8), (5, 5), 0)
    out = []
    for _ in range(n):
        noisy = base.astype(int) + rng.normal(0, 8, base.shape)
        out.append(np.clip(noisy, 0, 255).astype(np.uint8))
    return out


class FixedDetector:
    """Stand-in detector that always reports one face covering the frame."""

    def detect(self, frame):
        h, w = frame.shape[:2]
        return [(0, 0, w, h)]


def trained_identifier():
    a, b = texture(1), texture(2)
    return FaceIdentifier().fit(a[:15] + b[:15], ["subject_id_01"] * 15 + ["subject_id_02"] * 15)


# ---------------------------------------------------------------- detection
@pytest.mark.parametrize("species", ["macaque", "human"])
def test_detector_loads_and_finds_nothing_in_blank_frame(species):
    det = FaceDetector(species=species)
    assert det.detect(np.full((480, 640, 3), 128, np.uint8)) == []


def test_detector_accepts_grayscale():
    assert FaceDetector().detect(np.zeros((480, 640), np.uint8)) == []


def test_detector_rejects_unknown_species():
    with pytest.raises(ValueError):
        FaceDetector(species="dog")


def test_verify_only_applies_to_macaque():
    assert FaceDetector(species="human", verify=True).verify is False


# ---------------------------------------------------------------- confirmer
def test_confirmer_requires_k_of_n_frames():
    c = FaceConfirmer(required=3, window=5)
    assert [c.update(n) for n in (1, 0, 1, 0, 1)] == [False, False, False, False, True]
    c.reset()
    assert c.update(1) is False


def test_confirmer_forgets_old_frames():
    c = FaceConfirmer(required=2, window=3)
    for n in (1, 1, 0, 0):
        ok = c.update(n)
    assert ok is False


# ---------------------------------------------------------------- identification
def test_identifier_feature_length():
    assert FaceIdentifier().features(texture(0, n=1)[0]).shape == (5 * 5 * 59,)


def test_identifier_separates_two_subjects():
    ident = trained_identifier()
    a, b = texture(1), texture(2)
    labels, probs = ident.predict(a[15:] + b[15:])
    assert labels == ["subject_id_01"] * 5 + ["subject_id_02"] * 5
    assert np.all(probs >= ident.reject_prob)


def test_identifier_returns_unknown_below_threshold():
    ident = trained_identifier()
    ident.reject_prob = 1.01                      # nothing can pass
    labels, _ = ident.predict(texture(1)[:3])
    assert labels == [UNKNOWN] * 3


def test_identifier_needs_two_subjects_and_training():
    with pytest.raises(ValueError):
        FaceIdentifier().fit(texture(1, n=5), ["subject_id_01"] * 5)
    with pytest.raises(RuntimeError):
        FaceIdentifier().predict(texture(1, n=1))


def test_identifier_save_load_roundtrip(tmp_path):
    ident = trained_identifier()
    ident.save(tmp_path / "id.pkl")
    again = FaceIdentifier.load(tmp_path / "id.pkl")
    crops = texture(2)[15:]
    assert again.predict(crops)[0] == ident.predict(crops)[0]
    assert again.subjects == ["subject_id_01", "subject_id_02"]


# ---------------------------------------------------------------- directory layout
def test_load_subject_crops(tmp_path):
    for sid, seed in (("subject_id_01", 1), ("subject_id_02", 2)):
        d = tmp_path / sid / "face_images"
        d.mkdir(parents=True)
        for k, img in enumerate(texture(seed, n=3)):
            cv2.imwrite(str(d / f"{k}.png"), img)
    (tmp_path / "not_recognized" / "face_images").mkdir(parents=True)
    (tmp_path / "subject_id_03").mkdir()               # no images: skipped
    crops, labels = load_subject_crops(tmp_path)
    assert labels == ["subject_id_01"] * 3 + ["subject_id_02"] * 3
    assert crops[0].shape == (100, 100)


def make_session(tmp_path):
    s = tmp_path / "session_001"
    for trial, seed in (("trial_001", 1), ("trial_002", 2)):
        d = s / "trial_images" / trial
        d.mkdir(parents=True)
        for k, img in enumerate(texture(seed, n=3)):
            cv2.imwrite(str(d / f"frame_{k + 1:03d}.png"), img)
    return s


def test_annotate_session_writes_recognition_log(tmp_path):
    s = make_session(tmp_path)
    log = annotate_session(s, detector=FixedDetector(), identifier=trained_identifier())
    on_disk = json.loads((s / "recognition_log.json").read_text())
    assert on_disk == log and len(log) == 6
    assert log[0]["trial"] == "trial_001" and log[0]["frame"] == "frame_001.png"
    assert set(log[0]["faces"][0]) == {"x", "y", "w", "h", "identity", "prob"}
    assert trial_identities(s / "recognition_log.json") == {
        "trial_001": "subject_id_01", "trial_002": "subject_id_02"}


def test_annotate_session_saves_unrecognized_crops(tmp_path):
    s = make_session(tmp_path)
    ident = trained_identifier()
    ident.reject_prob = 1.01
    out = tmp_path / "not_recognized" / "face_images"
    annotate_session(s, detector=FixedDetector(), identifier=ident, save_unrecognized_to=out)
    assert len(list(out.glob("*.jpg"))) == 6


def test_annotate_session_detection_only(tmp_path):
    s = make_session(tmp_path)
    log = annotate_session(s, detector=FixedDetector())
    assert all(f["identity"] is None for e in log for f in e["faces"])
    assert trial_identities(log) == {}


def test_trial_identities_majority_rule():
    log = [dict(trial="t1", frame=str(k), faces=[dict(identity=i)])
           for k, i in enumerate(["a", "a", "b"])]
    assert trial_identities(log, min_fraction=0.6) == {"t1": "a"}
    assert trial_identities(log, min_fraction=0.7) == {"t1": "unassigned"}


def test_annotate_legacy_database(tmp_path):
    db = tmp_path / "legacy.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE trial_pictures (picture_id INTEGER, trial_number INTEGER, "
                "frame_number INTEGER, image_data BLOB)")
    for pid, img in enumerate(texture(1, n=3)):
        ok, buf = cv2.imencode(".jpg", img)
        con.execute("INSERT INTO trial_pictures VALUES (?,?,?,?)", (pid, 1, pid, buf.tobytes()))
    con.commit()
    con.close()
    assert annotate_legacy_database(db, detector=FixedDetector(), identifier=trained_identifier()) == 3
    assert annotate_legacy_database(db, detector=FixedDetector()) == 0     # already done
    rows = sqlite3.connect(db).execute("SELECT identity FROM trial_faces").fetchall()
    assert [r[0] for r in rows] == ["subject_id_01"] * 3


# ---------------------------------------------------------------- real images (optional)
MF = os.environ.get("MACAQUEFACES_DIR")


@pytest.mark.skipif(not MF, reason="set MACAQUEFACES_DIR to run on real macaque images")
def test_macaque_cascade_finds_faces_in_dataset_crops():
    files = sorted(Path(MF, "data", "MacaqueFaces", "Random").glob("*/*.jpg"))[:200:10]
    assert files, "no images found under MACAQUEFACES_DIR/data/MacaqueFaces/Random"
    det = FaceDetector(verify=False, scale=1.0, min_face=24, min_neighbors=3)
    hits = 0
    for f in files:
        img = cv2.copyMakeBorder(cv2.imread(str(f)), 40, 40, 40, 40, cv2.BORDER_REPLICATE)
        hits += len(det.detect(img)) > 0
    assert hits / len(files) >= 0.5
