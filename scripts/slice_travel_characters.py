import cv2
import numpy as np
from PIL import Image
from pathlib import Path

def extract_all_travel_characters_sealed():
    sheet_path = Path("assets/characters/travel/traveler_spritesheet.jpg")
    out_dir = Path("assets/characters/travel")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    sheet = cv2.imread(str(sheet_path))
    gray_sheet = cv2.cvtColor(sheet, cv2.COLOR_BGR2GRAY)
    thresh = (gray_sheet < 235).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(closed)
    boxes = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area > 8000 and h > 150:
            boxes.append((int(x), int(y), int(w), int(h)))

    top_row = sorted([b for b in boxes if b[1] < 300], key=lambda b: b[0])
    bot_row = sorted([b for b in boxes if b[1] >= 300], key=lambda b: b[0])
    
    all_boxes = top_row + bot_row
    
    names = [
        # Top Row
        "traveler_walking",
        "traveler_photographer",
        "traveler_exhausted",
        "traveler_lost_map",
        # Bottom Row
        "traveler_confused",
        "traveler_coffee",
        "traveler_foodie",
        "traveler_vlogger"
    ]
    
    img_h, img_w, _ = sheet.shape
    
    for idx, (x, y, w, h) in enumerate(all_boxes):
        name = names[idx]
        pad = 22
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img_w, x + w + pad)
        y2 = min(img_h, y + h + pad)
        
        crop = sheet[y1:y2, x1:x2].copy()
        ch, cw, _ = crop.shape
        
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        ink = (gray < 165).astype(np.uint8) * 255
        
        # Dilate ink to seal micro-gaps
        kernel_seal = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated_ink = cv2.dilate(ink, kernel_seal)
        
        # Background candidates: bright white and not ink
        bg_candidate = ((gray > 220) & (dilated_ink == 0)).astype(np.uint8) * 255
        
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
        print(f"Perfect Cut: {name} -> {out_file} (Size: {b_crop.size})")

if __name__ == "__main__":
    extract_all_travel_characters_sealed()
