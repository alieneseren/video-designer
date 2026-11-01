use image::imageops::FilterType;
use image::DynamicImage;
use std::path::Path;

/// Calculates 64-bit difference hash (dHash) from image path.
/// 1. Converts to grayscale.
/// 2. Resizes to 9x8 pixels.
/// 3. Compares adjacent pixels horizontally: P[x+1, y] > P[x, y].
/// 4. Generates a 16-character hexadecimal string.
pub fn compute_dhash<P: AsRef<Path>>(path: P) -> yt_core::Result<String> {
    let img = image::open(path).map_err(|e| yt_core::WorkerError::Media(format!("Görsel açılamadı: {}", e)))?;
    Ok(compute_dhash_from_image(&img))
}

pub fn compute_dhash_from_image(img: &DynamicImage) -> String {
    let gray = img.to_luma8();
    let resized = image::imageops::resize(&gray, 9, 8, FilterType::Triangle);

    let mut hash_val: u64 = 0;
    for y in 0..8 {
        for x in 0..8 {
            let left = resized.get_pixel(x, y)[0];
            let right = resized.get_pixel(x + 1, y)[0];
            if right > left {
                hash_val |= 1 << (y * 8 + x);
            }
        }
    }

    format!("{:016x}", hash_val)
}

/// Calculates Hamming distance between two 16-char hex dHash strings.
/// Uses native hardware instruction (POPCNT) via `count_ones()` for 1-nanosecond execution.
pub fn hamming_distance(h1: &str, h2: &str) -> u32 {
    let v1 = u64::from_str_radix(h1.trim(), 16).unwrap_or(0);
    let v2 = u64::from_str_radix(h2.trim(), 16).unwrap_or(0);
    (v1 ^ v2).count_ones()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_identical_hashes() {
        let h1 = "0123456789abcdef";
        let h2 = "0123456789abcdef";
        assert_eq!(hamming_distance(h1, h2), 0);
    }

    #[test]
    fn test_one_bit_difference() {
        let h1 = "0000000000000000";
        let h2 = "0000000000000001";
        assert_eq!(hamming_distance(h1, h2), 1);
    }
}
