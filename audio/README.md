# audio

Original music and sound tooling for the launch video. Everything here is
synthesised from scratch; no samples, loops or licensed music.

- `synth/` Python package: instruments, sequencer, mixer, effects, metering.
- `examples/dreamy_demo.py` renders a 16-bar demo with stems and metrics.
- `tests/test_synth.py` numerical quality checks (tuning, aliasing, DC, clicks,
  reverb decay, limiter true peak, loudness meter against ffmpeg).
- `tools/inventory.py` measures the audio clips on the Kaizen DSP website.

Setup: `pip install -r audio/requirements.txt` (numba is optional but makes the
per-sample kernels about 100x faster).

Run:

```
python3 audio/tests/test_synth.py
python3 audio/examples/dreamy_demo.py --out /home/user/build/audio-demo
```

Renders go outside the repo (default `/home/user/build/`). The optional
Choroboros pass calls the local `choro-render` build through
`synth/external.py`; that binary and anything it is built from must never be
committed here.
