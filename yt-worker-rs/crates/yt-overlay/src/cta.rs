use tiny_skia::*;

/// Renders the universal YouTube Social CTA Badge (Subscribe + Like + Bell)
/// Position: Exactly at lower quarter `cy ≈ int(h * 0.74)` (e.g. y = 1420 px on 1080x1920)
/// Dimensions: 460px width, 72px height, 36px pill border radius.
pub fn render_cta_badge(width: u32, height: u32, center_y: f32) -> Option<Pixmap> {
    let mut pixmap = Pixmap::new(width, height)?;

    let badge_w = 460.0;
    let badge_h = 72.0;
    let x0 = (width as f32 - badge_w) / 2.0;
    let y0 = center_y - (badge_h / 2.0);

    // 1. Badge Pill Background (Dark semi-transparent charcoal)
    let mut bg_paint = Paint::default();
    bg_paint.set_color_rgba8(28, 31, 38, 235);
    bg_paint.anti_alias = true;

    if let Some(rect) = Rect::from_xywh(x0, y0, badge_w, badge_h) {
        let path = PathBuilder::from_rect(rect);
        pixmap.fill_path(&path, &bg_paint, FillRule::Winding, Transform::identity(), None);

        // Subtle border
        let mut stroke_paint = Paint::default();
        stroke_paint.set_color_rgba8(255, 255, 255, 40);
        let stroke = Stroke { width: 1.5, ..Default::default() };
        pixmap.stroke_path(&path, &stroke_paint, &stroke, Transform::identity(), None);
    }

    // 2. Red YouTube Play Icon Box
    let mut red_paint = Paint::default();
    red_paint.set_color_rgba8(235, 32, 32, 255);
    red_paint.anti_alias = true;

    if let Some(yt_rect) = Rect::from_xywh(x0 + 20.0, y0 + 18.0, 48.0, 36.0) {
        let yt_path = PathBuilder::from_rect(yt_rect);
        pixmap.fill_path(&yt_path, &red_paint, FillRule::Winding, Transform::identity(), None);

        // White Play Triangle
        let mut tri_builder = PathBuilder::new();
        tri_builder.move_to(x0 + 38.0, y0 + 27.0);
        tri_builder.line_to(x0 + 52.0, y0 + 36.0);
        tri_builder.line_to(x0 + 38.0, y0 + 45.0);
        tri_builder.close();

        if let Some(tri_path) = tri_builder.finish() {
            let mut white_paint = Paint::default();
            white_paint.set_color_rgba8(255, 255, 255, 255);
            pixmap.fill_path(&tri_path, &white_paint, FillRule::Winding, Transform::identity(), None);
        }
    }

    // 3. Dividers
    let mut div_paint = Paint::default();
    div_paint.set_color_rgba8(255, 255, 255, 50);
    let div_stroke = Stroke { width: 1.5, ..Default::default() };

    let mut div1 = PathBuilder::new();
    div1.move_to(x0 + 280.0, y0 + 16.0);
    div1.line_to(x0 + 280.0, y0 + 56.0);
    if let Some(p) = div1.finish() {
        pixmap.stroke_path(&p, &div_paint, &div_stroke, Transform::identity(), None);
    }

    let mut div2 = PathBuilder::new();
    div2.move_to(x0 + 365.0, y0 + 16.0);
    div2.line_to(x0 + 365.0, y0 + 56.0);
    if let Some(p) = div2.finish() {
        pixmap.stroke_path(&p, &div_paint, &div_stroke, Transform::identity(), None);
    }

    Some(pixmap)
}
