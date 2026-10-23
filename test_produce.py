import json
import asyncio
from pathlib import Path
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.server import run_channel
from src.channel_manager import ChannelManager
from src.video_generator import VideoGenerator
from src.script_writer import ScriptWriter

def main():
    mgr = ChannelManager()
    writer = ScriptWriter(provider="claude", api_key="", model="", ollama_url="", lmstudio_url="")
    generator = VideoGenerator(nasa_api_key="DEMO_KEY")
    
    # Let's pick 'crónicasdereddits' which is one of the Reddit channels.
    channel_id = 'crónicasdereddits'
    ch = mgr.get_channel(channel_id)
    if not ch:
        print("Channel not found")
        return
        
    payload_script = {
        "title": "Mi peor cita de Tinder",
        "question": "¿Cuál fue tu peor experiencia en una cita de Tinder?",
        "subreddit": "r/PreguntasReddit",
        "author": "u/throwaway123",
        "upvotes": "15.2k",
        "narration": "Conocí a este chico en Tinder, todo parecía normal. Fuimos a tomar un café y de repente me dice que es un extraterrestre buscando pareja en la Tierra. Al principio pensé que era una broma, pero luego sacó un aparato raro y empezó a escanear mi cara. Salí corriendo y lo bloqueé en todas partes.",
        "language": "es"
    }
    
    edit_options = mgr.get_resolved_edit_options(channel_id)
    
    res = run_channel(
        channel_config=ch,
        writer=writer,
        generator=generator,
        manager=mgr,
        output_dir="output",
        shorts_mode=ch.get("shorts_mode", False),
        transition=ch.get("transition", "fade"),
        edit_options=edit_options,
        custom_script=payload_script,
        custom_images=None
    )
    print("Result:", json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
