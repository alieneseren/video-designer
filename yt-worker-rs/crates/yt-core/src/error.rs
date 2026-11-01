use thiserror::Error;

pub type Result<T> = std::result::Result<T, WorkerError>;

#[derive(Error, Debug)]
pub enum WorkerError {
    #[error("I/O Hatası: {0}")]
    Io(#[from] std::io::Error),

    #[error("JSON Serileştirme Hatası: {0}")]
    Json(#[from] serde_json::Error),

    #[error("İş Emri Hatası: {0}")]
    JobConfig(String),

    #[error("Medya Çözümleme Hatası: {0}")]
    Media(String),

    #[error("FFmpeg Komut Hatası: {0}")]
    Ffmpeg(String),

    #[error("Görsel Doğrulama Hatası: {0}")]
    Validation(String),

    #[error("Ağ / İndirme Hatası: {0}")]
    Network(String),

    #[error("Bilinmeyen Hata: {0}")]
    Other(String),
}
