import os
import random
import shutil

from PIL import Image

try:
    RESAMPLE = Image.Resampling.LANCZOS          # Pillow >= 9.1
except AttributeError:                            # older Pillow
    RESAMPLE = Image.LANCZOS

# ----------------------------- CONFIG ---------------------------------
TIGER_DIR      = r"C:\Users\aadit\OneDrive\Desktop\FaunaAI\Tiger_Photo_Esewa"
INDIVIDUAL_DIR = r"C:\Users\aadit\OneDrive\Desktop\FaunaAI\Individual"
OUT_DIR        = r"C:\Users\aadit\OneDrive\Desktop\FaunaAI\subset_for_colab"

TIGER_COUNT     = 700      # random tiger images to copy
PER_SPECIES_CAP = 70       # max images per 'other' species (keeps it diverse + balanced)
DOWNSCALE_LONG  = 1536     # longest-edge pixels (keeps upload small). 0 = copy originals.
SEED            = 42
IMG_EXT         = (".jpg", ".jpeg", ".png")
# ----------------------------------------------------------------------

random.seed(SEED)


def list_images(root):
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.lower().endswith(IMG_EXT):
                out.append(os.path.join(dirpath, f))
    return out


def save_image(src, dst):
    """Downscale-on-copy to keep the upload small; fall back to a plain copy."""
    if DOWNSCALE_LONG and DOWNSCALE_LONG > 0:
        try:
            im = Image.open(src).convert("RGB")
            w, h = im.size
            scale = DOWNSCALE_LONG / float(max(w, h))
            if scale < 1.0:
                im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), RESAMPLE)
            im.save(dst, "JPEG", quality=90)
            return
        except Exception as e:
            print(f"  ! downscale failed for {os.path.basename(src)} ({e}); copying original")
    shutil.copy2(src, dst)


def unique_name(folder, name):
    """Keep the original filename (it carries the camera/deployment id); avoid collisions."""
    base, ext = os.path.splitext(name)
    cand, i = name, 1
    while os.path.exists(os.path.join(folder, cand)):
        cand = f"{base}__dup{i}{ext}"
        i += 1
    return cand


def main():
    print(f"Output: {OUT_DIR}")
    print(f"Downscale longest edge: {DOWNSCALE_LONG or 'OFF (originals)'}\n")

    # ---- TIGER (flat folder of crops) ----
    tiger_out = os.path.join(OUT_DIR, "tiger")
    os.makedirs(tiger_out, exist_ok=True)
    tigers = list_images(TIGER_DIR)
    if not tigers:
        print(f"!! No images found under {TIGER_DIR} — check the path.")
        return
    random.shuffle(tigers)
    tigers = tigers[:TIGER_COUNT]
    for src in tigers:
        dst = os.path.join(tiger_out, unique_name(tiger_out, os.path.basename(src)))
        save_image(src, dst)
    print(f"TIGER: copied {len(tigers)} images")

    # ---- OTHER (one subfolder per species, preserved) ----
    other_root = os.path.join(OUT_DIR, "other")
    os.makedirs(other_root, exist_ok=True)
    species_dirs = [d for d in os.listdir(INDIVIDUAL_DIR)
                    if os.path.isdir(os.path.join(INDIVIDUAL_DIR, d))]
    if not species_dirs:
        print(f"!! No species subfolders under {INDIVIDUAL_DIR} — check the path.")
        return

    total_other = 0
    print("OTHER (per species):")
    for sp in sorted(species_dirs):
        imgs = list_images(os.path.join(INDIVIDUAL_DIR, sp))
        random.shuffle(imgs)
        imgs = imgs[:PER_SPECIES_CAP]
        sp_out = os.path.join(other_root, sp)
        os.makedirs(sp_out, exist_ok=True)
        for src in imgs:
            dst = os.path.join(sp_out, unique_name(sp_out, os.path.basename(src)))
            save_image(src, dst)
        total_other += len(imgs)
        print(f"  {sp}: {len(imgs)}")
    print(f"OTHER: copied {total_other} images across {len(species_dirs)} species")

    print("\n" + "=" * 60)
    print(f"DONE.  tiger={len(tigers)}  other={total_other}")
    print("Next steps:")
    print(f"  1. Zip this folder:  {OUT_DIR}")
    print( "  2. Upload the zip to Google Drive (e.g. MyDrive/subset_for_colab.zip)")
    print( "  3. Open the Colab notebook and run it (GPU runtime).")
    print("=" * 60)


if __name__ == "__main__":
    main()
