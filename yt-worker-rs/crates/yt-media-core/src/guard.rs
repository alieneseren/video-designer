use std::collections::HashSet;
use std::path::{Path, PathBuf};
use tracing::{info, warn};

pub struct TimelineGuard {
    used_paths: HashSet<PathBuf>,
    used_dhashes: Vec<String>,
    max_hamming_threshold: u32,
}

impl TimelineGuard {
    pub fn new(max_hamming_threshold: u32) -> Self {
        Self {
            used_paths: HashSet::new(),
            used_dhashes: Vec::new(),
            max_hamming_threshold,
        }
    }

    pub fn reset(&mut self) {
        self.used_paths.clear();
        self.used_dhashes.clear();
        info!("🔄 [TimelineGuard] Algısal dHash ve varlık kayıt havuzu sıfırlandı.");
    }

    /// Checks if an asset or perceptually similar variant was already used in the timeline.
    pub fn is_asset_used<P: AsRef<Path>>(&self, path: P) -> bool {
        let path_ref = path.as_ref();
        if self.used_paths.contains(path_ref) {
            return true;
        }

        if let Ok(dhash) = crate::dhash::compute_dhash(path_ref) {
            for existing in &self.used_dhashes {
                let dist = crate::dhash::hamming_distance(&dhash, existing);
                if dist <= self.max_hamming_threshold {
                    warn!(
                        "🛑 [TimelineGuard] Algısal kopya tespit edildi: {} (Hamming Mesafesi: {} <= {})",
                        path_ref.display(),
                        dist,
                        self.max_hamming_threshold
                    );
                    return true;
                }
            }
        }

        false
    }

    /// Marks an asset as used, recording both path and dHash.
    pub fn mark_used<P: AsRef<Path>>(&mut self, path: P) {
        let p = path.as_ref().to_path_buf();
        if let Ok(dhash) = crate::dhash::compute_dhash(&p) {
            self.used_dhashes.push(dhash);
        }
        self.used_paths.insert(p);
    }

    pub fn used_count(&self) -> usize {
        self.used_paths.len()
    }
}

impl Default for TimelineGuard {
    fn default() -> Self {
        Self::new(10) // Strict Hamming distance <= 10 counts as perceptual duplicate
    }
}
