use tiny_skia::*;

/// Renders a gold-bordered glassmorphic subtitle card (1080x1920 canvas)
/// Card properties:
/// - Background: dark navy glass rgba(18, 22, 34, 0.90)
/// - Border: vibrant gold amber rgba(251, 191, 36, 1.0), stroke width 4px, radius 24px
/// - Drop shadow: soft black blur rgba(0, 0, 0, 0.47)
/// - Position: centered at y ≈ 1600px (bottom 20%)
pub fn render_gold_glass_card(width: u32, height: u32, card_w: f32, card_h: f32, center_y: f32) -> Option<Pixmap> {
    let mut pixmap = Pixmap::new(width, height)?;

    let x0 = (width as f32 - card_w) / 2.0;
    let y0 = center_y - (card_h / 2.0);

    // 1. Soft Shadow
    let mut shadow_paint = Paint::default();
    shadow_paint.set_color_rgba8(0, 0, 0, 120);
    shadow_paint.anti_alias = true;

    if let Some(shadow_rect) = Rect::from_xywh(x0, y0 + 6.0, card_w, card_h) {
        let shadow_path = PathBuilder::from_rect(shadow_rect);
        pixmap.fill_path(&shadow_path, &shadow_paint, FillRule::Winding, Transform::identity(), None);
    }

    // 2. Glass Card Background
    let mut bg_paint = Paint::default();
    bg_paint.set_color_rgba8(18, 22, 34, 230);
    bg_paint.anti_alias = true;

    if let Some(card_rect) = Rect::from_xywh(x0, y0, card_w, card_h) {
        let card_path = PathBuilder::from_rect(card_rect);
        pixmap.fill_path(&card_path, &bg_paint, FillRule::Winding, Transform::identity(), None);

        // 3. Gold Amber Outline
        let mut stroke_paint = Paint::default();
        stroke_paint.set_color_rgba8(251, 191, 36, 255);
        stroke_paint.anti_alias = true;

        let stroke = Stroke {
            width: 3.5,
            ..Default::default()
        };
        pixmap.stroke_path(&card_path, &stroke_paint, &stroke, Transform::identity(), None);
    }

    Some(pixmap)
}
