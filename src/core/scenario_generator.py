"""
core/scenario_generator.py
===========================
LLM Scenario Generator & Concrete Visual Query Schema Gate (Deterministic Gate 5)
Enforces that every scene's `visual_query` describes concrete physical reality:
- Physical camera framing (e.g., 'close up', 'wide angle shot', 'macro tracking shot', 'low angle')
- Concrete subject action (e.g., 'basketball sneakers stopping', 'explosive crossover step back dribble')
- Physical environment (e.g., 'on polished NBA hardwood floor', 'under bright arena lighting')
Rejects abstract concepts (e.g., 'eccentric quad braking', 'neurobiological superiority').
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("ScenarioGenerator")

# Abstract conceptual terms forbidden in concrete visual queries
ABSTRACT_TERMS_BLACKLIST = [
    "eccentric quad braking",
    "eccentric braking",
    "quad braking",
    "braking mechanics",
    "the power of deceleration",
    "power of deceleration",
    "deceleration concept",
    "kinetic force dissipation",
    "kinetic dissipation",
    "force dissipation",
    "kinetic force",
    "neurobiological superiority",
    "neural dominance",
    "neurobiological dominance",
    "tactical superiority",
    "psychological mind games",
    "mind games",
    "psychological pressure",
    "defensive pressure",
    "abstract biomechanics",
    "the concept of",
    "representing",
    "symbolizing",
    "metaphorical",
    "conceptual idea"
]

# Required physical dimensions for concrete visual queries
CAMERA_FRAMING_TERMS = [
    "close up", "extreme close up", "macro", "wide angle", "wide shot",
    "low angle", "high angle", "overhead", "tracking shot", "slow motion",
    "side view", "front view", "tight shot", "broadcast replay", "full speed"
]

ENVIRONMENT_TERMS = [
    "hardwood", "court", "floor", "arena", "stadium", "laboratory",
    "stands", "bench", "rim", "hoop", "backboard", "net", "locker room",
    "tunnel", "mocap", "3d wireframe", "shot clock", "led clock", "clock", "scoreboard", "led"
]


def validate_concrete_visual_query(query: str) -> Tuple[bool, str]:
    """
    Kural 5 Deterministik Doğrulayıcı:
    visual_query soyut kavramları (örn: 'eccentric quad braking') içeriyorsa reddeder.
    Fiziksel kamera açısı + sporcu eylemi + somut çevre tanımlanmasını doğrular.
    """
    if not query or len(query.strip()) < 10:
        return False, "🚨 [Visual Query Reddi] Sorgu boş veya çok kısa (< 10 karakter)!"

    q_lower = query.lower()

    # 1. Yasaklı soyut kavram kontrolü
    for bad in ABSTRACT_TERMS_BLACKLIST:
        if bad in q_lower:
            return False, f"🚨 [Soyut Kavram Reddi] '{bad}' soyut bir kavramdır! Kamera açısı + somut eylem + çevre tanımlanmalıdır."

    # 2. Somut fiziksel kamera açısı kontrolü
    has_framing = any(f in q_lower for f in CAMERA_FRAMING_TERMS)
    # 3. Somut ortam/çevre kontrolü
    has_environment = any(e in q_lower for e in ENVIRONMENT_TERMS)

    if not has_framing and not has_environment:
        return False, "🚨 [Yetersiz Somutluk] visual_query fiziksel kamera kadrajı (close up, wide angle...) veya somut ortam (hardwood, court, arena...) içermelidir!"

    return True, "OK"


CONCRETE_VISUAL_QUERY_SYSTEM_PROMPT = """
CRITICAL VISUAL QUERY GUIDELINES (DETERMINISTIC MECHANICAL RULE 5):
Every scene's "visual_query" field MUST strictly describe physical camera framing + subject action + physical environment.
NEVER output abstract medical, biomechanical, or conceptual jargon.

CORRECT CONCRETE EXAMPLES:
- "close up basketball sneakers stopping on NBA hardwood floor slow motion" (NOT "eccentric quad braking")
- "James Harden explosive crossover step back dribble shaking defender in NBA arena" (NOT "kinetic deceleration mechanics")
- "3D animation of brain synaptic firing and neurological impulses travelling down nerve" (NOT "neurobiological supremacy")
- "vintage red digital 7-segment LED shot clock displaying 0.3 seconds" (NOT "the urgency of time")
- "macro close up eye iris dilating and visual cortex optical nerve connection" (NOT "optic perception speed")

FORBIDDEN ABSTRACT PHRASES:
- "eccentric quad braking"
- "the power of deceleration"
- "neurobiological dominance"
- "kinetic force dissipation"
- "psychological mind games"
"""

SCENARIO_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "topic": {"type": "string"},
        "athlete_name": {"type": "string"},
        "hook_summary": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene_index": {"type": "integer"},
                    "narration": {"type": "string"},
                    "duration_sec": {"type": "number", "maximum": 2.40},
                    "media_type": {"type": "string", "enum": ["video", "image"]},
                    "visual_query": {
                        "type": "string",
                        "description": "Concrete physical camera framing + subject action + environment (e.g. 'close up basketball sneakers stopping on NBA hardwood floor slow motion')"
                    },
                    "camera_framing": {"type": "string"},
                    "environment": {"type": "string"},
                    "locked": {"type": "boolean", "default": True}
                },
                "required": ["scene_index", "narration", "visual_query", "media_type"]
            }
        }
    },
    "required": ["title", "athlete_name", "scenes"]
}


@dataclass
class ScenarioScene:
    scene_index: int
    narration: str
    visual_query: str
    media_type: str = "video"
    duration_sec: float = 2.10
    camera_framing: str = "wide angle"
    environment: str = "NBA hardwood court"
    locked: bool = True

    def validate(self) -> Tuple[bool, str]:
        valid, reason = validate_concrete_visual_query(self.visual_query)
        if not valid:
            return False, f"Scene {self.scene_index}: {reason}"
        if self.duration_sec > 2.45:
            return False, f"Scene {self.scene_index}: duration_sec {self.duration_sec:.2f}s > 2.40s cap!"
        return True, "OK"


class ScenarioGenerator:
    """LLM Senaryo ve Sahne Şema Üreticisi."""

    @staticmethod
    def get_prompt_instructions() -> str:
        return CONCRETE_VISUAL_QUERY_SYSTEM_PROMPT

    @staticmethod
    def get_json_schema() -> Dict[str, Any]:
        return SCENARIO_JSON_SCHEMA

    @staticmethod
    def validate_scene_data(scene_data: Dict[str, Any]) -> Tuple[bool, str]:
        vq = scene_data.get("visual_query") or scene_data.get("concrete_visual_query", "")
        return validate_concrete_visual_query(vq)
