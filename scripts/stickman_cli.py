#!/usr/bin/env python3
"""
stickman_cli.py
===============
Unified Command-Line Production Tool for:
1. Aviation / BlackboxAudioo Documentaries (Articulated Cockpit CVR, ATC Tower, NTSB)
2. Travel & Walking Vlogs (Articulated Walk Cycle, Foot Roll, Hand Gestures, Inner Monologue)
3. Crayon Capital Unified 2D World Scenes (Illustrated Environment + Character)

Usage Examples:
# Aviation Cockpit CVR Scene:
python3 scripts/stickman_cli.py aviation --scene cockpit \
    --flight "AIR FLORIDA FLIGHT 90" \
    --cap "Yes it is, there's eighty knots..." \
    --fo "Larry, that don't look right, does it?" \
    --bank 38 \
    --output output/stickman_demos/blackbox_cockpit_cvr.mp4

# Aviation ATC Tower Scene:
python3 scripts/stickman_cli.py aviation --scene atc \
    --facility "WASHINGTON NATIONAL TOWER (DCA)" \
    --text "Palm 90, Washington Tower, Runway 36 cleared for takeoff!" \
    --output output/stickman_demos/blackbox_atc_tower.mp4

# Travel Vlog with Illustrated Crayon Street:
python3 scripts/stickman_cli.py crayon-world \
    --text "Galata sokaklarında 14 bin adım... Bu tarihi kafede bir kahve molası her şeye değer!" \
    --output output/stickman_demos/crayon_capital_masterpiece.mp4
"""

import sys
import argparse
from pathlib import Path
from PIL import Image

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.stickman_engine import (
    StickmanEngine,
    CrayonSceneProducer,
    CrayonWorldEngine,
    AviationSceneProducer,
    SatireSceneProducer,
    CrayonStrutProducer,
    ArticulatedRig,
)


def main():
    parser = argparse.ArgumentParser(description="Stickman & Animated Character Production Engine CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Aviation / Blackbox Command
    av_p = subparsers.add_parser("aviation", help="Generate BlackboxAudioo aviation scenes")
    av_p.add_argument("--scene", choices=["cockpit", "atc"], default="cockpit", help="Scene type")
    av_p.add_argument("--flight", default="AIR FLORIDA FLIGHT 90", help="Flight name / Number")
    av_p.add_argument("--situation", default="COCKPIT EMERGENCY // STALL & LOSS OF CONTROL", help="Situation title")
    av_p.add_argument("--cap", default="Yes it is, there's eighty knots...", help="Captain CVR quote")
    av_p.add_argument("--fo", default="Larry, that don't look right, does it?", help="First Officer CVR quote")
    av_p.add_argument("--facility", default="WASHINGTON NATIONAL TOWER (DCA)", help="ATC Facility name")
    av_p.add_argument("--text", default="Palm 90, Washington Tower, Runway 36 cleared for takeoff!", help="ATC transmission")
    av_p.add_argument("--bank", type=float, default=38.0, help="Aircraft bank angle")
    av_p.add_argument("--duration", "-d", type=float, default=5.5, help="Duration in seconds")
    av_p.add_argument("--output", "-o", default="output/stickman_demos/blackbox_demo.mp4", help="Output file path")

    # 2. Crayon World Scene Command
    world_p = subparsers.add_parser("crayon-world", help="Generate full Crayon Capital illustrated world scene")
    world_p.add_argument("--text", "-t", required=True, help="Dialogue / Inner monologue text")
    world_p.add_argument("--badge", default="İÇ SES // GÜNLÜK", help="Badge text on bubble")
    world_p.add_argument("--location", default="📍 BEYOĞLU // GALATA KAHVESİ", help="Location title")
    world_p.add_argument("--stats", default="👟 14.850 Adım // 9.5 km • ☀️ 21°C Altın Saat", help="Location stats")
    world_p.add_argument("--bg", default="assets/crayon_street_bg.jpg", help="Illustrated background path")
    world_p.add_argument("--duration", "-d", type=float, default=6.0, help="Duration in seconds")
    world_p.add_argument("--output", "-o", default="output/stickman_demos/crayon_capital_masterpiece.mp4", help="Output path")

    # 3. Procedural Walk Command
    walk_p = subparsers.add_parser("walk", help="Generate procedural walk cycle across screen")
    walk_p.add_argument("--text", "-t", required=True, help="Dialogue text")
    walk_p.add_argument("--badge", default="İÇ SES // YÜRÜYÜŞ GÜNLÜĞÜ", help="Badge text")
    walk_p.add_argument("--location", default="📍 İSTANBUL // GALATA SOKAKLARI", help="Location title")
    walk_p.add_argument("--stats", default="👟 14.850 Adım // 9.5 km • ☀️ 21°C", help="Location stats")
    walk_p.add_argument("--duration", "-d", type=float, default=5.0, help="Duration in seconds")
    walk_p.add_argument("--bg", help="Background image path")
    walk_p.add_argument("--greenscreen", action="store_true", help="Render on broadcast green screen")
    walk_p.add_argument("--output", "-o", default="output/stickman_demos/walk_demo.mp4", help="Output path")

    # 4. Technology & Finance Documentary Command
    tech_p = subparsers.add_parser("tech", help="Generate Crayon Capital style Tech & Finance Documentary scene")
    tech_p.add_argument("--headline", default="SILICON VALLEY VC DISASTER // CASH BURN REPORT", help="Top headline")
    tech_p.add_argument("--company", default="NEURALSCALE AI (SERIES B)", help="Company name")
    tech_p.add_argument("--valuation", default="$2.4 BILLION -> $80 MILLION (-97% COLLAPSE)", help="Valuation collapse")
    tech_p.add_argument("--founder", default="We bought 24,000 H100 GPUs... and built a chatbot that writes haikus!", help="Tech founder dialogue")
    tech_p.add_argument("--trader", default="The market cap just vaporized! Liquidate the margin calls!", help="Trader dialogue")
    tech_p.add_argument("--duration", "-d", type=float, default=6.0, help="Duration in seconds")
    tech_p.add_argument("--output", "-o", default="output/stickman_demos/crayon_tech_finance.mp4", help="Output path")

    # 5. Military Satire & Defense Contracting Command
    mil_p = subparsers.add_parser("military", help="Generate Crayon Combat style Pentagon War Room & Military Satire scene")
    mil_p.add_argument("--program", default="PROJECT OVERLORD // F-35 STEALTH FIGHTER PROGRAM", help="Program title")
    mil_p.add_argument("--budget", default="ORIGINAL: $233 BILLION -> CURRENT: $1.7 TRILLION (+630%)", help="Budget overrun")
    mil_p.add_argument("--general", default="We gave you 1.7 TRILLION dollars! Why does it crash when it gets wet?!", help="Pentagon General dialogue")
    mil_p.add_argument("--ceo", default="Relax General, for another $500 Billion, we might install windshield wipers.", help="Defense CEO dialogue")
    # 6. Dynamic Action & Pacing Command
    act_p = subparsers.add_parser("action-walk", help="Generate dynamic walking, pacing, and multi-action scenes across any environment")
    act_p.add_argument("--mode", choices=["walk_to_target", "pacing", "walk_across"], default="walk_to_target", help="Motion mode")
    act_p.add_argument("--bg", default="assets/crayon_tech_bg.jpg", help="Background illustration path")
    act_p.add_argument("--character", choices=["tech_founder", "pentagon_general", "defense_ceo", "trader", "traveler"], default="tech_founder", help="Character archetype")
    act_p.add_argument("--text", "-t", required=True, help="Dialogue quote")
    act_p.add_argument("--badge", default="KARAKTER", help="Badge text on bubble")
    act_p.add_argument("--banner", default="DYNAMIC MOTION // SCENE REENACTMENT", help="Top banner title")
    act_p.add_argument("--start-x", type=float, default=180.0, help="Starting X coordinate")
    act_p.add_argument("--target-x", type=float, default=780.0, help="Target X coordinate")
    act_p.add_argument("--duration", "-d", type=float, default=6.0, help="Duration in seconds")
    act_p.add_argument("--output", "-o", default="output/stickman_demos/action_walk_demo.mp4", help="Output path")

    # 7. Authentic Crayon Strut Command
    strut_p = subparsers.add_parser("strut", help="Generate authentic Crayon Capital 4-beat zero-slip walk cycle")
    strut_p.add_argument("--archetype", choices=["tech_founder", "wall_street_trader", "defense_ceo", "pentagon_general", "traveler"], default="tech_founder", help="Character archetype")
    strut_p.add_argument("--bg", default="assets/crayon_tech_bg.jpg", help="Background illustration path")
    strut_p.add_argument("--text", "-t", required=True, help="Dialogue text")
    strut_p.add_argument("--badge", default="KARAKTER", help="Badge text on bubble")
    strut_p.add_argument("--banner", default="CRAYON CAPITAL STYLE // SKELETAL WALK", help="Banner title")
    strut_p.add_argument("--action", choices=["walk", "burning_cash", "head_panic", "coffee", "point"], default="burning_cash", help="Stop action pose")
    strut_p.add_argument("--start-x", type=float, default=None, help="Custom start X coordinate")
    strut_p.add_argument("--target-x", type=float, default=None, help="Custom target X coordinate")
    strut_p.add_argument("--scale", type=float, default=0.82, help="Character scale relative to environment (default: 0.82)")
    strut_p.add_argument("--ground-y", type=float, default=None, help="Custom ground Y coordinate")
    strut_p.add_argument("--duration", "-d", type=float, default=6.0, help="Duration in seconds")
    strut_p.add_argument("--output", "-o", default="output/stickman_demos/crayon_strut_demo.mp4", help="Output path")

    args = parser.parse_args()

    if args.command == "aviation":
        producer = AviationSceneProducer()
        print(f"✈️ Generating BlackboxAudioo Aviation Scene ({args.scene})...")
        print(f"   • Output: {args.output}")

        if args.scene == "cockpit":
            out_p = producer.render_crayon_cockpit_scene(
                output_path=args.output,
                flight_name=args.flight,
                situation_title=args.situation,
                captain_dialogue=args.cap,
                fo_dialogue=args.fo,
                bank_angle=args.bank,
                duration_sec=args.duration,
            )
        else:
            out_p = producer.render_atc_tower_scene(
                output_path=args.output,
                facility_name=args.facility,
                atc_instruction=args.text,
                duration_sec=args.duration,
            )
        print(f"✅ Aviation scene rendered successfully: {out_p}")

    elif args.command == "crayon-world":
        engine = CrayonWorldEngine()
        sprites = {
            'contact': Image.open('assets/characters/travel/crayon_char_walk_contact.png'),
            'passing': Image.open('assets/characters/travel/crayon_char_walk_passing.png'),
            'action': Image.open('assets/characters/travel/crayon_char_coffee.png'),
        }
        print(f"🎨 Generating Crayon Capital Unified World Scene...")
        out_p = engine.render_cinematic_street_scene(
            output_path=args.output,
            bg_illustration_path=args.bg,
            character_sprites=sprites,
            dialogue=args.text,
            duration_sec=args.duration,
            badge_title=args.badge,
            location_title=args.location,
            location_stats=args.stats,
            start_x=320.0,
            pause_x=980.0,
            pause_time=3.0,
            ground_y=910.0,
            char_height=460,
        )
        print(f"✅ Crayon world scene rendered successfully: {out_p}")

    elif args.command == "walk":
        producer = CrayonSceneProducer()
        out_p = producer.render_walk_across_video(
            output_path=args.output,
            dialogue=args.text,
            duration_sec=args.duration,
            badge_title=args.badge,
            location_title=args.location,
            location_stats=args.stats,
            bg_media=args.bg,
            green_screen=args.greenscreen,
        )
        print(f"✅ Walk video rendered successfully: {out_p}")

    elif args.command == "tech":
        producer = SatireSceneProducer()
        print(f"💼 Generating Tech & Finance Documentary Scene...")
        print(f"   • Output: {args.output}")
        out_p = producer.render_tech_finance_scene(
            output_path=args.output,
            headline=args.headline,
            company_name=args.company,
            valuation_drop=args.valuation,
            founder_dialogue=args.founder,
            trader_dialogue=args.trader,
            duration_sec=args.duration,
        )
        print(f"✅ Tech Finance scene rendered successfully: {out_p}")

    elif args.command == "military":
        producer = SatireSceneProducer()
        print(f"🎖️ Generating Military Satire Scene...")
        print(f"   • Output: {args.output}")
        out_p = producer.render_military_satire_scene(
            output_path=args.output,
            program_title=args.program,
            budget_summary=args.budget,
            general_dialogue=args.general,
            ceo_dialogue=args.ceo,
            duration_sec=args.duration,
        )
        print(f"✅ Military Satire scene rendered successfully: {out_p}")

    elif args.command == "action-walk":
        engine = CrayonWorldEngine()
        print(f"🚶 Generating Dynamic Action & Walking Scene ({args.mode})...")
        print(f"   • Background: {args.bg}")
        print(f"   • Character: {args.character}")
        print(f"   • Output: {args.output}")

        # Map character to action sprite
        char_map = {
            "tech_founder": "assets/characters/defense_finance/crayon_tech_founder.png",
            "pentagon_general": "assets/characters/defense_finance/crayon_pentagon_general.png",
            "defense_ceo": "assets/characters/defense_finance/crayon_defense_ceo.png",
            "trader": "assets/characters/defense_finance/crayon_wall_street_trader.png",
            "traveler": "assets/characters/travel/crayon_char_coffee.png",
        }
        action_sprite_path = char_map.get(args.character, char_map["tech_founder"])

        sprites = {
            "contact": Image.open("assets/characters/travel/crayon_char_walk_contact.png"),
            "passing": Image.open("assets/characters/travel/crayon_char_walk_passing.png"),
            "action": Image.open(action_sprite_path),
        }

        # Select ground_y based on background
        ground_y = 950.0 if ("tech" in args.bg or "military" in args.bg) else 890.0

        out_p = engine.render_action_scene(
            output_path=args.output,
            bg_path=args.bg,
            character_sprites=sprites,
            dialogue=args.text,
            duration_sec=args.duration,
            motion_mode=args.mode,
            start_x=args.start_x,
            target_x=args.target_x,
            ground_y=ground_y,
            char_height=480,
            walk_speed=2.5,
            pause_time=2.8,
            bubble_type="comic",
            badge_text=args.badge,
            banner_title=args.banner,
        )
        print(f"✅ Dynamic action scene rendered successfully: {out_p}")

    elif args.command == "strut":
        is_mil = "military" in args.bg
        is_tech = "tech" in args.bg

        if args.ground_y is not None:
            ground_y = args.ground_y
        else:
            ground_y = 740.0 if is_mil else (820.0 if is_tech else 940.0)

        if args.scale != 0.82:
            char_scale = args.scale
        else:
            char_scale = 0.74 if is_mil else (0.76 if is_tech else 0.82)

        start_x = args.start_x if args.start_x is not None else (240.0 if (is_mil or is_tech) else 420.0)
        target_x = args.target_x if args.target_x is not None else (760.0 if is_mil else (750.0 if is_tech else 880.0))

        producer = CrayonStrutProducer(scale=char_scale)
        print(f"🚶 Generating Authentic Crayon Strut Scene ({args.archetype}, scale={char_scale}, ground_y={ground_y})...")
        print(f"   • Output: {args.output}")
        out_p = producer.render_strut_scene(
            output_path=args.output,
            bg_path=args.bg,
            dialogue=args.text,
            duration_sec=args.duration,
            archetype=args.archetype,
            start_x=start_x,
            target_x=target_x,
            ground_y=ground_y,
            action_pose=args.action,
            badge_text=args.badge,
            banner_title=args.banner,
            scale=char_scale,
        )
        print(f"✅ Crayon Strut scene rendered successfully: {out_p}")


if __name__ == "__main__":
    main()



