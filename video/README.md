# OnceSealed demo video

The ~3-minute submission video, made with [Remotion](https://www.remotion.dev/) (React → MP4).

- `narration.json`: the narration, one entry per scene (`say` overrides pronunciation; captions show `text`).
- `tts.py`: voices it with edge-tts (Microsoft neural voice `en-US-AndrewNeural`, an AI voice) and writes
  `public/audio/` and `src/narration.generated.json` (scene durations and caption timings).
- `public/shots/`: screenshots of the running demo, captured at 2x with
  `python scripts/gallery.py --scale 2 --out video/public/shots`.
- `src/scenes.tsx`: one view per scene; camera moves and highlight boxes are in screenshot coordinates.

```bash
pip install edge-tts && python tts.py      # only when the narration changes
npm install
npm run studio                             # preview
npm run render                             # out/oncesealed.mp4
```

Every figure in the video comes from the repository's measurements (see the README's "What we measured").
