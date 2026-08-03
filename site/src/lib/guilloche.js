// Guilloché generator (hypotrochoid interference) — the site's recurring
// engraved-rosette motif. Shared by the hero background and the small
// footer mark so both stay visually identical.
export function guilloche(canvas, opts) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const rect = canvas.getBoundingClientRect();
  const w = (canvas.width = rect.width * dpr), h = (canvas.height = rect.height * dpr);
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, w, h);
  const lw = (opts.lw || 0.6) * dpr;
  const cx = w / 2, cy = h / 2;
  const scale = (Math.min(w, h) / 2) * (opts.scale || 0.86);
  opts.layers.forEach((L) => {
    // Draw each layer fully opaque on an offscreen canvas first, then
    // composite once at the intended alpha — see hero script for why
    // (self-overlapping strokes render inconsistently across browsers
    // otherwise).
    const off = document.createElement('canvas');
    off.width = w; off.height = h;
    const octx = off.getContext('2d');
    octx.lineWidth = lw; octx.strokeStyle = L.color;
    octx.beginPath();
    const { R, r, d, turns = 60 } = L, step = 0.02;
    for (let t = 0; t <= Math.PI * 2 * turns; t += step) {
      const k = (R - r) / r;
      const x = (R - r) * Math.cos(t) + d * Math.cos(k * t);
      const y = (R - r) * Math.sin(t) - d * Math.sin(k * t);
      const px = cx + x * scale, py = cy + y * scale;
      t === 0 ? octx.moveTo(px, py) : octx.lineTo(px, py);
    }
    octx.stroke();
    ctx.globalAlpha = L.alpha ?? 0.5;
    ctx.drawImage(off, 0, 0);
  });
  ctx.globalAlpha = 1;
}

// Redraws on every real size change of the canvas (not just window resize)
// and once webfonts finish swapping in — fixes a Safari bug where the very
// first draw happens before the font swap resizes the layout, leaving a
// stale, stretched bitmap.
export function watchAndDraw(canvas, draw) {
  let raf;
  const scheduleDraw = () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(draw);
  };
  new ResizeObserver(scheduleDraw).observe(canvas);
  document.fonts?.ready?.then(scheduleDraw);
}
