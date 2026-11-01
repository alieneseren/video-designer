"""
story_manager.py
================
Hikaye & Masal kanalları için hikaye taslaklarını (Story Drafts) yönetir.
Kullanıcı taslaklarını kaydeder, Gemini ile geliştirilen senaryoları saklar,
hikayeyi bölümlere (Part 1, Part 2...) ayırır ve sistemin Üretim Materyallerine
(material.json) dönüştürür.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
STORIES_FILE = CONFIG_DIR / "story_drafts.json"


class StoryManager:
    def __init__(self, stories_path: Optional[Path] = None):
        self.stories_file = stories_path or STORIES_FILE
        self.stories_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.stories_file.exists():
            self._save_raw([])

    def _load_raw(self) -> List[Dict[str, Any]]:
        try:
            if self.stories_file.exists():
                with open(self.stories_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[STORY-MGR] ⚠️ Taslaklar yüklenirken hata: {e}")
        return []

    def _save_raw(self, stories: List[Dict[str, Any]]) -> None:
        try:
            with open(self.stories_file, "w", encoding="utf-8") as f:
                json.dump(stories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[STORY-MGR] ⚠️ Taslaklar kaydedilirken hata: {e}")

    def list_stories(self, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tüm taslakları veya belirli bir kanalın taslaklarını döndürür."""
        stories = self._load_raw()
        if channel_id:
            cid = str(channel_id).strip()
            return [s for s in stories if s.get("channel_id") == cid]
        return stories

    def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """Belirtilen ID'ye sahip hikaye taslağını bulur."""
        stories = self._load_raw()
        for s in stories:
            if s.get("id") == story_id:
                return s
        return None

    def create_story(
        self,
        channel_id: str,
        title: str,
        raw_text: str,
        target_language: str = "tr",
        genre: str = "sci_fi_mystery",
        plot_notes: str = "",
        developed_story: Optional[Dict[str, Any]] = None,
        author: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Yeni bir hikaye taslağı oluşturur."""
        stories = self._load_raw()
        now = datetime.now().isoformat()
        story_id = f"story_{uuid.uuid4().hex[:8]}"

        item = {
            "id": story_id,
            "channel_id": channel_id,
            "title": title.strip() or "İsimsiz Hikaye",
            "raw_text": raw_text.strip(),
            "target_language": target_language or "tr",
            "genre": genre or "sci_fi_mystery",
            "plot_notes": plot_notes.strip(),
            "status": "developed" if developed_story else "draft",
            "author": author or "Antigravity Storyteller",
            "developed_story": developed_story or None,
            "created_at": now,
            "updated_at": now,
        }
        stories.insert(0, item)
        self._save_raw(stories)
        print(f"[STORY-MGR] ✨ Yeni hikaye taslağı kaydedildi: '{item['title']}' ({story_id})")
        return item

    def update_story(self, story_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mevcut bir hikaye taslağını günceller."""
        stories = self._load_raw()
        target = None
        for s in stories:
            if s.get("id") == story_id:
                target = s
                break
        if not target:
            return None

        # İzin verilen alanları güncelle
        allowed = [
            "title", "raw_text", "target_language", "genre", "plot_notes",
            "status", "developed_story", "author", "converted_materials"
        ]
        for key in allowed:
            if key in updates:
                target[key] = updates[key]

        target["updated_at"] = datetime.now().isoformat()
        self._save_raw(stories)
        print(f"[STORY-MGR] 📝 Hikaye taslağı güncellendi: '{target['title']}' ({story_id})")
        return target

    def delete_story(self, story_id: str) -> bool:
        """Hikaye taslağını siler."""
        stories = self._load_raw()
        initial_len = len(stories)
        stories = [s for s in stories if s.get("id") != story_id]
        if len(stories) < initial_len:
            self._save_raw(stories)
            print(f"[STORY-MGR] 🗑️ Hikaye taslağı silindi: {story_id}")
            return True
        return False

    def convert_to_materials(self, story_id: str) -> Dict[str, Any]:
        """
        Geliştirilen hikayeyi (veya ham taslağı) multi-part Shorts formatında
        sistemin Üretim Materyalleri (MaterialsManager) paketlerine dönüştürür.
        """
        story = self.get_story(story_id)
        if not story:
            raise ValueError(f"Hikaye bulunamadı: {story_id}")

        from materials_manager import MaterialsManager
        mgr = MaterialsManager()
        ch_id = story.get("channel_id")
        lang = story.get("target_language", "tr")
        developed = story.get("developed_story") or {}

        parts = developed.get("parts")
        if not parts or not isinstance(parts, list):
            # Eğer parçalara bölünmemişse tek parça olarak derle
            parts = [
                {
                    "part_number": 1,
                    "part_title": story.get("title", "Hikaye"),
                    "scenes": developed.get("scenes") or [
                        {
                            "scene_num": 1,
                            "narration": story.get("raw_text", ""),
                            "caption": story.get("title", ""),
                            "image_prompt": "Cinematic sci-fi space atmosphere, starry void, vector art, 9:16 vertical ratio",
                            "camera_effect": "zoom_in",
                            "duration_sec": 45,
                        }
                    ],
                    "hook": developed.get("hook", story.get("title", "")),
                    "cliffhanger": developed.get("cliffhanger", "Devamı için takipte kalın!"),
                }
            ]

        total_parts = len(parts)
        saved_materials = []

        for p_idx, part in enumerate(parts, 1):
            p_num = part.get("part_number", p_idx)
            p_title = part.get("part_title") or f"{story.get('title')} - Part {p_num}"
            scenes = part.get("scenes", [])
            hook = part.get("hook") or story.get("title")
            cliffhanger = part.get("cliffhanger") or (
                f"Part {p_num + 1} yakında! Takipte kalın..." if p_num < total_parts else "Hikayenin sonu. Takip ettiğiniz için teşekkürler!"
            )

            # Standardize scene structures
            formatted_scenes = []
            for s_i, sc in enumerate(scenes, 1):
                formatted_scenes.append({
                    "scene_num": sc.get("scene_num", s_i),
                    "narration": sc.get("narration", ""),
                    "caption": sc.get("caption") or sc.get("narration", "")[:60],
                    "image_prompt": sc.get("image_prompt") or sc.get("prompt") or "Cinematic procedural space art, glowing stars, 9:16 vertical",
                    "camera_effect": sc.get("camera_effect", "zoom_in"),
                    "highlight_words": sc.get("highlight_words", []),
                    "emotion": sc.get("emotion", "dramatic"),
                    "duration_sec": sc.get("duration_sec", 8),
                })

            script_payload = {
                "title": f"{story.get('title')} // PART {p_num}",
                "description": f"{hook}\n\n{story.get('title')} serisi Bölüm {p_num}/{total_parts}.\n\n#Shorts #Hikaye #Animasyon #Aurora #SciFi",
                "tags": ["Shorts", "Hikaye", "Animasyon", "SciFi", "Storytime", f"Part{p_num}"],
                "keywords": ["hikaye", "animasyon", "shorts", "part"],
                "style_prompt": "Procedural cinematic atmospheric vector space animation, aurora glow, glowing spacecraft, starry void",
                "scenes": formatted_scenes,
                "metadata": {
                    "is_story_series": True,
                    "series_id": story_id,
                    "series_title": story.get("title"),
                    "part_number": p_num,
                    "total_parts": total_parts,
                    "hook": hook,
                    "cliffhanger": cliffhanger,
                    "render_mode": "procedural_story_animation",
                    "target_language": lang,
                }
            }

            saved = mgr.save_material(
                channel_id=ch_id,
                script=script_payload,
                title=f"{story.get('title')} - Part {p_num}",
                topic=f"{story.get('title')} (Bölüm {p_num}/{total_parts})",
                notes=f"Hikaye Taslağından ({story_id}) türetildi. Hook: {hook}"
            )
            saved_materials.append(saved)

        # Taslağı 'converted' olarak işaretle
        self.update_story(story_id, {
            "status": "converted",
            "converted_materials": [m.get("id") for m in saved_materials]
        })

        return {
            "success": True,
            "story_id": story_id,
            "total_parts": total_parts,
            "materials": saved_materials
        }
