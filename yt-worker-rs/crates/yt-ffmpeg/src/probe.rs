use std::path::Path;
use tokio::process::Command;
use tracing::warn;

pub async fn get_media_duration<P: AsRef<Path>>(path: P) -> yt_core::Result<f64> {
    let p = path.as_ref();
    let output = Command::new("ffprobe")
        .args([
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            p.to_str().unwrap_or(""),
        ])
        .output()
        .await
        .map_err(|e| yt_core::WorkerError::Ffmpeg(format!("ffprobe çalıştırılamadı: {}", e)))?;

    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        warn!("ffprobe hatası ({}): {}", p.display(), err);
        return Err(yt_core::WorkerError::Ffmpeg(err.into()));
    }

    let out_str = String::from_utf8_lossy(&output.stdout);
    let dur: f64 = out_str.trim().parse().map_err(|e| {
        yt_core::WorkerError::Ffmpeg(format!("Süre parse edilemedi ({}): {}", out_str, e))
    })?;

    Ok(dur)
}
