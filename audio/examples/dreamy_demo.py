#!/usr/bin/env python3
"""16-bar dreamy synth-pop demo (104 BPM, G major) built entirely from the synth
package: clean guitar arpeggio, FM electric piano, Juno-style pad, pluck bass,
drums and transition FX, mixed with sends, bus compression and a true-peak-safe
limiter.

Outputs (default /home/user/build/audio-demo/):
  raw_<part>.wav          dry instrument renders (mono DI guitar, stereo pad ...)
  dry/stem_*.wav          post-fader mix stems, return_*.wav, mix.wav, mix_info.json
  choroboros/...          the same mix with Choroboros on guitar and pad (only when
                          the local choro-render build exists, see docs/brief/dsp-renderer.md)
  metrics.json, *.png     loudness, true peak, octave bands, crest factor, spectrograms

Usage: python3 audio/examples/dreamy_demo.py [--out DIR] [--lufs -16] [--no-choroboros]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from synth import (GM, Bass, Clap, EPiano, Guitar, HiHat, Humanize, JunoPad, Kick, Mixer, Note,  # noqa: E402
                   Reverb, Rim, Snare, Song, StereoDelay, arpeggio, db_to_amp, drum_grid, duck, fx, io, meter, viz)
from synth.external import choro_available, choroboros  # noqa: E402

BPM, BARS = 104, 16
OPEN = (40, 45, 50, 55, 59, 64)

# Guitar voicings as (string, fret), low to high. F#4 rings on top of every chord.
GTR = {
    "Gmaj9": [(0, 3), (2, 0), (3, 2), (4, 0), (5, 2)],             # G2 D3 A3 B3 F#4
    "Em9": [(0, 0), (1, 2), (2, 0), (3, 0), (4, 3), (5, 2)],       # E2 B2 D3 G3 D4 F#4
    "Cmaj7#11": [(1, 3), (2, 2), (3, 0), (4, 0), (5, 2)],          # C3 E3 G3 B3 F#4
    "D/A": [(1, 0), (2, 0), (3, 2), (4, 3), (5, 2)],               # A2 D3 A3 D4 F#4
}
PROG = ["Gmaj9", "Em9", "Cmaj7#11", "D/A"]
PAD = {"Gmaj9": [55, 59, 62, 66], "Em9": [52, 55, 59, 66], "Cmaj7#11": [52, 55, 59, 66], "D/A": [54, 57, 62, 66]}
EP = {"Gmaj9": [59, 62, 66, 69], "Em9": [55, 59, 62, 66], "Cmaj7#11": [59, 64, 66, 67], "D/A": [54, 57, 62, 64]}
BASS = {"Gmaj9": 43, "Em9": 40, "Cmaj7#11": 36, "D/A": 38}
ARP_SHAPE = [0.0, 0.5, 1.0, 0.75, 0.25, 0.75, 1.0, 0.5]   # position in the voicing, per 8th note


def compose(song: Song):
    parts = {k: [] for k in ("guitar", "pad", "ep", "bass", "kick", "snare", "clap", "hats", "rim")}
    for bar in range(BARS):
        ch = PROG[bar % 4]
        b0 = song.beats(bar)
        sec = "intro" if bar < 4 else ("main1" if bar < 8 else ("main2" if bar < 12 else "outro"))
        last_bar = bar == BARS - 1

        # guitar: let-ring 8th-note arpeggio (strings choke themselves when replayed)
        voicing = GTR[ch]
        if last_bar:   # final strum, left to ring
            for k, (s, f) in enumerate(voicing):
                parts["guitar"].append(Note(b0 + k * 0.06, 9.0, OPEN[s] + f, 0.62 - 0.03 * k, {"string": s, "fret": f}))
        else:
            base_v = {"intro": 0.55, "main1": 0.62, "main2": 0.7, "outro": 0.5}[sec]
            for i, pos in enumerate(ARP_SHAPE):
                s, f = voicing[int(round(pos * (len(voicing) - 1)))]
                v = base_v + (0.1 if i in (0, 4) else 0.0)
                parts["guitar"].append(Note(b0 + i * 0.5, 4.5 - i * 0.5, OPEN[s] + f, v, {"string": s, "fret": f}))

        # pad: whole-bar chords, slightly overlapping
        pv = {"intro": 0.55 + 0.1 * bar, "main1": 0.8, "main2": 0.85, "outro": 0.7}[sec]
        dur = 7.5 if last_bar else 4.2
        parts["pad"] += [Note(b0, dur, p, pv, {"centre": 60}) for p in PAD[ch]]

        # electric piano: syncopated comping in the main sections, soft whole notes at the end
        if sec in ("main1", "main2"):
            for off, d, v in ((0.0, 1.4, 0.62), (1.5, 0.9, 0.5), (3.0, 0.9, 0.55)):
                parts["ep"] += [Note(b0 + off, d, p, v) for p in EP[ch]]
            if sec == "main2" and bar % 2 == 1:   # a little answering figure on top
                parts["ep"] += [Note(b0 + 3.5, 0.5, 74, 0.5), Note(b0 + 3.75, 0.6, 71, 0.45)]
        elif sec == "outro":
            parts["ep"] += [Note(b0, 3.8 if not last_bar else 7.0, p, 0.45) for p in EP[ch]]

        # bass: pulsing 8ths in the main sections, long notes in the outro
        root = BASS[ch]
        if sec in ("main1", "main2"):
            for i in range(8):
                v = 0.85 if i in (0, 4) else 0.62
                p = root + (12 if (sec == "main2" and i == 7) else 0)
                parts["bass"].append(Note(b0 + i * 0.5, 0.42, p, v))
        elif sec == "outro" and bar < BARS - 1:
            parts["bass"].append(Note(b0, 3.6, root, 0.6))

        # drums
        if sec in ("main1", "main2"):
            parts["kick"] += drum_grid("X.....x.X....." + ("x." if sec == "main2" else ".."), GM["kick"], b0)
            parts["snare"] += drum_grid("....X.......X...", GM["snare"], b0)
            parts["clap"] += drum_grid("....X.......X...", GM["clap"], b0)
            hats = "o.x.o.x.o.x.o.x." if sec == "main1" else "gxgxgxgxgxgxgxgx"
            parts["hats"] += drum_grid(hats, GM["closed_hat"], b0)
            if sec == "main2" and bar % 2 == 1:
                parts["hats"].append(Note(b0 + 3.5, 0.5, GM["open_hat"], 0.7))
            if bar in (7, 11):  # fill into the next section
                parts["snare"] += drum_grid("............gox", GM["snare"], b0, accents={"g": 0.35, "o": 0.5, "x": 0.7})
        elif sec == "intro" and bar >= 2:
            parts["rim"] += drum_grid("............x...", 37, b0)
            parts["hats"] += drum_grid("..o...o...o...o.", GM["closed_hat"], b0, accents={"o": 0.4})
        elif sec == "outro" and bar < 14:
            parts["hats"] += drum_grid("..o...o...o...o.", GM["closed_hat"], b0, accents={"o": 0.35})
            if bar == 12:
                parts["kick"].append(Note(b0, 1, GM["kick"], 0.9))
    return parts


def render_parts(song: Song):
    hum = lambda seed, ms=6.0, vel=0.07: Humanize(timing_ms=ms, velocity=vel, seed=seed)
    notes = compose(song)
    raw = {
        "guitar_di": song.render(Guitar(tone="di", seed=1), notes["guitar"], hum(1, 7.0), stereo=False),
        "pad": song.render(JunoPad(seed=3), notes["pad"], hum(3, 4.0, 0.03)),
        "ep": song.render(EPiano(seed=2), notes["ep"], hum(2, 5.0, 0.06), stereo=False),
        "bass": song.render(Bass(seed=4), notes["bass"], hum(4, 3.0, 0.05), stereo=False),
        "kick": song.render(Kick(seed=10, f_end=49.0), notes["kick"], hum(10, 1.5, 0.03), stereo=False),  # tuned to G1
        "snare": song.render(Snare(seed=11), notes["snare"], hum(11, 3.0, 0.05), stereo=False),
        "clap": song.render(Clap(seed=12), notes["clap"], Humanize(timing_ms=2.0, velocity=0.05, push_ms=4.0, seed=12),
                            stereo=False),
        "hats": song.render(HiHat(seed=13), notes["hats"],
                            Humanize(timing_ms=4.0, velocity=0.12, swing=0.12, grid=0.25, seed=13), stereo=False),
        "rim": song.render(Rim(seed=14), notes["rim"], hum(14, 3.0, 0.05), stereo=False),
    }
    # transition FX, placed so risers and the reverse cymbal land on the downbeat
    n = song.length
    fxs = np.zeros((n, 2))
    rl = song.seconds(8)
    fxs += song.place(fx.riser(rl, seed=20), song.beats(4) - 8)
    fxs += song.place(fx.reverse_cymbal(song.seconds(4), seed=24), song.beats(4) - 4)
    fxs += song.place(fx.reverse_cymbal(song.seconds(4), seed=25, level=0.22), song.beats(8) - 4)
    raw["fx_risers"] = fxs
    hits = song.place(fx.impact(3.5, seed=22), song.beats(4))
    hits += song.place(fx.downlifter(song.seconds(6), seed=21), song.beats(12))
    raw["fx_hits"] = hits
    return raw


def build_mix(song: Song, raw: dict, guitar=None, pad=None, target_lufs=-16.0):
    m = Mixer()
    plate = Reverb(rt60=2.6, hf_ratio=0.45, size=1.1, predelay_ms=28, low_cut=220, high_cut=7000, width=1.1)
    room = Reverb(rt60=0.75, hf_ratio=0.5, size=0.45, predelay_ms=4, low_cut=300, high_cut=9000, diffusion=0.7)
    delay = StereoDelay.synced(BPM, 0.75, 1.0, feedback=0.32, cross=0.6, lp_hz=4200, hp_hz=350)
    m.bus("plate", plate, gain_db=0.0).bus("room", room, gain_db=0.0).bus("delay", delay, gain_db=0.0)
    kick = raw["kick"]
    g = guitar if guitar is not None else raw["guitar_di"]
    p = pad if pad is not None else raw["pad"]
    m.track("kick", kick, gain_db=-6.0, eq=[("peak", 55, -1.5, 1.2)], sends={"room": -20})
    m.track("snare", raw["snare"], gain_db=-5.0, eq=[("peak", 190, 1.5, 1.2)], sends={"room": -9, "plate": -15})
    m.track("clap", raw["clap"], gain_db=-5.0, pan=0.0, sends={"plate": -11})
    m.track("hats", raw["hats"], gain_db=-5.0, pan=0.22, eq=[("highshelf", 10000, -3.0, 0.7)], sends={"room": -18})
    m.track("rim", raw["rim"], gain_db=-7.0, pan=-0.25, sends={"plate": -10})
    m.track("bass", raw["bass"], gain_db=-2.0, eq=[("highpass", 35, 0, 0.7), ("peak", 120, 1.5, 1.0)],
            inserts=[lambda x: duck(x, kick, 3.0, 3, 150)])
    m.track("pad", p, gain_db=-2.0, width=1.1, eq=[("highpass", 140, 0, 0.7), ("peak", 350, -2.0, 0.9)],
            sends={"plate": -9}, inserts=[lambda x: duck(x, kick, 2.0, 5, 220)])
    m.track("ep", raw["ep"], gain_db=-7.0, pan=-0.18, eq=[("highpass", 120, 0, 0.7)], sends={"plate": -12, "delay": -17})
    m.track("guitar", g, gain_db=-4.0, pan=0.12 if g.ndim == 1 else 0.0,
            eq=[("highpass", 110, 0, 0.7), ("peak", 3200, 1.0, 1.0)], sends={"delay": -13, "plate": -11})
    m.track("fx_risers", raw["fx_risers"], gain_db=-9.0, sends={"plate": -12})
    m.track("fx_hits", raw["fx_hits"], gain_db=-6.0, sends={"plate": -14})
    comp = dict(threshold_db=-20.0, ratio=2.0, attack_ms=25.0, release_ms=180.0, knee_db=6.0, sidechain_hp=90.0)
    return m.render(master_comp=comp, target_lufs=target_lufs, ceiling_dbtp=-1.0)


def summarize(x, sr=48000):
    r = meter.report(x, sr)
    keep = ("duration_s", "integrated_lufs", "loudness_range_lu", "max_short_term_lufs", "true_peak_dbtp",
            "sample_peak_dbfs", "plr_db", "crest", "dc_offset", "clipped_runs", "octave_bands_db_rel",
            "spectral_tilt_db_per_oct_125_8k", "spectral_centroid_hz", "stereo", "tempo", "key")
    return {k: r[k] for k in keep}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/home/user/build/audio-demo")
    ap.add_argument("--lufs", type=float, default=-16.0)
    ap.add_argument("--no-choroboros", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    song = Song(bpm=BPM, bars=BARS, tail_s=3.5)
    raw = render_parts(song)
    t_parts = time.time() - t0
    for k, v in raw.items():
        io.write_wav(os.path.join(a.out, f"raw_{k}.wav"), v)

    metrics = {"song": {"bpm": BPM, "bars": BARS, "key": "G major", "duration_s": round(song.length / song.sr, 3),
                        "progression": PROG}, "render_seconds": {"parts": round(t_parts, 2)}}
    t1 = time.time()
    dry = build_mix(song, raw, target_lufs=a.lufs)
    metrics["render_seconds"]["mix"] = round(time.time() - t1, 2)
    dry.export(os.path.join(a.out, "dry"))
    metrics["dry_mix"] = summarize(dry.master)
    metrics["dry_mix"]["bus_comp_max_gr_db"] = dry.info.get("bus_comp_max_gr_db")
    metrics["dry_mix"]["bus_comp_mean_gr_db"] = dry.info.get("bus_comp_mean_gr_db")
    metrics["dry_mix"]["limiter"] = dry.info.get("limiter")
    metrics["dry_mix"]["master_gain_db"] = dry.info.get("master_gain_db")
    metrics["stems"] = {k: {"lufs": round(meter.integrated_lufs(v), 2), "true_peak_dbtp": round(meter.true_peak(v), 2),
                            "crest_db": round(meter.crest_factor_db(v)["sample_peak_to_rms_db"], 2),
                            "dc": float(f"{np.abs(v.mean(axis=0)).max():.1e}")}
                        for k, v in {**dry.stems, **{"return_" + r: w for r, w in dry.returns.items()}}.items()}
    marks = [(song.seconds(song.beats(b)), lab) for b, lab in ((0, "intro"), (4, "main"), (8, "main 2"), (12, "outro"))]
    viz.spectrogram_png(dry.master, os.path.join(a.out, "mix_dry_spectrogram.png"), title="dreamy demo, dry mix",
                        markers=marks)
    viz.bar_chart_png({(f"{int(k)}" if float(k) >= 1000 else k): v for k, v in
                       metrics["dry_mix"]["octave_bands_db_rel"].items()},
                      os.path.join(a.out, "mix_dry_octave_bands.png"), title="Octave bands, dB relative to total")
    for k in ("guitar", "pad", "ep", "bass", "kick", "hats"):
        viz.spectrogram_png(dry.stems[k], os.path.join(a.out, f"stem_{k}_spectrogram.png"), title=f"stem: {k}",
                            width=1200, height=360, markers=marks)
    io.encode_preview(os.path.join(a.out, "dry", "mix.wav"), os.path.join(a.out, "mix_dry_preview.m4a"))

    # Same arrangement with Choroboros on the guitar DI (Green, NQ) and the pad (Black, HQ Ensemble),
    # using the demo settings from docs/brief/product.md section 7.2, loudness-matched to the dry stems.
    if not a.no_choroboros and choro_available():
        t2 = time.time()
        gi = choroboros("green", hq=False, rate=0.60, depth=20, offset=90, width=130, color=35, mix=45)
        gi.mono_input = True
        pi = choroboros("black", hq=True, rate=0.50, depth=30, offset=120, width=170, color=60, mix=55)
        g_wet = gi(raw["guitar_di"])
        p_wet = pi(raw["pad"])
        match = {}
        for name, wet, dry_src in (("guitar", g_wet, raw["guitar_di"]), ("pad", p_wet, raw["pad"])):
            gdb = meter.integrated_lufs(dry_src) - meter.integrated_lufs(wet)
            match[name] = round(gdb, 2)
        g_wet = g_wet * db_to_amp(match["guitar"])
        p_wet = p_wet * db_to_amp(match["pad"])
        io.write_wav(os.path.join(a.out, "raw_guitar_choroboros_green.wav"), g_wet)
        io.write_wav(os.path.join(a.out, "raw_pad_choroboros_black.wav"), p_wet)
        wet = build_mix(song, raw, guitar=g_wet, pad=p_wet, target_lufs=a.lufs)
        wet.export(os.path.join(a.out, "choroboros"))
        metrics["choroboros_mix"] = summarize(wet.master)
        metrics["choroboros_mix"]["loudness_match_gain_db"] = match
        metrics["choroboros_mix"]["settings"] = {
            "guitar": "Green NQ (Lagrange 3rd), Rate 0.60 Hz, Depth 20%, Offset 90, Width 130%, Color 35%, Mix 45%",
            "pad": "Black HQ (Ensemble), Rate 0.50 Hz, Depth 30%, Offset 120, Width 170%, Color 60%, Mix 55%"}
        metrics["choroboros_stem_width"] = {
            "guitar_dry": meter._round(meter.stereo_stats(raw["guitar_di"])),
            "guitar_choroboros": meter._round(meter.stereo_stats(g_wet)),
            "pad_dry": meter._round(meter.stereo_stats(raw["pad"])),
            "pad_choroboros": meter._round(meter.stereo_stats(p_wet))}
        metrics["render_seconds"]["choroboros"] = round(time.time() - t2, 2)
        viz.spectrogram_png(wet.master, os.path.join(a.out, "mix_choroboros_spectrogram.png"),
                            title="dreamy demo, Choroboros on guitar and pad", markers=marks)
        viz.spectrogram_png(wet.stems["guitar"], os.path.join(a.out, "stem_guitar_choroboros_spectrogram.png"),
                            title="stem: guitar through Choroboros Green", width=1200, height=360, markers=marks)
        io.encode_preview(os.path.join(a.out, "choroboros", "mix.wav"), os.path.join(a.out, "mix_choroboros_preview.m4a"))
    metrics["render_seconds"]["total"] = round(time.time() - t0, 2)
    with open(os.path.join(a.out, "metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=1, default=float)
    d = metrics["dry_mix"]
    print(f"dry mix: {d['integrated_lufs']} LUFS, TP {d['true_peak_dbtp']} dBTP, LRA {d['loudness_range_lu']} LU, "
          f"PLR {d['plr_db']} dB, crest {d['crest']}, corr {d['stereo']['correlation']}")
    print("octave bands:", d["octave_bands_db_rel"])
    if "choroboros_mix" in metrics:
        c = metrics["choroboros_mix"]
        print(f"choroboros mix: {c['integrated_lufs']} LUFS, TP {c['true_peak_dbtp']} dBTP, corr {c['stereo']['correlation']}")
    print("render seconds:", metrics["render_seconds"])


if __name__ == "__main__":
    main()
