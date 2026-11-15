"""
Run Basketball Engine 2.0 on Kontrol Jobs
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, "/Users/alienes/yt-oto-video/files")
sys.path.insert(0, "/Users/alienes/yt-oto-video/files/src")

from src.modules.basketball.orchestrator import BasketballOrchestrator

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("RunBasketballV2")

JOBS = [
    {
        "job_id": "exec_mat_20261104_224042_The_Deceleration_Secret_Behind",
        "athlete_key": "james_harden",
        "topic": "The Deceleration Secret Behind James Harden Step-Back Jumper Biomechanics Houston Rockets"
    },
    {
        "job_id": "exec_mat_20261104_224042_The_Neurobiology_of_Derek_Fish",
        "athlete_key": "derek_fisher",
        "topic": "The Neurobiology of Derek Fisher 0.4 Second Buzzer Beater 2004 NBA Playoffs Spurs vs Lakers"
    }
]

def main():
    parser = argparse.ArgumentParser(description="Run Basketball Engine 2.0")
    parser.add_argument("--bypass-cache", action="store_true", default=True, help="Bypass and clear local media cache")
    parser.add_argument("--job", type=str, default="", help="Specific job ID to render")
    args = parser.parse_args()

    bypass_cache = args.bypass_cache or os.environ.get("BYPASS_CACHE", "1").lower() in ["1", "true", "yes"]

    orchestrator = BasketballOrchestrator(channel_id="thebasketballshows")
    jobs_to_run = [j for j in JOBS if not args.job or j["job_id"] == args.job]

    for job in jobs_to_run:
        try:
            logger.info(f"\n🎬 {job['job_id']} üretimi başlatılıyor (bypass_cache={bypass_cache})...")
            orchestrator.produce_video(
                job_id=job["job_id"],
                athlete_key=job["athlete_key"],
                topic=job["topic"],
                voice_clone_id="vc_1792868444",
                force_rebuild=True,
                bypass_cache=bypass_cache
            )
        except Exception as e:
            logger.error(f"❌ Hata ({job['job_id']}): {e}", exc_info=True)
            raise e

    logger.info("\n🎉 TÜM VİDEOLAR BASKETBALL ENGINE 2.0 İLE BAŞARIYLA ÜRETİLDİ!")

if __name__ == "__main__":
    main()
