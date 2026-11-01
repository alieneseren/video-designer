use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PanZoomType {
    ZoomIn,
    ZoomOut,
    PanLeftToRight,
    PanRightToLeft,
    StaticCenter,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimelineCut {
    pub index: usize,
    pub start_sec: f64,
    pub duration_sec: f64,
    pub asset_path: PathBuf,
    pub dhash: String,
    pub pan_zoom_type: PanZoomType,
    pub is_infographic: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubtitleCard {
    pub index: usize,
    pub text: String,
    pub start_sec: f64,
    pub end_sec: f64,
    pub highlight_words: Vec<String>,
}
