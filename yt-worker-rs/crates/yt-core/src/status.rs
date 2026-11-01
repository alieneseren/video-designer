use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JobStatus {
    pub job_id: String,
    pub status: String,
    pub progress: u8,
    pub message: String,
    pub updated_at: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub video_path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub extra: Option<serde_json::Value>,
}

impl JobStatus {
    pub fn new(job_id: impl Into<String>, status: impl Into<String>, progress: u8, message: impl Into<String>) -> Self {
        Self {
            job_id: job_id.into(),
            status: status.into(),
            progress,
            message: message.into(),
            updated_at: Utc::now().to_rfc3339(),
            video_path: None,
            error: None,
            extra: None,
        }
    }

    pub fn save_to_file<P: AsRef<Path>>(&self, path: P) -> crate::Result<()> {
        let content = serde_json::to_string_pretty(self)?;
        std::fs::write(path, content)?;
        Ok(())
    }
}
