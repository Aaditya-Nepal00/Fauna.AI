"""
Batch test script for Fauna.AI FrameGuard.
Samples ~50-60 images spread across Tiger_Photo_Esewa and prints per-image
triage, flank, flank_conf, night, species_hint, species_conf, crop_blur,
whole_blur, blown_frac. Then prints distribution summaries.

Run from project root:
    cd backend && python batch_test.py
"""
import os
import sys
import random
import logging

logging.basicConfig(level=logging.WARNING, format="%(levelname)-5s %(message)s")

# Must run from backend/
sys.path.insert(0, ".")

from app.pipeline.frame_guard import FrameGuard

TIGER_DIR = r"C:\Users\aadit\OneDrive\Desktop\FaunaAI\Tiger_Photo_Esewa"
SAMPLE_SIZE = 60
SEED = 42

def sample_images(root: str, n: int, seed: int) -> list[str]:
    """Walk the folder tree and return a random stratified sample."""
    all_files = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith((".jpg", ".jpeg", ".png")):
                all_files.append(os.path.join(dirpath, fn))
    random.seed(seed)
    random.shuffle(all_files)
    return all_files[:n]

def main():
    print(f"\nLoading FrameGuard...")
    fg = FrameGuard()
    print(f"backend={fg.backend}  flank_mode={fg.flank_mode}\n")

    paths = sample_images(TIGER_DIR, SAMPLE_SIZE, SEED)
    print(f"Sampled {len(paths)} images from {TIGER_DIR}\n")

    header = (
        f"{'#':>3}  {'triage':<14} {'flank':<10} {'flank_conf':>10}  "
        f"{'night':<5} {'sp_hint':<28} {'sp_conf':>7}  "
        f"{'crop_blur':>9} {'whole_blur':>10} {'blown':>6}  filename"
    )
    print(header)
    print("-" * len(header))

    results = []
    for i, path in enumerate(paths, 1):
        try:
            r = fg.process(path)
            flank = r.flank or "-"
            fc = f"{r.flank_confidence:.2f}" if r.flank_confidence is not None else "-"
            hint = (r.species_hint or "-")[:27]
            sc = f"{r.species_confidence:.2f}" if r.species_confidence is not None else "-"
            cb = f"{r.crop_blur_score:.1f}" if r.crop_blur_score is not None else "-"
            wb = f"{r.blur_score:.1f}"
            bf = f"{r.blown_fraction:.3f}" if r.blown_fraction is not None else "-"
            fname = os.path.basename(path)
            print(
                f"{i:>3}  {r.triage.value:<14} {flank:<10} {fc:>10}  "
                f"{'Y' if r.is_night else 'N':<5} {hint:<28} {sc:>7}  "
                f"{cb:>9} {wb:>10} {bf:>6}  {fname}"
            )
            results.append(r)
        except Exception as e:
            print(f"{i:>3}  ERROR: {e}  ({os.path.basename(path)})")

    # ── Distribution summaries ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("TRIAGE DISTRIBUTION")
    print(f"{'='*60}")
    triage_counts: dict[str, int] = {}
    for r in results:
        k = r.triage.value
        triage_counts[k] = triage_counts.get(k, 0) + 1
    for k, v in sorted(triage_counts.items(), key=lambda x: -x[1]):
        pct = v / len(results) * 100
        print(f"  {k:<18} {v:>3}  ({pct:.0f}%)")

    tigers = [r for r in results if r.triage.value == "TIGER"]
    if tigers:
        print(f"\n{'='*60}")
        print(f"FLANK DISTRIBUTION  ({len(tigers)} tigers)")
        print(f"{'='*60}")
        flank_counts: dict[str, int] = {}
        for r in tigers:
            k = r.flank or "None"
            flank_counts[k] = flank_counts.get(k, 0) + 1
        for k, v in sorted(flank_counts.items(), key=lambda x: -x[1]):
            pct = v / len(tigers) * 100
            print(f"  {k:<12} {v:>3}  ({pct:.0f}%)")

        confs = [r.flank_confidence for r in tigers if r.flank_confidence is not None]
        if confs:
            print(f"\n  flank_confidence stats over {len(confs)} tiger images:")
            confs_sorted = sorted(confs)
            print(f"    min={min(confs):.2f}  max={max(confs):.2f}  "
                  f"median={confs_sorted[len(confs)//2]:.2f}  "
                  f"mean={sum(confs)/len(confs):.2f}")
            buckets = [0, 0, 0, 0, 0]  # <0.55, 0.55-0.60, 0.60-0.70, 0.70-0.85, >=0.85
            for c in confs:
                if c < 0.55:
                    buckets[0] += 1
                elif c < 0.60:
                    buckets[1] += 1
                elif c < 0.70:
                    buckets[2] += 1
                elif c < 0.85:
                    buckets[3] += 1
                else:
                    buckets[4] += 1
            labels = ["<0.55", "0.55-0.60", "0.60-0.70", "0.70-0.85", ">=0.85"]
            print("    Confidence histogram:")
            for label, cnt in zip(labels, buckets):
                print(f"      {label:<12} {cnt:>3}")

    print(f"\nDone. {len(results)}/{len(paths)} processed successfully.")

if __name__ == "__main__":
    main()
