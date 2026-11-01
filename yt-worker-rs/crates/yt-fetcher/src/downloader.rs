use std::path::Path;
use tracing::warn;
use yt_media_core::TimelineGuard;

pub struct AssetFetcher {
    client: reqwest::Client,
    guard: TimelineGuard,
}

impl AssetFetcher {
    pub fn new() -> Self {
        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(15))
            .user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            .build()
            .unwrap_or_default();

        Self {
            client,
            guard: TimelineGuard::default(),
        }
    }

    /// Verifies image bytes: decodes format and resolution.
    /// Rejects images < 480px width or height.
    pub fn validate_image_bytes(bytes: &[u8]) -> Option<(u32, u32)> {
        if let Ok(reader) = image::ImageReader::new(std::io::Cursor::new(bytes)).with_guessed_format() {
            if let Ok(dims) = reader.into_dimensions() {
                if dims.0 >= 480 && dims.1 >= 480 {
                    return Some(dims);
                }
            }
        }
        None
    }

    /// Downloads an image URL and saves to target path if valid and not perceptually duplicated.
    pub async fn download_and_verify<P: AsRef<Path>>(&mut self, url: &str, target_path: P) -> yt_core::Result<bool> {
        let resp = match self.client.get(url).send().await {
            Ok(r) => r,
            Err(e) => {
                warn!("İndirme hatası ({}): {}", url, e);
                return Ok(false);
            }
        };

        if !resp.status().is_success() {
            return Ok(false);
        }

        let bytes = resp.bytes().await.map_err(|e| yt_core::WorkerError::Network(e.to_string()))?;
        if Self::validate_image_bytes(&bytes).is_none() {
            return Ok(false);
        }

        let temp_path = target_path.as_ref().with_extension("tmp");
        tokio::fs::write(&temp_path, &bytes).await?;

        // Perceptual dHash check
        if self.guard.is_asset_used(&temp_path) {
            let _ = tokio::fs::remove_file(&temp_path).await;
            return Ok(false);
        }

        self.guard.mark_used(&temp_path);
        tokio::fs::rename(&temp_path, target_path).await?;
        Ok(true)
    }
}

impl Default for AssetFetcher {
    fn default() -> Self {
        Self::new()
    }
}
