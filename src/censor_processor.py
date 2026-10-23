import os
import cv2
import urllib.request
import numpy as np
from pathlib import Path

class NASALogoCensor:
    MEATBALL_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/NASA_logo.svg/330px-NASA_logo.svg.png"
    WORM_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/NASA_Worm_logo.svg/330px-NASA_Worm_logo.svg.png"
    
    def __init__(self, template_dir: str = "config/assets/templates"):
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        self.meatball_path = self.template_dir / "nasa_meatball.png"
        self.worm_path = self.template_dir / "nasa_worm.png"
        
        # Download templates if missing
        self._ensure_templates()
        
        # Initialize detector
        try:
            self.detector = cv2.SIFT_create()
            self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
            self.ratio_threshold = 0.7
            self.use_sift = True
            print("[CENSOR] SIFT detector initialized.")
        except AttributeError:
            self.detector = cv2.ORB_create(nfeatures=1000)
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            self.ratio_threshold = 0.8
            self.use_sift = False
            print("[CENSOR] SIFT not available, ORB detector initialized.")
            
        # Load templates and compute descriptors
        self.templates = []
        self._load_template(self.meatball_path, "meatball")
        self._load_template(self.worm_path, "worm")

    def _ensure_templates(self):
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        for path, url in [(self.meatball_path, self.MEATBALL_URL), (self.worm_path, self.WORM_URL)]:
            if not path.exists():
                try:
                    print(f"[CENSOR] Downloading NASA template from {url}...")
                    r = requests.get(url, headers=headers, timeout=15)
                    r.raise_for_status()
                    with open(path, "wb") as f:
                        f.write(r.content)
                    print(f"[CENSOR] Downloaded template saved to {path}")
                except Exception as e:
                    print(f"[CENSOR] Error downloading template from {url}: {e}")

    def _load_template(self, path: Path, label: str):
        if not path.exists():
            return
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"[CENSOR] Warning: Failed to load template image at {path}")
            return
        kp, des = self.detector.detectAndCompute(img, None)
        if des is not None:
            self.templates.append({
                "label": label,
                "img": img,
                "kp": kp,
                "des": des,
                "shape": img.shape
            })
            print(f"[CENSOR] Template '{label}' loaded successfully with {len(kp)} keypoints.")
        else:
            print(f"[CENSOR] Warning: No features found in template '{label}' at {path}")

    def _sort_box_points(self, pts):
        # pts is np.array of shape (4, 2)
        xSorted = pts[np.argsort(pts[:, 0]), :]
        leftMost = xSorted[:2, :]
        rightMost = xSorted[2:, :]
        
        leftMost = leftMost[np.argsort(leftMost[:, 1]), :]
        (tl, bl) = leftMost
        
        rightMost = rightMost[np.argsort(rightMost[:, 1]), :]
        (tr, br) = rightMost
        
        return np.array([tl, tr, br, bl], dtype="float32")

    def detect_logo_color_fallback(self, frame_bgr) -> list[np.ndarray]:
        """
        Color-based circular contour detector for the NASA meatball blue logo.
        Returns a list of 4-point arrays representing perspective corners of detected logos.
        """
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        # NASA Blue: Hue is roughly 110 (220 deg / 2). Let's expand range slightly
        lower_blue = np.array([100, 100, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Morphological close to fill gaps inside the circle
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected_boxes = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Size limits based on frame size (e.g. at least 150 pixels, at most 15% of frame area)
            h, w = frame_bgr.shape[:2]
            max_area = w * h * 0.15
            if 150 < area < max_area:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter == 0:
                    continue
                circularity = 4 * np.pi * area / (perimeter ** 2)
                # A circle has circularity ~1.0. Let's match circularity > 0.65
                if circularity > 0.65:
                    rect = cv2.minAreaRect(cnt)
                    box = cv2.boxPoints(rect)
                    sorted_box = self._sort_box_points(box)
                    detected_boxes.append(sorted_box)
                    
        return detected_boxes

    def process_frame(self, frame_rgb: np.ndarray, censor_logo_path: str) -> np.ndarray:
        """
        Processes a single frame (RGB format) and overlays censor logo on NASA logo in perspective.
        """
        if not censor_logo_path or not os.path.exists(censor_logo_path):
            return frame_rgb # No censor logo, skip
            
        censor_img = cv2.imread(censor_logo_path, cv2.IMREAD_UNCHANGED)
        if censor_img is None:
            return frame_rgb
            
        # Ensure censor image has BGR + Alpha
        if censor_img.ndim == 2:
            censor_img = cv2.cvtColor(censor_img, cv2.COLOR_GRAY2BGRA)
        elif censor_img.shape[2] == 3:
            censor_img = cv2.cvtColor(censor_img, cv2.COLOR_BGR2BGRA)
            
        fh, fw = frame_rgb.shape[:2]
        ch, cw = censor_img.shape[:2]
        censor_corners = np.float32([[0, 0], [cw - 1, 0], [cw - 1, ch - 1], [0, ch - 1]])
        
        # OpenCV works with BGR
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # Optimize speed: if frame is large, downscale for feature detection
        max_dim = 640
        scale_factor = 1.0
        if max(fh, fw) > max_dim:
            scale_factor = max_dim / max(fh, fw)
            dw = int(fw * scale_factor)
            dh = int(fh * scale_factor)
            detect_gray = cv2.resize(frame_gray, (dw, dh), interpolation=cv2.INTER_AREA)
        else:
            detect_gray = frame_gray
            
        kp_frame, des_frame = self.detector.detectAndCompute(detect_gray, None)
        
        censor_applied = False
        
        # 1. Feature Matching (SIFT/ORB)
        if des_frame is not None and len(kp_frame) > 0:
            for temp in self.templates:
                if temp["des"] is None or len(temp["des"]) < 4:
                    continue
                    
                matches = self.matcher.knnMatch(temp["des"], des_frame, k=2)
                good_matches = []
                for match_pair in matches:
                    if len(match_pair) == 2:
                        m, n = match_pair
                        if m.distance < self.ratio_threshold * n.distance:
                            good_matches.append(m)
                            
                if len(good_matches) >= 4:
                    # Get coordinates of matching points
                    src_pts = np.float32([temp["kp"][m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                    dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                    
                    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                    if H is not None and mask is not None:
                        inliers = np.sum(mask)
                        if inliers >= 4:
                            # Map clean corners of template to the frame coordinates (rescaled if needed)
                            th, tw = temp["shape"]
                            temp_corners = np.float32([[0, 0], [tw - 1, 0], [tw - 1, th - 1], [0, th - 1]]).reshape(-1, 1, 2)
                            dst_corners_scaled = cv2.perspectiveTransform(temp_corners, H).reshape(-1, 2)
                            
                            # Scale coordinates back to original size
                            dst_corners = dst_corners_scaled / scale_factor
                            
                            # Warp censor logo to original frame size
                            M_warp = cv2.getPerspectiveTransform(censor_corners, dst_corners.astype(np.float32))
                            warped_censor = cv2.warpPerspective(censor_img, M_warp, (fw, fh))
                            
                            # Blend warped censor onto frame
                            c_bgr = warped_censor[:, :, :3]
                            c_alpha = warped_censor[:, :, 3:4] / 255.0
                            
                            frame_bgr = (1.0 - c_alpha) * frame_bgr + c_alpha * c_bgr
                            censor_applied = True
                            print(f"[CENSOR] Detected and censored '{temp['label']}' logo using feature matching. Inliers: {inliers}")
                            
        # 2. Color-based Fallback (for circular meatball logo)
        if not censor_applied:
            detected_color_boxes = self.detect_logo_color_fallback(frame_bgr)
            for box in detected_color_boxes:
                M_warp = cv2.getPerspectiveTransform(censor_corners, box)
                warped_censor = cv2.warpPerspective(censor_img, M_warp, (fw, fh))
                
                c_bgr = warped_censor[:, :, :3]
                c_alpha = warped_censor[:, :, 3:4] / 255.0
                
                frame_bgr = (1.0 - c_alpha) * frame_bgr + c_alpha * c_bgr
                censor_applied = True
                print("[CENSOR] Detected and censored circular NASA logo using HSV color fallback.")
                
        if censor_applied:
            frame_bgr = np.clip(frame_bgr, 0, 255).astype(np.uint8)
            return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            
        return frame_rgb
