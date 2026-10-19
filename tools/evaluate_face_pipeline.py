# -*- coding: utf-8 -*-
"""
evaluate_face_pipeline.py -- benchmark mnky_bx macaque_face.py on the public MacaqueFaces
data (Witham 2018; https://github.com/clwitham/MacaqueFaces).

Usage:
    git clone https://github.com/clwitham/MacaqueFaces
    cd MacaqueFaces && mkdir data && cd data && unzip ../ModelSet/MacaqueFaces.zip && cd ../..
    python tools/evaluate_face_pipeline.py --mf MacaqueFaces \
        --false-positives 34,37,44,52,55,56,58,60,70,71,72,74,75,77,90

--false-positives is a visual labelling of face_eval/detections_macaque.jpg
(which of the 91 macaque-cascade detections are not faces); check it yourself.

Part A -- detection on MacaqueFaces_Test.mp4 (six rhesus monkeys, 1080p):
    every 10th frame (2 fps) is run through the human Haar cascade (what the
    task uses now), the macaque cascade alone, and the macaque cascade with
    eye/nose verification. Detected crops are saved as montages so a person can
    label which are true faces; pass that list with --false-positives.
Part B -- identification on the ModelSet face crops (34 individuals):
    each individual's 100 'Random' images are split in half (train / test).
    (1) 100 random pairs of individuals, the Stage 1 situation (two animals);
    (2) all 34 individuals at once, a colony-scale situation;
    repeated for 10, 25 and 50 training images per animal.
"""
import argparse, glob, itertools, os, random, sys, time
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mnky_bx.face_recognition_system.macaque_face import FaceDetector, FaceIdentifier  # noqa: E402


def part_a(mf, out, fp):
    v = cv2.VideoCapture(os.path.join(mf, "TestVideo", "MacaqueFaces_Test.mp4"))
    frames, i = [], 0
    while True:
        ok, f = v.read()
        if not ok:
            break
        if i % 10 == 0:
            frames.append(f)
        i += 1
    dets = {"human_haar": FaceDetector("human", scale=1.0, min_face=40),
            "macaque": FaceDetector("macaque", verify=False, scale=1.0, min_face=40),
            "macaque_verified": FaceDetector("macaque", verify=True, scale=1.0, min_face=40)}
    print(f"Part A: {len(frames)} frames")
    crops = {}
    for name, d in dets.items():
        t = time.time()
        boxes = [d.detect(f) for f in frames]
        ms = 1000 * (time.time() - t) / len(frames)
        crops[name] = [f[y:y + h, x:x + w] for f, bb in zip(frames, boxes) for (x, y, w, h) in bb]
        print(f"  {name:18s} detections={len(crops[name]):3d}  frames with a detection="
              f"{sum(len(b) > 0 for b in boxes):2d}  {ms:.0f} ms/frame (1080p, this machine)")
        n, cols = len(crops[name]), 14
        M = np.full((max(1, -(-n // cols)) * 84, cols * 84, 3), 255, np.uint8)
        for k, c in enumerate(crops[name]):
            r, cc = divmod(k, cols)
            M[r * 84 + 2:r * 84 + 82, cc * 84 + 2:cc * 84 + 82] = cv2.resize(c, (80, 80))
            cv2.putText(M, str(k), (cc * 84 + 3, r * 84 + 14), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 255), 1)
        cv2.imwrite(os.path.join(out, f"detections_{name}.jpg"), M)
    if fp is not None:
        vd = dets["macaque_verified"]
        gray = [cv2.equalizeHist(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)) for c in crops["macaque"]]
        isface = np.array([k not in fp for k in range(len(gray))])
        passed = np.array([vd._verify_face(g) for g in gray])
        print(f"  macaque cascade: {isface.sum()}/{len(isface)} detections are faces "
              f"(precision {isface.mean():.0%})")
        print(f"  eye/nose verification keeps {passed[isface].sum()}/{isface.sum()} faces and "
              f"{passed[~isface].sum()}/{(~isface).sum()} non-faces")


def part_b(mf, seed=0):
    root = os.path.join(mf, "data", "MacaqueFaces", "Random")
    ids = sorted(os.listdir(root))
    rng = random.Random(seed)
    ident = FaceIdentifier()
    feats = {}
    for a in ids:
        files = sorted(glob.glob(os.path.join(root, a, "*.jpg")))
        rng.shuffle(files)
        feats[a] = np.array([ident.features(cv2.imread(f, cv2.IMREAD_GRAYSCALE)) for f in files])
    print(f"Part B: {len(ids)} individuals, {min(len(v) for v in feats.values())}-"
          f"{max(len(v) for v in feats.values())} images each")
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
    results = {}
    for n_train in (10, 25, 50):
        def fit_eval(group):
            Xtr = np.vstack([feats[a][:n_train] for a in group])
            ytr = np.concatenate([[a] * n_train for a in group])
            Xte = np.vstack([feats[a][50:] for a in group])
            yte = np.concatenate([[a] * len(feats[a][50:]) for a in group])
            clf = LDA(solver="lsqr", shrinkage="auto").fit(Xtr, ytr)
            return (clf.predict(Xte) == yte).mean()
        all_pairs = list(itertools.combinations(ids, 2))
        pairs = [fit_eval(p) for p in random.Random(seed + n_train).sample(all_pairs, 100)]
        allc = fit_eval(ids)
        results[n_train] = (np.mean(pairs), np.percentile(pairs, 5), allc)
        print(f"  {n_train:2d} training images/animal: two animals {np.mean(pairs):.1%} "
              f"(5th pct {np.percentile(pairs, 5):.1%}, {len(pairs)} random pairs); "
              f"all {len(ids)} animals {allc:.1%}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mf", default="MacaqueFaces")
    ap.add_argument("--out", default="face_eval")
    ap.add_argument("--false-positives", default=None,
                    help="comma-separated indices of non-face crops in detections_macaque.jpg")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    fp = None if a.false_positives is None else {int(x) for x in a.false_positives.split(",")}
    part_a(a.mf, a.out, fp)
    part_b(a.mf)
