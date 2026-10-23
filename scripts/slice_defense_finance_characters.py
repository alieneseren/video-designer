import cv2
import numpy as np
from PIL import Image
from pathlib import Path

def extract_defense_finance_characters():
    sheet_path = Path("assets/characters/defense_finance/crayon_defense_finance_sheet.jpg")
    out_dir = Path("assets/characters/defense_finance")
    out_dir.mkdir(parents=True, exist_ok=True)

    sheet = cv2.imread(str(sheet_path))
    h, w, _ = sheet.shape

    # 4 columns: CEO, General, Tech Founder, Wall Street Trader
    splits = [
        ("crayon_defense_ceo", 0, 380),
        ("crayon_pentagon_general", 380, 735),
        ("crayon_tech_founder", 735, 1025),
        ("crayon_wall_street_trader", 1025, 1376)
    ]

    for name, x1, x2 in splits:
        crop = sheet[:674, x1:x2].copy()
        cnh, cnw, _ = crop.shape

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        ink = (gray < 165).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated_ink = cv2.dilate(ink, kernel)

        bg_candidate = ((gray > 220) & (dilated_ink == 0)).astype(np.uint8) * 255
        mask = np.zeros((cnh + 2, cnw + 2), np.uint8)

        # Floodfill from perimeter
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

        # Retain only components belonging to the main character
        num_sp, labels_sp, stats_sp, _ = cv2.connectedComponentsWithStats((alpha > 50).astype(np.uint8))
        if num_sp > 1:
            main_idx = np.argmax(stats_sp[1:, cv2.CC_STAT_AREA]) + 1
            for i_sp in range(1, num_sp):
                if i_sp != main_idx and stats_sp[i_sp, cv2.CC_STAT_AREA] < 2000:
                    alpha[labels_sp == i_sp] = 0

        orig = cv2.cvtColor(crop, cv2.COLOR_BGR2RGBA)
        orig[:, :, 3] = alpha

        pil_img = Image.fromarray(orig)
        bbox = pil_img.getbbox()
        if bbox:
            b_crop = pil_img.crop(bbox)
        else:
            b_crop = pil_img

        out_path = out_dir / f"{name}.png"
        b_crop.save(out_path)
        print(f"Extracted: {name} -> {out_path} (Size: {b_crop.size})")

if __name__ == "__main__":
    extract_defense_finance_characters()
