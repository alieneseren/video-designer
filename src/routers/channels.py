"""
Channels and Channel Groups router.
"""
from fastapi import APIRouter, HTTPException
from channel_manager import ChannelManager
from models.channel import ChannelSchema, ToggleSchema, SocialSchema, GroupSchema

router = APIRouter(tags=["Channels"])


@router.get("/api/channels")
def get_channels():
    return ChannelManager().all_channels()


@router.post("/api/channels")
def add_channel(channel: ChannelSchema):
    try:
        return ChannelManager().add_channel(
            channel_id=channel.channel_id,
            name=channel.name,
            language=channel.language,
            topic_category=channel.topic_category,
            custom_topics=channel.custom_topics,
            schedule_hour=channel.schedule_hour,
            active=channel.active,
            shorts_mode=channel.shorts_mode,
            transition=channel.transition,
            edit_options=channel.edit_options,
            instagram=bool(channel.instagram),
            instagram_username=channel.instagram_username,
            instagram_user_id=channel.instagram_user_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api/channels/{channel_id}/toggle")
def toggle_channel(channel_id: str, payload: ToggleSchema):
    mgr = ChannelManager()
    if not mgr.get_channel(channel_id):
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    mgr.set_active(channel_id, payload.active)
    return {"success": True, "active": payload.active}


@router.put("/api/channels/{channel_id}/social")
def toggle_channel_social(channel_id: str, payload: SocialSchema):
    mgr = ChannelManager()
    channel = mgr.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    
    if payload.instagram is not None:
        channel["instagram"] = payload.instagram
    if payload.instagram_username is not None:
        channel["instagram_username"] = payload.instagram_username.strip().lstrip("@")
    if payload.tiktok is not None:
        channel["tiktok"] = payload.tiktok
        
    mgr._save()
    return {
        "success": True,
        "channel_id": channel_id,
        "instagram": channel.get("instagram", False),
        "instagram_username": channel.get("instagram_username", ""),
        "instagram_user_id": channel.get("instagram_user_id", ""),
        "tiktok": channel.get("tiktok", False)
    }


@router.put("/api/channels/{channel_id}")
def update_channel(channel_id: str, channel: ChannelSchema):
    mgr = ChannelManager()
    existing = mgr.get_channel(channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    return mgr.add_channel(
        channel_id=channel.channel_id,
        name=channel.name,
        language=channel.language,
        topic_category=channel.topic_category,
        custom_topics=channel.custom_topics,
        schedule_hour=channel.schedule_hour,
        active=channel.active,
        shorts_mode=channel.shorts_mode,
        transition=channel.transition,
        edit_options=channel.edit_options,
        instagram=channel.instagram if channel.instagram is not None else existing.get("instagram", False),
        instagram_username=channel.instagram_username,
        instagram_user_id=channel.instagram_user_id,
    )


@router.delete("/api/channels/{channel_id}")
def delete_channel(channel_id: str):
    mgr = ChannelManager()
    if not mgr.get_channel(channel_id):
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    mgr.remove_channel(channel_id)
    return {"success": True}


@router.get("/api/groups")
def get_groups():
    mgr = ChannelManager()
    groups = mgr.all_groups()
    res = []
    for g in groups:
        member_channels = []
        for cid in g.get("channel_ids", []):
            ch = mgr.get_channel(cid)
            if ch:
                member_channels.append({
                    "channel_id": ch["channel_id"],
                    "name": ch["name"],
                    "language": ch["language"],
                    "topic_category": ch["topic_category"],
                    "active": ch.get("active", True),
                })
        res.append({
            **g,
            "channels": member_channels,
            "languages": list({ch["language"] for ch in member_channels}),
        })
    return res


@router.post("/api/groups")
def create_group(payload: GroupSchema):
    mgr = ChannelManager()
    try:
        group = mgr.add_group(
            name=payload.name,
            topic_category=payload.topic_category,
            channel_ids=payload.channel_ids,
            reddit_avatar_path=payload.reddit_avatar_path,
            reddit_username=payload.reddit_username,
        )
        return {"success": True, "group": group}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api/groups/{group_id}")
def update_group(group_id: str, payload: GroupSchema):
    mgr = ChannelManager()
    try:
        group = mgr.update_group(
            group_id=group_id,
            name=payload.name,
            channel_ids=payload.channel_ids,
            reddit_avatar_path=payload.reddit_avatar_path,
            reddit_username=payload.reddit_username,
        )
        return {"success": True, "group": group}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/groups/{group_id}")
def delete_group(group_id: str):
    mgr = ChannelManager()
    mgr.delete_group(group_id)
    return {"success": True}


@router.get("/api/channels-and-groups")
def get_channels_and_groups():
    """
    Eklenti ve Dashboard için birleşik liste.
    Gruplara dahil olan münferit kanallar gizlenir, sadece Gruplar ve Bağımsız Kanallar listelenir.
    Kanal ve grupların içerik planı ve kalan üretilmemiş konu sayıları da eklenir.
    """
    from pathlib import Path
    from content_planner import ContentPlanner
    from settings_manager import SettingsManager

    settings_mgr = SettingsManager()
    output_dir = settings_mgr.get("output_dir", "output")
    mgr = ChannelManager()
    all_chans = mgr.all_channels()
    groups = mgr.all_groups()
    grouped_ids = mgr.get_grouped_channel_ids()

    items = []
    # 1. Grupları ekle
    for g in groups:
        member_channels = [mgr.get_channel(cid) for cid in g.get("channel_ids", []) if mgr.get_channel(cid)]
        langs = [ch["language"] for ch in member_channels]
        lang_str = "/".join(langs).upper() if langs else ""
        grp_dir = Path(output_dir) / "groups" / g["id"]
        grp_rows = []
        try:
            grp_planner = ContentPlanner(grp_dir)
            grp_rows = grp_planner.get_plan()
        except Exception:
            pass
        grp_unproduced = sum(1 for r in grp_rows if r.get("uretildi") != "Evet")
        has_plan = len(grp_rows) > 0

        items.append({
            "type": "group",
            "id": g["id"],
            "group_id": g["id"],
            "name": f"👥 [Grup] {g['name']} ({lang_str})",
            "raw_name": g["name"],
            "topic_category": g["topic_category"],
            "channel_ids": g.get("channel_ids", []),
            "languages": langs,
            "shorts_mode": any(ch.get("shorts_mode", False) for ch in member_channels) if member_channels else True,
            "has_plan": has_plan,
            "unproduced_count": grp_unproduced,
            "total_plan_count": len(grp_rows),
        })

    # 2. Yalnızca bağımsız (gruba dahil olmayan) kanalları ekle
    for ch in all_chans:
        if ch["channel_id"] not in grouped_ids:
            ch_dir = Path(output_dir) / ch["channel_id"]
            ch_rows = []
            try:
                ch_planner = ContentPlanner(ch_dir)
                ch_rows = ch_planner.get_plan()
            except Exception:
                pass
            ch_unproduced = sum(1 for r in ch_rows if r.get("uretildi") != "Evet")
            has_plan = len(ch_rows) > 0

            items.append({
                "type": "channel",
                "id": ch["channel_id"],
                "channel_id": ch["channel_id"],
                "name": f"{ch['name']} ({ch.get('language', 'en').upper()})",
                "raw_name": ch["name"],
                "topic_category": ch.get("topic_category", "space"),
                "channel_ids": [ch["channel_id"]],
                "languages": [ch.get("language", "en")],
                "shorts_mode": ch.get("shorts_mode", False),
                "has_plan": has_plan,
                "unproduced_count": ch_unproduced,
                "total_plan_count": len(ch_rows),
            })

    return items
