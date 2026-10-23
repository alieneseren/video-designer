import os
import time
import json
import glob
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from .models import Scenario

def _resolve_whatsapp_base_config() -> Path:
    candidates = [
        Path("/home/ubuntu/yt-render-server/assets/whatsapp"),
        Path(__file__).resolve().parent.parent / "assets" / "whatsapp",
        Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp",
        Path("config/assets/whatsapp").resolve()
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp"

BASE_CONFIG = _resolve_whatsapp_base_config()
DEFAULT_TEMPLATE = str(BASE_CONFIG / "templates" / "whatsapp_chat.html")
DEFAULT_WALLPAPER = str(BASE_CONFIG / "assets" / "wallpapers" / "urban_wall.jpg")

class VideoRenderer:
    def __init__(
        self,
        template_path: str = DEFAULT_TEMPLATE,
        temp_dir: str = "/tmp/whatsapp_render"
    ):
        self.template_path = template_path
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def prepare_html(self, scenario: Scenario) -> str:
        with open(self.template_path, "r", encoding="utf-8") as f:
            template = f.read()

        # Resolve avatar path robustly
        avatar_path = None
        if scenario.contact_avatar:
            if os.path.isabs(scenario.contact_avatar) and os.path.exists(scenario.contact_avatar):
                avatar_path = scenario.contact_avatar
            elif os.path.exists(scenario.contact_avatar):
                avatar_path = os.path.abspath(scenario.contact_avatar)
            elif (BASE_CONFIG / "assets" / "avatars" / scenario.contact_avatar).exists():
                avatar_path = str(BASE_CONFIG / "assets" / "avatars" / scenario.contact_avatar)

        if not avatar_path or not os.path.exists(avatar_path):
            # Fallback based on contact gender / name
            cname = (scenario.contact_name or "").lower()
            is_fem = (getattr(scenario, "contact_avatar_gender", None) == "female" or
                      any(w in cname for w in ["anne", "merve", "ayşe", "zeynep", "fatma", "aşkım", "prenses", "sevgili", "kız", "valide", "abla", "kaynana", "hatun", "karım"]))
            def_name = "female.png" if is_fem else "male.png"
            avatar_path = str(BASE_CONFIG / "assets" / "avatars" / def_name)
        
        # Base64 data URI to prevent any file:// policy/CORS issues in headless Chromium
        try:
            import base64
            with open(avatar_path, "rb") as af:
                av_b64 = base64.b64encode(af.read()).decode("utf-8")
            ext = os.path.splitext(avatar_path)[1].lower().replace(".", "")
            mime = "image/png" if ext == "png" else ("image/jpeg" if ext in ("jpg", "jpeg") else "image/png")
            avatar_uri = f"data:{mime};base64,{av_b64}"
        except Exception:
            avatar_uri = f"file://{avatar_path}"

        wallpaper_path = os.path.abspath(DEFAULT_WALLPAPER)
        try:
            import base64
            with open(wallpaper_path, "rb") as wf:
                wp_b64 = base64.b64encode(wf.read()).decode("utf-8")
            wallpaper_uri = f"data:image/jpeg;base64,{wp_b64}"
        except Exception:
            wallpaper_uri = f"file://{wallpaper_path}"

        scenario_dict = scenario.to_dict()
        scenario_json = json.dumps(scenario_dict, ensure_ascii=False)

        html = template.replace("{{ layout }}", scenario.layout)
        html = html.replace("{{ theme }}", scenario.theme)
        html = html.replace("{{ contact_name }}", scenario.contact_name)
        html = html.replace("{{ contact_status }}", scenario.contact_status)
        html = html.replace("{{ contact_avatar }}", avatar_uri)
        html = html.replace("{{ watermark_username }}", scenario.watermark_username)
        html = html.replace("{{ wallpaper_uri }}", wallpaper_uri)
        html = html.replace("{{ scenario_json }}", scenario_json)

        def resolve_layout_block(content: str, block_layout: str, is_active: bool) -> str:
            start_tag = f'{{% if layout == "{block_layout}" %}}'
            end_tag = "{% endif %}"
            while start_tag in content:
                p1 = content.find(start_tag)
                p2 = content.find(end_tag, p1)
                if p2 == -1:
                    break
                p2_end = p2 + len(end_tag)
                if is_active:
                    inner = content[p1 + len(start_tag):p2]
                    content = content[:p1] + inner + content[p2_end:]
                else:
                    content = content[:p1] + content[p2_end:]
            return content

        html = resolve_layout_block(html, "fullscreen", scenario.layout == "fullscreen")
        html = resolve_layout_block(html, "compact_top", scenario.layout == "compact_top")
        html = resolve_layout_block(html, "viral_chat", scenario.layout == "viral_chat")

        rendered_html_path = os.path.join(self.temp_dir, "rendered_chat.html")
        with open(rendered_html_path, "w", encoding="utf-8") as f:
            f.write(html)

        return os.path.abspath(rendered_html_path)

    def render_video(
        self,
        scenario: Scenario,
        master_audio_path: str,
        total_duration: float,
        output_mp4_path: str
    ) -> str:
        html_file = self.prepare_html(scenario)
        rec_dir = os.path.join(self.temp_dir, "recordings")
        os.makedirs(rec_dir, exist_ok=True)

        for f in glob.glob(os.path.join(rec_dir, "*")):
            try:
                os.remove(f)
            except Exception:
                pass

        print(f"[Renderer] Launching Chromium to capture 1080x1920 video ({total_duration:.1f}s)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--allow-file-access-from-files"
                ]
            )
            context = browser.new_context(
                record_video_dir=rec_dir,
                record_video_size={"width": 1080, "height": 1920},
                viewport={"width": 1080, "height": 1920},
                device_scale_factor=1
            )
            page = context.new_page()
            page.goto(f"file://{html_file}")

            # Wait for animation duration + lead time
            time.sleep(total_duration + 0.5)

            context.close()
            browser.close()

        rec_files = glob.glob(os.path.join(rec_dir, "*.webm"))
        if not rec_files:
            raise RuntimeError("Playwright failed to record video.")

        recorded_webm = rec_files[0]
        print(f"[Renderer] Video recorded. Merging with master audio via FFmpeg...")

        os.makedirs(os.path.dirname(os.path.abspath(output_mp4_path)), exist_ok=True)

        # For compact_top layout (Bi' Dublaj / Hamza Dublaj style):
        # Prepare ASMR/gameplay background for the bottom 960px
        asmr_bg_file = os.path.join(self.temp_dir, "bottom_asmr.mp4")
        has_asmr = False
        if scenario.layout == "compact_top":
            try:
                try:
                    from asmr_manager import prepare_asmr_background
                except ImportError:
                    from src.asmr_manager import prepare_asmr_background

                print(f"[Renderer] ASMR/Gameplay arka planı hazırlanıyor (Süre: {total_duration + 3.0:.1f}s)...")
                prepare_asmr_background(
                    target_duration=total_duration + 3.0,
                    output_path=asmr_bg_file,
                    width=1080,
                    height=960,
                    fps=30
                )
                if os.path.exists(asmr_bg_file) and os.path.getsize(asmr_bg_file) > 1000:
                    has_asmr = True
                    print(f"[Renderer] ASMR arka planı hazır: {asmr_bg_file}")
            except Exception as asmr_err:
                print(f"[Renderer] ASMR arka plan hazırlama uyarısı: {asmr_err}")

        if has_asmr:
            filter_complex = (
                "[0:v]crop=1080:960:0:0[top_chat];"
                "[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=30[bottom_asmr];"
                "[top_chat][bottom_asmr]vstack[v]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", recorded_webm,
                "-i", asmr_bg_file,
                "-i", master_audio_path,
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "2:a",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-threads", "4",
                "-pix_fmt", "yuv420p",
                "-af", "loudnorm=I=-14:LRA=7:tp=-1.5",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                output_mp4_path
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-i", recorded_webm,
                "-i", master_audio_path,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-threads", "4",
                "-pix_fmt", "yuv420p",
                "-af", "loudnorm=I=-14:LRA=7:tp=-1.5",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                output_mp4_path
            ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[Renderer] Video rendered successfully -> {output_mp4_path}")
        return output_mp4_path
