"""
stickman_engine
===============
Modern 2D Stickman & Comic Animation Engine for YouTube Documentaries & Vlog Reenactments.
Supports:
- Crayon Capital / MinutePhysics / Kurzgesagt vector aesthetic.
- 2-joint IK skeletal rigging and 4-phase procedural walk cycles with true ankle roll.
- Articulated hands & arms (yoke grip, radio mic to mouth, pointing at warnings).
- BlackboxAudioo aviation documentary scenes (Cockpit CVR, ATC Tower, NTSB Investigation).
- Travel & walking vlog scenes with inner monologue thought bubbles.
- Alpha-channel ProRes 4444 and broadcast green screen MP4 overlays.
"""

from .character import StickmanCharacter, CharacterState, ProceduralStickman
from .bubble import ComicBubble, ThoughtBubble, InfoBadge
from .animator import StickmanTimeline, MotionPath, easing_elastic_out
from .overlay import StickmanOverlayCompositor
from .crayon_walker import CrayonWalker, CrayonSceneProducer, solve_2joint_ik
from .world_engine import CrayonWorldEngine
from .articulated_rig import ArticulatedRig
from .aviation_scenes import AviationSceneProducer
from .satire_scenes import SatireSceneProducer
from .crayon_strut import CrayonStrutRig, CrayonStrutProducer
from .engine import StickmanEngine

__all__ = [
    "StickmanCharacter",
    "CharacterState",
    "ProceduralStickman",
    "ComicBubble",
    "ThoughtBubble",
    "InfoBadge",
    "StickmanTimeline",
    "MotionPath",
    "easing_elastic_out",
    "StickmanOverlayCompositor",
    "CrayonWalker",
    "CrayonSceneProducer",
    "CrayonWorldEngine",
    "ArticulatedRig",
    "AviationSceneProducer",
    "SatireSceneProducer",
    "CrayonStrutRig",
    "CrayonStrutProducer",
    "solve_2joint_ik",
    "StickmanEngine",
]

