import cv2
import numpy as np
from PIL import Image
from pathlib import Path

def extract_aviation_characters():
    sheet_path = Path("assets/characters/aviation/crayon_aviation_spritesheet.jpg")
    out_dir = Path("assets/characters/aviation")
    out_dir.mkdir(parents=True, exist_ok=True)

    sheet = cv2.imread(str(sheet_path))
    h, w, _ = sheet.shape
    cols = 3
    rows = 2
    cell_w = w / cols
    cell_h = h / rows

    names = [
        # Row 1
        "crayon_captain_yoke",
        "crayon_captain_confused",
        "crayon_fo_pointing",
        # Row 2
        "crayon_fo_shocked",
        "crayon_atc_radio",
        "crayon_ntsb_inspector",
    ]

    idx = 0
    for r in range(rows):
        for c in range(cols):
            name = names[idx]
            x1 = int(c * cell_w)
            y1 = int(r * cell_h)
            x2 = int((c + 1) * cell_w)
            y2 = int((r + 1) * cell_h)

            crop = sheet[y1:y2, x1:x2].copy()
            ch, cw, _ = crop.shape

            # Crop out text label at the bottom of each cell (lower 50px)
            crop_no_label = crop[:ch - 48, :].copy()
            cnh, cnw, _ = crop_no_label.shape

            gray = cv2.cvtColor(crop_no_label, cv2.COLOR_BGR2GRAY)
            ink = (gray < 165).astype(np.uint8) * 255
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            dilated_ink = cv2.dilate(ink, kernel)

            bg_candidate = ((gray > 220) & (dilated_ink == 0)).astype(np.uint8) * 255
            mask = np.zeros((cnh + 2, cnw + 2), np.uint8)

            for bx in range(0, cnw):
                for by in [0, cnh - 1]:
                    if bg_candidate[by, bx] == 255:
                        cv2.floodFill(bg_candidate, mask, (bx, by), 128)
            for by in range(0, cnh):
                for bx in [0, cnw - 1]:
                    if bg_candidate[by, bx] == 255:
                        cv2.floodFill(bg_candidate, mask, (bx, by), 128)

            bg_mask = (mask[1:-1, 1:-1] == 1)
            alpha = np.where(bg_mask, 0, 255).astype(np.uint8)

            # Keep only the largest main component (removes any stray label remnants or speckles)
            num_sp, labels_sp, stats_sp, _ = cv2.connectedComponentsWithStats((alpha > 50).astype(np.uint8))
            main_idx = np.argmax(stats_sp[1:, cv2.CC_STAT_AREA]) + 1
            for i_sp in range(1, num_sp):
                if i_sp != main_idx and stats_sp[i_sp, cv2.CC_STAT_AREA] < 3000:
                    alpha[labels_sp == i_sp] = 0

            orig = cv2.cvtColor(crop_no_label, cv2.COLOR_BGR2RGBA)
            orig[:, :, 3] = alpha

            pil_img = Image.fromarray(orig)
            bbox = pil_img.getbbox()
            if bbox:
                b_crop = pil_img.crop(bbox)
            else:
                b_crop = pil_img

            out_path = out_dir / f"{name}.png"
            b_crop.save(out_path)
            print(f"Aviation Cutout {idx}: {name} -> {out_path} (Size: {b_crop.size})")
            idx += 1

if __name__ == "__main__":
    extract_aviation_characters()
