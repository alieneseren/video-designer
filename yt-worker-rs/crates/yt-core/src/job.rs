use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ChannelConfig {
    #[serde(default)]
    pub channel_id: String,
    #[serde(default)]
    pub topic_category: String,
    #[serde(default)]
    pub language: String,
    #[serde(default)]
    pub target_fps: Option<u32>,
    #[serde(default)]
    pub aspect_ratio: Option<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SceneData {
    #[serde(default)]
    pub scene_index: usize,
    #[serde(default)]
    pub narration: String,
    #[serde(default)]
    pub visual_description: Option<String>,
    #[serde(default)]
    pub search_queries: Option<Vec<String>>,
    #[serde(default)]
    pub duration_sec: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ScriptData {
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub narration: Option<String>,
    #[serde(default)]
    pub text: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub tags: Option<Vec<String>>,
    #[serde(default)]
    pub language: Option<String>,
    #[serde(default)]
    pub scenes: Option<Vec<SceneData>>,
    #[serde(default)]
    pub messages: Option<Vec<serde_json::Value>>,
    #[serde(default)]
    pub question: Option<String>,
    #[serde(default)]
    pub infographic_stats: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct JobData {
    #[serde(default)]
    pub job_id: String,
    #[serde(default)]
    pub channel_id: String,
    #[serde(default)]
    pub channel_config: Option<ChannelConfig>,
    #[serde(default)]
    pub channel_type: Option<String>,
    #[serde(default)]
    pub category: Option<String>,
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub script_data: Option<ScriptData>,
    #[serde(default)]
    pub script: Option<ScriptData>,
    #[serde(default)]
    pub language: Option<String>,
    #[serde(default)]
    pub force_rebuild: Option<bool>,
    #[serde(default)]
    pub workspace_dir: Option<String>,
    #[serde(default)]
    pub output_dir: Option<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

impl JobData {
    pub fn from_file<P: AsRef<Path>>(path: P) -> crate::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let job: Self = serde_json::from_str(&content)?;
        Ok(job)
    }

    pub fn get_title(&self) -> String {
        if let Some(t) = &self.title {
            if !t.is_empty() { return t.clone(); }
        }
        if let Some(s) = &self.script_data {
            if let Some(t) = &s.title {
                if !t.is_empty() { return t.clone(); }
            }
        }
        if let Some(s) = &self.script {
            if let Some(t) = &s.title {
                if !t.is_empty() { return t.clone(); }
            }
        }
        "Untitled Shorts".to_string()
    }

    pub fn get_language(&self) -> String {
        if let Some(l) = &self.language {
            return l.to_lowercase();
        }
        if let Some(s) = &self.script_data {
            if let Some(l) = &s.language {
                return l.to_lowercase();
            }
        }
        if let Some(c) = &self.channel_config {
            if !c.language.is_empty() {
                return c.language.to_lowercase();
            }
        }
        "en".to_string()
    }

    pub fn get_topic_category(&self) -> String {
        if let Some(c) = &self.channel_config {
            if !c.topic_category.is_empty() {
                return c.topic_category.to_lowercase();
            }
        }
        if let Some(cat) = &self.category {
            return cat.to_lowercase();
        }
        "general".to_string()
    }

    pub fn is_sports(&self) -> bool {
        let cat = self.get_topic_category();
        let ch = self.channel_id.to_lowercase();
        cat.contains("sports") || cat.contains("basketball") || ch.contains("basketball")
    }
}
