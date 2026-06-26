# Rendered Reels

Actual video files rendered from the still images in this repo.

## jordan_in_20s_v1.mp4

- **Spec:** 9:16 · 1080×1920 · 30 fps · ~20s · H.264 + AAC (~12 MB, ~5 Mbps)
- **Type:** photo-to-video cinematic montage (Reel 09 concept), built from the
  real Jordan stills already in this repo — no external footage needed.
- **Sequence:** Petra valley → Amman white hills → Roman ruins → Amman cityscape
  → Petra landscape → Petra royal tombs, bookended by a **hook card**
  ("JORDAN / in 20 seconds") and a **CTA card** ("Save this trip / Follow for
  more Jordan / @jordan.unveiled.co").
- **Treatment:** blurred-fill 9:16 framing (whole 4:5 photo stays visible),
  slow Ken Burns push on every still, 0.5s crossfades, one unified warm
  cinematic grade + vignette across all shots, soft generated ambient pad.

### Before posting

- **Swap the audio** for a trending/licensed track from the Instagram/TikTok
  in-app library — that drives reach and avoids licensing issues. The built-in
  pad is a royalty-free placeholder so the file isn't silent.
- Optionally trim/reorder stills or change the hook in `scripts/build_reel.py`.

### Rebuild

```bash
pip install imageio imageio-ffmpeg pillow numpy   # one-time
python3 scripts/build_reel.py
```

Edit `SEQ`, `SECS_PER_PHOTO`, the hook/CTA text, or the grade at the top of
`scripts/build_reel.py` to produce variants. ffmpeg is provided by the
`imageio-ffmpeg` pip package — no system install required.
