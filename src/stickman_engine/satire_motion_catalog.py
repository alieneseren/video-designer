"""
satire_motion_catalog.py
========================
Semantic Action & Motion Catalog for Tactical Crayon & Satirical Stickman Animations.
Defines SMPL 22-joint skeletal topology, bone connectivity, archetype roles,
and natural language diffusion prompts for NVIDIA ARDY (nv-tlabs/ardy).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


# SMPL 22-Joint Humanoid Topology
SMPL_22_JOINTS: Dict[str, int] = {
    "pelvis": 0,
    "left_hip": 1,
    "right_hip": 2,
    "spine1": 3,
    "left_knee": 4,
    "right_knee": 5,
    "spine2": 6,
    "left_ankle": 7,
    "right_ankle": 8,
    "spine3": 9,
    "left_foot": 10,
    "right_foot": 11,
    "neck": 12,
    "left_collar": 13,
    "right_collar": 14,
    "head": 15,
    "left_shoulder": 16,
    "right_shoulder": 17,
    "left_elbow": 18,
    "right_elbow": 19,
    "left_wrist": 20,
    "right_wrist": 21,
}

JOINT_NAMES = [
    "pelvis", "left_hip", "right_hip", "spine1", "left_knee", "right_knee",
    "spine2", "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot",
    "neck", "left_collar", "right_collar", "head", "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow", "left_wrist", "right_wrist"
]

# Skeletal Bone Connectivity Pairs (Parent, Child)
SKELETAL_BONES: List[Tuple[int, int]] = [
    # Torso & Head
    (0, 3),   # pelvis -> spine1
    (3, 6),   # spine1 -> spine2
    (6, 9),   # spine2 -> spine3
    (9, 12),  # spine3 -> neck
    (12, 15), # neck -> head
    # Left Arm
    (9, 13),  # spine3 -> left_collar
    (13, 16), # left_collar -> left_shoulder
    (16, 18), # left_shoulder -> left_elbow
    (18, 20), # left_elbow -> left_wrist
    # Right Arm
    (9, 14),  # spine3 -> right_collar
    (14, 17), # right_collar -> right_shoulder
    (17, 19), # right_shoulder -> right_elbow
    (19, 21), # right_elbow -> right_wrist
    # Left Leg
    (0, 1),   # pelvis -> left_hip
    (1, 4),   # left_hip -> left_knee
    (4, 7),   # left_knee -> left_ankle
    (7, 10),  # left_ankle -> left_foot
    # Right Leg
    (0, 2),   # pelvis -> right_hip
    (2, 5),   # right_hip -> right_knee
    (5, 8),   # right_knee -> right_ankle
    (8, 11),  # right_ankle -> right_foot
]


@dataclass
class SatireMotionDef:
    """Definition of a satirical kinetic motion beat."""
    motion_id: str
    prompt: str
    archetype: str
    emotion: str
    default_duration: float
    props: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


# Core Satirical Motion Registry
SATIRE_MOTIONS: Dict[str, SatireMotionDef] = {
    "war_room_slam": SatireMotionDef(
        motion_id="war_room_slam",
        prompt="A military general standing aggressively, slamming both fists onto a conference table and leaning forward with intense fury",
        archetype="general",
        emotion="angry",
        default_duration=3.5,
        props=["general_cap", "medals", "war_map"],
        tags=["pentagon", "military", "slam", "furious", "angry", "budget", "crash"]
    ),
    "contractor_shrug": SatireMotionDef(
        motion_id="contractor_shrug",
        prompt="A defense contractor executive leaning back comfortably, crossing legs, shrugging with open palms, and tilting head smugly",
        archetype="defense_ceo",
        emotion="smug",
        default_duration=3.2,
        props=["necktie", "coffee_cup"],
        tags=["ceo", "contractor", "shrug", "billion", "dollars", "profit", "lobbyist"]
    ),
    "bureaucrat_panic": SatireMotionDef(
        motion_id="bureaucrat_panic",
        prompt="A frantic government auditor pacing back and forth erratically, clutching head with both hands, shaking in distress, and dropping a stack of papers",
        archetype="auditor",
        emotion="panic",
        default_duration=3.0,
        props=["glasses", "dropped_papers", "briefcase"],
        tags=["auditor", "panic", "audit", "pentagon_fails", "lost", "trillion", "deficit"]
    ),
    "podium_propaganda": SatireMotionDef(
        motion_id="podium_propaganda",
        prompt="A government spokesperson gesturing grandly with index finger, pumping fist into the air, and leaning dynamically over a press briefing podium",
        archetype="spokesperson",
        emotion="pompous",
        default_duration=3.0,
        props=["podium", "microphones"],
        tags=["briefing", "press", "announcement", "propaganda", "statement", "whitehouse"]
    ),
    "soldier_duck_cover": SatireMotionDef(
        motion_id="soldier_duck_cover",
        prompt="A combat infantry soldier suddenly ducking low, covering tactical helmet with arms, cowering comically, then cautiously peeking upward",
        archetype="soldier",
        emotion="shocked",
        default_duration=2.8,
        props=["combat_helmet", "rifle"],
        tags=["soldier", "duck", "explosion", "missile", "drone", "combat", "failure"]
    ),
    "wall_street_toast": SatireMotionDef(
        motion_id="wall_street_toast",
        prompt="A wealthy corporate lobbyist laughing boisterously, raising a glass high in a celebratory toast, and slapping their knee with joy",
        archetype="lobbyist",
        emotion="greedy_laugh",
        default_duration=3.0,
        props=["champagne_glass", "gold_watch"],
        tags=["bank", "stock", "contract", "subsidy", "toast", "celebration", "cash"]
    ),
    "facepalm_disbelief": SatireMotionDef(
        motion_id="facepalm_disbelief",
        prompt="A person shaking head slowly in utter disbelief, placing hand firmly over face in a slow dramatic facepalm, then sighing heavily",
        archetype="general",
        emotion="defeated",
        default_duration=3.0,
        props=["general_cap"],
        tags=["facepalm", "disbelief", "ridiculous", "waste", "scandal", "incompetence"]
    ),
    "proud_strut": SatireMotionDef(
        motion_id="proud_strut",
        prompt="A pompous figure walking with exaggerated high-stepping strut, chest puffed out, chin held high, swinging arms theatrically",
        archetype="defense_ceo",
        emotion="arrogant",
        default_duration=3.2,
        props=["necktie", "cigar"],
        tags=["strut", "walk", "arrogant", "success", "monopoly", "overcharge"]
    )
}


def resolve_satire_motion(
    script_text: str = "",
    scene_type: str = "",
    character_role: str = ""
) -> SatireMotionDef:
    """
    Analyzes script narration and scene context to resolve the optimal
    satirical kinetic motion beat for ARDY diffusion.
    """
    text_lower = f"{script_text} {scene_type} {character_role}".lower()

    # Priority keyword scoring
    scores: Dict[str, int] = {}
    for m_id, m_def in SATIRE_MOTIONS.items():
        score = 0
        for tag in m_def.tags:
            if tag in text_lower:
                score += 2
        if m_def.archetype in text_lower:
            score += 3
        scores[m_id] = score

    best_match = max(scores, key=scores.get)
    if scores[best_match] > 0:
        return SATIRE_MOTIONS[best_match]

    # Archetype fallbacks
    if "general" in text_lower or "military" in text_lower:
        return SATIRE_MOTIONS["war_room_slam"]
    if "ceo" in text_lower or "contractor" in text_lower or "money" in text_lower:
        return SATIRE_MOTIONS["contractor_shrug"]
    if "panic" in text_lower or "fail" in text_lower or "loss" in text_lower:
        return SATIRE_MOTIONS["bureaucrat_panic"]

    return SATIRE_MOTIONS["war_room_slam"]
