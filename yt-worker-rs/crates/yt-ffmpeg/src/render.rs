use std::path::Path;
use tokio::process::Command;
use tracing::warn;
use yt_core::PanZoomType;

pub struct FfmpegRenderer {
    fps: u32,
}

impl FfmpegRenderer {
    pub fn new(fps: u32) -> Self {
        Self { fps }
    }

    /// Renders a single image into a Ken Burns cut video clip.
    pub async fn render_image_cut<P1: AsRef<Path>, P2: AsRef<Path>>(
        &self,
        image_path: P1,
        output_path: P2,
        duration_sec: f64,
        pz: PanZoomType,
    ) -> yt_core::Result<()> {
        let vf = crate::filtergraph::build_ken_burns_filter(pz, duration_sec, self.fps);

        let status = Command::new("ffmpeg")
            .args([
                "-y",
                "-loop", "1",
                "-i", image_path.as_ref().to_str().unwrap_or(""),
                "-t", &format!("{:.3}", duration_sec),
                "-vf", &vf,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "veryfast",
                "-r", &self.fps.to_string(),
                output_path.as_ref().to_str().unwrap_or(""),
            ])
            .output()
            .await
            .map_err(|e| yt_core::WorkerError::Ffmpeg(e.to_string()))?;

        if !status.status.success() {
            let err = String::from_utf8_lossy(&status.stderr);
            warn!("FFmpeg cut render hatası: {}", err);
            return Err(yt_core::WorkerError::Ffmpeg(err.into()));
        }

        Ok(())
    }

    /// Concatenates cuts using concat demuxer.
    pub async fn concat_cuts<P1: AsRef<Path>, P2: AsRef<Path>>(
        &self,
        concat_txt: P1,
        output_path: P2,
    ) -> yt_core::Result<()> {
        let status = Command::new("ffmpeg")
            .args([
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_txt.as_ref().to_str().unwrap_or(""),
                "-c", "copy",
                output_path.as_ref().to_str().unwrap_or(""),
            ])
            .output()
            .await
            .map_err(|e| yt_core::WorkerError::Ffmpeg(e.to_string()))?;

        if !status.status.success() {
            let err = String::from_utf8_lossy(&status.stderr);
            return Err(yt_core::WorkerError::Ffmpeg(err.into()));
        }

        Ok(())
    }

    /// Muxes final audio (voiceover + bgm) and video into master video.
    pub async fn finalize_video<P1: AsRef<Path>, P2: AsRef<Path>, P3: AsRef<Path>>(
        &self,
        visual_path: P1,
        audio_path: P2,
        output_path: P3,
        duration_sec: f64,
    ) -> yt_core::Result<()> {
        let status = Command::new("ffmpeg")
            .args([
                "-y",
                "-i", visual_path.as_ref().to_str().unwrap_or(""),
                "-i", audio_path.as_ref().to_str().unwrap_or(""),
                "-t", &format!("{:.3}", duration_sec),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                "-shortest",
                output_path.as_ref().to_str().unwrap_or(""),
            ])
            .output()
            .await
            .map_err(|e| yt_core::WorkerError::Ffmpeg(e.to_string()))?;

        if !status.status.success() {
            let err = String::from_utf8_lossy(&status.stderr);
            return Err(yt_core::WorkerError::Ffmpeg(err.into()));
        }

        Ok(())
    }
}
