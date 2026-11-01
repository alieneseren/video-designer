use yt_core::PanZoomType;

/// Builds an FFmpeg video filter for Ken Burns effect with strict 9:16 aspect ratio.
/// Always enforces: `scale=1242:2208:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2`
pub fn build_ken_burns_filter(pz: PanZoomType, duration_sec: f64, fps: u32) -> String {
    let frames = (duration_sec * fps as f64).round() as u64;

    match pz {
        PanZoomType::ZoomIn => {
            format!(
                "scale=1242:2208:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,\
                 zoompan=z='min(zoom+0.0015,1.25)':d={}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={}",
                frames, fps
            )
        }
        PanZoomType::ZoomOut => {
            format!(
                "scale=1242:2208:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,\
                 zoompan=z='if(lte(zoom,1.0),1.25,max(1.0,zoom-0.0015))':d={}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={}",
                frames, fps
            )
        }
        PanZoomType::PanLeftToRight => {
            format!(
                "scale=1242:2208:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,\
                 zoompan=z=1.15:x='(on/{})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':d={}:s=1080x1920:fps={}",
                frames, frames, fps
            )
        }
        PanZoomType::PanRightToLeft => {
            format!(
                "scale=1242:2208:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,\
                 zoompan=z=1.15:x='(1-on/{})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':d={}:s=1080x1920:fps={}",
                frames, frames, fps
            )
        }
        PanZoomType::StaticCenter => {
            "scale=1242:2208:force_original_aspect_ratio=increase,crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2".to_string()
        }
    }
}
