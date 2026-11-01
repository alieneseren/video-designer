from pathlib import Path


def sync_materials_with_generated_videos(manager, materials: list[dict]) -> None:
    """Mark matching materials and plan rows produced once a final video exists."""
    if not materials:
        return

    remote_videos = []
    queue_state = {}
    active_materials = [
        item for item in materials
        if item.get("status") not in ("produced", "downloaded")
    ]
    if active_materials:
        try:
            from remote_runner import RemoteRunner

            runner = RemoteRunner()
            remote_videos = runner.list_server_videos()
            if any(item.get("status") == "in_cloud_queue" for item in active_materials):
                queue_state = runner.get_queue_status()
        except Exception as exc:
            print(f"[MATERIAL-SYNC] Uzak video durumu okunamadı: {exc}")

    remote_by_channel: dict[str, list[dict]] = {}
    for video in remote_videos:
        remote_by_channel.setdefault(str(video.get("channel_id") or ""), []).append(video)

    pending_job_ids = {
        str(queue_state.get("current_job") or ""),
        *(str(name).removesuffix(".json") for name in queue_state.get("queue_files", [])),
    }
    from browser_uploader import find_planned_video_folder
    from channel_manager import ChannelManager
    from content_planner import ContentPlanner

    for material in materials:
        channel_id = str(material.get("channel_id") or "")
        material_id = str(material.get("material_id") or material.get("id") or "")
        row_id = str(material.get("row_id") or "")
        already_produced = material.get("status") in ("produced", "downloaded")
        is_group, clean_id, target_dir = manager._resolve_target(channel_id)

        if is_group:
            member_channels = material.get("member_channel_ids") or []
            if not member_channels:
                try:
                    group = ChannelManager().get_group(clean_id)
                    member_channels = (group or {}).get("channel_ids") or []
                except Exception as exc:
                    print(f"[MATERIAL-SYNC] Grup kanalları okunamadı ({clean_id}): {exc}")
                    member_channels = []
            expected_channels = [str(cid) for cid in member_channels]
        else:
            expected_channels = [channel_id] if channel_id else []

        if not already_produced and material.get("status") == "in_cloud_queue":
            if not is_group and f"exec_{material_id}" in pending_job_ids:
                continue
            if is_group and any(
                job_id.startswith(f"exec_mat_{clean_id}_{member}_{row_id}_")
                for job_id in pending_job_ids
                for member in expected_channels
            ):
                continue

        local_matches = set()
        if row_id and not is_group:
            try:
                if find_planned_video_folder(channel_id, row_id, output_base_dir=str(manager.output_dir)):
                    local_matches.add(channel_id)
            except Exception as exc:
                print(f"[MATERIAL-SYNC] Yerel video aranamadı ({channel_id}/{row_id}): {exc}")

        if material_id:
            for expected_channel in expected_channels:
                candidate_dirs = Path(manager.output_dir).joinpath(expected_channel, "yuklenecek")
                if not candidate_dirs.is_dir():
                    continue
                for candidate in candidate_dirs.glob(f"*{material_id}*"):
                    if candidate.is_dir() and any(
                        (candidate / filename).is_file()
                        for filename in ("final.mp4", "final_video.mp4", "video.mp4", "base.mp4")
                    ):
                        local_matches.add(expected_channel)

        remote_matches = set()
        for expected_channel in expected_channels:
            for video in remote_by_channel.get(expected_channel, []):
                exact_job = video.get("job_id") == f"exec_{material_id}"
                matching_row = bool(row_id) and str(video.get("row_id") or "") == row_id
                if exact_job or matching_row:
                    remote_matches.add(expected_channel)

        if is_group:
            produced = bool(expected_channels) and set(expected_channels).issubset(local_matches | remote_matches)
        else:
            produced = bool(expected_channels) and bool(local_matches or remote_matches)

        if not produced and not already_produced:
            continue

        if not already_produced and manager.update_material_status(channel_id, material_id, "produced"):
            material["status"] = "produced"
        if row_id:
            try:
                planner = ContentPlanner(target_dir)
                plan_row = next(
                    (row for row in planner.get_plan() if str(row.get("id", "")).strip() == row_id),
                    None,
                )
                plan_status = str((plan_row or {}).get("uretildi") or "").strip().lower()
                if plan_row and plan_status not in ("evet", "yes", "true", "1"):
                    planner.mark_as_produced(row_id)
            except Exception as exc:
                print(f"[MATERIAL-SYNC] Plan satırı üretildi olarak işaretlenemedi ({channel_id}/{row_id}): {exc}")
