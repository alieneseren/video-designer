import cv2
import numpy as np
from PIL import Image
from pathlib import Path

def extract_crayon_characters():
    sheet_path = Path("assets/characters/travel/crayon_character_spritesheet.jpg")
    out_dir = Path("assets/characters/travel")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    sheet = cv2.imread(str(sheet_path))
    gray = cv2.cvtColor(sheet, cv2.COLOR_BGR2GRAY)
    thresh = (gray < 240).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (12, 12))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(closed)
    boxes = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area > 15000 and h > 300: # large character component
            boxes.append((int(x), int(y), int(w), int(h)))

    # Sort left to right
    boxes = sorted(boxes, key=lambda b: b[0])
    print(f"Found {len(boxes)} character components:")
    for b in boxes:
        print(" ", b)

    names = [
        "crayon_char_walk_contact",
        "crayon_char_walk_passing",
        "crayon_char_phone",
        "crayon_char_pointing",
        "crayon_char_worried",
        "crayon_char_coffee"
    ]

    img_h, img_w, _ = sheet.shape

    for idx, (x, y, w, h) in enumerate(boxes[:6]):
        name = names[idx]
        pad = 25
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img_w, x + w + pad)
        y2 = min(img_h, y + h + pad)

        crop = sheet[y1:y2, x1:x2].copy()
        ch, cw, _ = crop.shape

        crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        ink = (crop_gray < 165).astype(np.uint8) * 255

        # Dilate ink to seal micro-gaps
        kernel_seal = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated_ink = cv2.dilate(ink, kernel_seal)

        bg_candidate = ((crop_gray > 220) & (dilated_ink == 0)).astype(np.uint8) * 255

        mask = np.zeros((ch + 2, cw + 2), np.uint8)
        for bx in range(0, cw):
            for by in [0, ch - 1]:
                if bg_candidate[by, bx] == 255:
                    cv2.floodFill(bg_candidate, mask, (bx, by), 128)
        for by in range(0, ch):
            for bx in [0, cw - 1]:
                if bg_candidate[by, bx] == 255:
                    cv2.floodFill(bg_candidate, mask, (bx, by), 128)

        bg_mask = (mask[1:-1, 1:-1] == 1)
        bg_mask_uint8 = bg_mask.astype(np.uint8) * 255
        alpha = np.where(bg_mask_uint8 == 255, 0, 255).astype(np.uint8)

        # Remove tiny speckles
        num_sp, labels_sp, stats_sp, _ = cv2.connectedComponentsWithStats((alpha > 50).astype(np.uint8))
        for i_sp in range(1, num_sp):
            if stats_sp[i_sp, cv2.CC_STAT_AREA] < 80:
                alpha[labels_sp == i_sp] = 0

        orig = cv2.cvtColor(crop, cv2.COLOR_BGR2RGBA)
        orig[:, :, 3] = alpha

        pil_img = Image.fromarray(orig)
        bbox = pil_img.getbbox()
        if bbox:
            b_crop = pil_img.crop(bbox)
        else:
            b_crop = pil_img

        out_file = out_dir / f"{name}.png"
        b_crop.save(out_file, "PNG")
        print(f"Clean Cutout: {name} -> {out_file} (Size: {b_crop.size})")

if __name__ == "__main__":
    extract_crayon_characters()
