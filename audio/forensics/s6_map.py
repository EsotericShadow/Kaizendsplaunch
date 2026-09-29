"""Step 6: section map, fills, candidate moments, and the repo outputs film/v5/{grid,hits,sections}.json.

Per bar (bar n spans T0 + (n-1) * 4P .. T0 + n * 4P on the grid of s4_grid.py): K-weighted loudness (BS.1770
filter, mean power over the bar, LUFS) of the master, of the fitted drums and of the non-drum part (master
minus fitted drums, s3_other.py), the guitar-to-drums ratio (non-drum minus drums, dB), drum hits per piece,
a 16th-note groove signature, and guitar onsets (peaks of the non-drum spectral flux).
Sections: the boundaries below are read off that per-bar table (the groove signature changes, the drums
stop, the loudness steps); everything reported per section is computed.
Fills: snare/tom hits on 16th positions that the section's groove does not use (used in < 34 % of its bars),
grouped when closer than one beat; a fill needs >= 3 such hits, or >= 2 plus a 16th-note run.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import common as C  # noqa: E402
import s4_grid as G  # noqa: E402
from synth import meter  # noqa: E402

SYM = {"kick": "K", "snare": "S", "racktom": "T", "floortom": "F", "hihat": "h", "crash": "C", "ride": "r"}
# (first bar, last bar, id, label, description) -- bars inclusive
SECTIONS = [
    (1, 8, "intro", "Intro: tom groove",
     "Band in on the first sample of bar 1 (crash + kick + rack tom). Kick with rack and floor toms, no snare; "
     "guitar under the drums. Bar 8 ends in a snare and tom fill."),
    (9, 14, "riff1", "Riff 1: full band, backbeat",
     "Snare on 2 and 4, crash on 1 every two bars, busy guitar riff on top of the drums."),
    (15, 22, "gtr1", "Stop, then guitar alone (long)",
     "One hit on the downbeat of bar 15 (kick, hat, crash), then the drums stop; the crash rings out and the "
     "guitar plays alone for 7 bars. The drum stems are digital silence in bars 19-21."),
    (23, 30, "toms2", "Tom groove 2",
     "The intro groove returns; bar 30 is a whole-bar snare and floor-tom fill."),
    (31, 38, "verse", "Verse: backbeat, sparser guitar",
     "Crash on the downbeat of bar 31, backbeat; guitar lighter and less busy than riff 1."),
    (39, 44, "riff2", "Riff 2: loudest, busiest guitar",
     "Same backbeat; the guitar riff is at its busiest and the master at its loudest."),
    (45, 52, "accents", "Accent section: crash pushes",
     "Crash + kick on 1, the 'and' of 2 and the 'and' of 4 in bars 45, 47, 49 and 51; snare figures in the "
     "bars between."),
    (53, 56, "gtr2", "Stop, then guitar alone",
     "Kick + snare + crash on the downbeat of bar 53, the drums stop, the guitar rings on alone."),
    (57, 66, "toms3", "Tom groove 3, guitar rising",
     "Tom groove; from bar 61 the guitar gets louder over the same groove."),
    (67, 68, "build1", "Snare and floor-tom build",
     "Two bars of snare and floor tom in 8ths into the stop."),
    (69, 72, "gtr3", "Stop, breakdown: quietest guitar alone",
     "Kick + crash on the downbeat of bar 69, then the quietest passage of the song, guitar alone."),
    (73, 76, "build2", "Build: hi-hat, then snare on every beat",
     "Hi-hat 8ths, then the snare on every beat; loudness rises bar by bar into bar 77."),
    (77, 83, "riff3", "Riff 3, with a stop-time bar",
     "Crash + kick on the downbeat of bar 77 (the drop after the build); bar 80 is a stop bar (hit on 1, "
     "silence, crash on the 'and' of 4); bar 83 is all pushes."),
    (84, 87, "gtr4", "Stop, then guitar alone",
     "Kick + snare on the downbeat of bar 84, the drums stop, guitar alone."),
    (88, 95, "drive", "Drive: snare on every beat",
     "Crash + kick + snare on the downbeat of bar 88; snare on every beat, crash every other bar."),
    (96, 103, "outro", "Outro: tom groove",
     "The tom groove once more; bar 103 is a floor-tom fill into the last crash (beat 3 of bar 103)."),
    (104, 104, "ringout", "Ring-out",
     "The last crash and the guitar decay; the file ends exactly on the end of bar 104."),
]


def bar_time(n, t0, P):
    return t0 + (n - 1) * 4 * P


def kpow(x):
    y = sosfilt(meter._k_weighting_sos(C.SR), x, axis=0)
    return (y ** 2).sum(axis=1) if y.ndim > 1 else y ** 2


def lufs(p, a, b):
    i0, i1 = int(a * C.SR), int(min(b, len(p) / C.SR) * C.SR)
    return float(-0.691 + 10 * np.log10(p[i0:i1].mean() + 1e-20)) if i1 > i0 else -120.0


def guitar_onsets(t0, t1):
    g = G.guitar_flux(int(G.SONG_END / G.FR) + 1)
    thr = np.percentile(g, 90)
    i0, i1 = int(t0 / G.FR), int(t1 / G.FR)
    s = g[i0:i1]
    return int(np.sum((s[1:-1] > thr) & (s[1:-1] >= s[:-2]) & (s[1:-1] > s[2:])))


def main():
    gr = G.main()
    t0, P = gr["t0"], gr["P"]
    hits = gr["hits"]
    raw = np.load(os.path.join(C.OUT, "work", "hits_raw.npy"), allow_pickle=True).item()["hits"]
    M = C.master()
    ND = sf.read(os.path.join(C.OUT, "stems", "nondrums.wav"), dtype="float64", always_2d=True)[0]
    pm, pn, pd = kpow(M), kpow(ND), kpow(M - ND)
    nbars = int(round((G.SONG_END - t0) / (4 * P)))
    bars = []
    for n in range(1, nbars + 1):
        a, b = bar_time(n, t0, P), bar_time(n + 1, t0, P)
        sig = [""] * 16
        cnt = {}
        for k, s in SYM.items():
            t = hits[k][:, 0]
            sel = t[(t >= a - 0.03) & (t < b - 0.03)]
            cnt[k] = int(len(sel))
            for x in sel:
                j = int(np.round((x - a) / (P / 4)))
                if 0 <= j < 16:
                    sig[j] += s
        lm, ld, lg = lufs(pm, a, b), lufs(pd, a, b), lufs(pn, a, b)
        bars.append({"bar": n, "t": round(a, 4), "lufs": round(lm, 1), "drums_lufs": round(ld, 1),
                     "nondrum_lufs": round(lg, 1), "gtr_minus_drums_db": round(min(lg - ld, 60.0), 1),
                     "hits": cnt, "groove": sig, "guitar_onsets": guitar_onsets(a, b)})
    # fills
    fills = []
    for (b0, b1, sid, label, _) in SECTIONS:
        bs = [bars[n - 1] for n in range(b0, b1 + 1) if n <= len(bars)]
        use = {c: np.zeros(16) for c in "STF"}
        for br in bs:
            for j, sy in enumerate(br["groove"]):
                for c in "STF":
                    if c in sy:
                        use[c][j] += 1
        for c in use:
            use[c] /= max(1, len(bs))
        odd = []
        for br in bs:
            for j, sy in enumerate(br["groove"]):
                oc = "".join(c for c in "STF" if c in sy and (use[c][j] < 0.34 or len(bs) <= 2))
                if oc:
                    odd.append((br["t"] + j * P / 4, oc))
        grp = []
        for t, sy in odd:
            if grp and t - grp[-1][0] > P * 1.01:
                fills.append(grp)
                grp = []
            grp.append((t, sy))
        if grp:
            fills.append(grp)
    fill_list = []
    for g in fills:
        ts = np.array([t for t, _ in g])
        run16 = np.any(np.diff(ts) < P / 4 * 1.2) if len(ts) > 1 else False
        a, b = ts.min() - 0.03, ts.max() + 0.03
        att = sorted(float(x) for k in ("snare", "racktom", "floortom") for x in hits[k][:, 0] if a <= x <= b)
        if len(ts) >= 3 or (len(ts) >= 2 and (run16 or len(att) >= 3)):
            pieces = "".join(sorted(set("".join(s for _, s in g) + "") & set("STF")))
            kind = {"S": "snare", "T": "rack tom", "F": "floor tom", "ST": "snare + toms", "FS": "snare + toms",
                    "FT": "toms", "FST": "snare + toms"}.get(pieces, pieces)
            nb = int(np.floor((ts.min() - t0) / (4 * P))) + 1
            beat = (ts.min() - bar_time(nb, t0, P)) / P + 1
            fill_list.append({"start": round(att[0], 4), "end": round(att[-1], 4), "bar": nb,
                              "beat": round(float(beat), 2), "kind": kind, "hits": len(att)})
    # sections
    secs = []
    for (b0, b1, sid, label, desc) in SECTIONS:
        a, b = bar_time(b0, t0, P), min(bar_time(b1 + 1, t0, P), G.SONG_END)
        bs = [bars[n - 1] for n in range(b0, min(b1, len(bars)) + 1)]
        ch = hits["crash"]
        big = [round(float(x), 4) for x, lv in ch if a - 0.03 <= x < b - 0.03]
        dbars = [br for br in bs if sum(v for k, v in br["hits"].items() if k != "ride") >= 3]
        share = len(dbars) / len(bs)
        drums = "in" if share >= 0.75 else ("out" if share <= 0.25 else "partly")
        if drums == "out" and bs[0]["hits"]["kick"] + bs[0]["hits"]["snare"] + bs[0]["hits"]["crash"] > 0:
            drums = "out after the downbeat hit"
        drum_hits = sum(sum(v for k, v in br["hits"].items() if k != "ride") for br in bs)
        secs.append({"id": sid, "label": label, "bars": [b0, b1], "start": round(a, 4), "end": round(b, 4),
                     "lufs": round(lufs(pm, a, b), 1), "lufs_range_per_bar": [min(x["lufs"] for x in bs),
                                                                               max(x["lufs"] for x in bs)],
                     "drums": drums, "drum_hits_per_bar": round(drum_hits / len(bs), 1),
                     "guitar_onsets_per_bar": round(float(np.mean([x["guitar_onsets"] for x in bs])), 1),
                     "gtr_minus_drums_db_median_bar": round(float(np.median([x["gtr_minus_drums_db"] for x in bs])), 1),
                     "crashes": big, "note": desc})
    cands = candidates(t0, P, bars, secs, hits, pm)
    out = dict(t0=t0, P=P, bars=bars, fills=fill_list, sections=secs, grid=gr, cands=cands)
    write_outputs(out, raw)
    np.save(os.path.join(C.OUT, "work", "map_stage.npy"), out, allow_pickle=True)
    for s in secs:
        print(f"{s['id']:8s} bars {s['bars'][0]:3d}-{s['bars'][1]:3d} {s['start']:8.3f}-{s['end']:8.3f}  "
              f"{s['lufs']:6.1f} LUFS  drums {s['drums']:26s} hits/bar {s['drum_hits_per_bar']:5.1f}  "
              f"gtr-drums {s['gtr_minus_drums_db_median_bar']:6.1f}  gOn/bar {s['guitar_onsets_per_bar']:5.1f}  crashes {len(s['crashes'])}")
    for f in fill_list:
        print("fill", f)
    return out


def at_downbeat(hits, t, w=0.03):
    return "+".join(k for k in ("crash", "kick", "snare", "racktom", "floortom")
                    if np.any(np.abs(hits[k][:, 0] - t) < w))


def candidates(t0, P, bars, secs, hits, pm):
    c = {}
    # hooks in the first 3 s: every drum attack, with the pieces sounding together
    ev = sorted((round(float(x), 4), k, float(lv)) for k in ("kick", "snare", "racktom", "floortom", "crash")
                for x, lv in hits[k] if x < 3.0)
    grp = []
    for t, k, lv in ev:
        if grp and t - grp[-1]["t"] < 0.03:
            grp[-1]["pieces"].append(k)
            continue
        nb = int(np.floor((t - t0 + 0.03) / (4 * P))) + 1
        beat = (t - bar_time(nb, t0, P)) / P + 1
        grp.append({"t": t, "bar": nb, "beat": round(float(beat), 2), "pieces": [k],
                    "lufs_400ms_after": round(lufs(pm, t, t + 0.4), 1)})
    c["first_3s_events"] = grp
    # TikTok: every bar line, 15 s continuous
    rows = []
    for br in bars:
        t = br["t"]
        if t + 15 > G.SONG_END:
            break
        first = lufs(pm, t, t + 1)
        before = lufs(pm, max(0, t - 1), t) if t > 1.0 else -70.0
        mean15 = lufs(pm, t, t + 15)
        inside = [s["id"] for s in secs if t + 1.5 < s["start"] < t + 14]
        rows.append({"bar": br["bar"], "start": round(t, 4), "end": round(t + 15, 4),
                     "first_second_lufs": round(first, 1), "contrast_vs_second_before_db": round(first - before, 1),
                     "downbeat": at_downbeat(hits, t), "lufs_15s": round(mean15, 1), "sections_starting_inside": inside})
    for r in rows:
        r["score"] = round((r["first_second_lufs"] + 20) + 0.5 * min(r["contrast_vs_second_before_db"], 20)
                           + (3 if "crash" in r["downbeat"] else 0) + 0.5 * (r["lufs_15s"] + 20)
                           + (2 if r["sections_starting_inside"] else 0), 1)
    top, used = [], []
    for r in sorted(rows, key=lambda r: -r["score"]):
        if all(abs(r["start"] - u) > 6 for u in used):
            top.append(r)
            used.append(r["start"])
        if len(top) >= 6:
            break
    c["tiktok_15s"] = sorted(top, key=lambda r: r["start"])
    c["tiktok_all_bars"] = rows
    return c


def jdump(obj):
    """JSON with one line per list item for lists of lists, compact otherwise (keeps the files readable)."""
    return json.dumps(obj, indent=1, separators=(",", ": "))


def write_outputs(out, raw):
    gr = out["grid"]
    t0, P = out["t0"], out["P"]
    os.makedirs(C.FILM_V5, exist_ok=True)
    tb = ("seconds from the first sample of the owner's master mp3 decoded gapless at 48 kHz "
          "(LAME encoder delay 576 and decoder delay 529 removed; the song = film time)")
    nb = len(out["bars"])
    beats = [round(t0 + k * P, 4) for k in range(nb * 4)]
    grid = {
        "about": "Beat grid of the owner's song (148 BPM, 4/4). Measured from the drum stems; see film/v5/AUDIO_MAP.md.",
        "time_base": tb,
        "bpm": round(gr["bpm"], 4), "bpm_standard_error": round(gr["bpm_se"], 4), "bpm_owner": 148,
        "period_s": round(P, 7), "t0": round(t0, 5), "meter": "4/4", "bars": nb,
        "formula": "beat k (k = 0, 1, 2, ...) at t0 + k * period_s; bar n (n = 1..104) starts at t0 + (n - 1) * 4 * period_s",
        "pickup": None,
        "before_bar_1": "0.000-0.405 s: no music (digital silence 0.05-0.25 s, a faint pre-roll swell at -65..-54 dBFS 0.28-0.39 s)",
        "song_end_s": G.SONG_END, "end_of_bar_104_s": round(t0 + nb * 4 * P, 4),
        "tempo": "constant: the drums sit on one fixed 148.000 BPM grid from bar 1 to bar 104, through every drum break",
        "downbeats": [round(t0 + (n - 1) * 4 * P, 4) for n in range(1, nb + 1)],
        "beats": beats,
        "tempo_curve_8s": {"columns": ["from_s", "to_s", "kick_snare_hits", "local_bpm", "phase_offset_ms"],
                           "rows": [[float(x) for x in r] for r in gr["local"]]},
        "fit": {"hits": int(gr["keep"].size), "used": int(gr["keep"].sum()),
                "residual_ms_median_abs": round(float(np.median(np.abs(gr["res"]))) * 1000, 2),
                "residual_ms_p90_abs": round(float(np.percentile(np.abs(gr["res"]), 90)) * 1000, 2)},
        "live_tempo_check": gr["dp_dev"],
        "downbeat_phase_scores": gr["phase_scores"],
        "validation": gr["tests"],
    }
    with open(os.path.join(C.FILM_V5, "grid.json"), "w") as f:
        f.write(json.dumps(grid, indent=1) + "\n")
    def arr(k, extra=None):
        v = raw[k]
        rows = []
        for h in v:
            r = [round(float(h[0]), 4), round(float(h[1]), 1)]
            if extra:
                r += extra(h)
            rows.append(r)
        return rows
    hitsj = {
        "about": "Drum hits of the owner's song, bleed removed. t = attack (s), dB = level in the piece's own band (dBFS). See film/v5/AUDIO_MAP.md.",
        "time_base": tb,
        "columns": {"kick": ["t", "dB"], "snare": ["t", "dB"], "racktom": ["t", "dB"], "floortom": ["t", "dB"],
                    "hihat": ["t", "dB", "open(1)/closed(0)"],
                    "crash": ["t", "dB", "L_minus_R_dB", "overhead_rise_s"],
                    "cymbal": ["t", "dB", "L_minus_R_dB", "overhead_rise_s"]},
        "kick": arr("kick"), "snare": arr("snare"), "racktom": arr("racktom"), "floortom": arr("floortom"),
        "hihat": arr("hihat", lambda h: [int(bool(h[3]))]),
        "crash": arr("crash", lambda h: [h[3], h[5]]),
        "cymbal": arr("ride", lambda h: [h[3], h[5]]),
        "fills": out["fills"],
        "notes": {
            "levels": "kick 40-100 Hz, snare 150-400 Hz, rack tom 90-170 Hz, floor tom 45-90 Hz (10 ms Hilbert peak); hi-hat and cymbals 6-16 kHz",
            "crash": "t is the kick/snare/tom attack the crash lands with (the crash's 6-16 kHz rise starts ~10 ms earlier, overhead_rise_s); crashes are overhead peaks that stay within 10 dB for >= 160 ms",
            "cymbal": "other cymbal hits (ride, crash-ride, short crashes): short overhead peaks with no snare, tom or hat hit within 25 ms",
            "confidence": "kick, snare, crash: high (attacks within ~1 ms of the grid). Rack tom: good. Floor tom: moderate (its mic rings and hears the kick; some weak intro hits may be resonance). Hi-hat: only clear, separate hat strokes (81); hats under snare hits are not listed",
        },
    }
    with open(os.path.join(C.FILM_V5, "hits.json"), "w") as f:
        f.write("{\n")
        keys = list(hitsj)
        for i, k in enumerate(keys):
            v = hitsj[k]
            if k in ("kick", "snare", "racktom", "floortom", "hihat", "crash", "cymbal"):
                body = json.dumps(v, separators=(",", ":"))
            else:
                body = json.dumps(v, indent=None, separators=(", ", ": "))
            f.write(f' "{k}": {body}' + (",\n" if i < len(keys) - 1 else "\n"))
        f.write("}\n")
    secj = {
        "about": "Section map of the owner's song on the 148 BPM grid (film/v5/grid.json). See film/v5/AUDIO_MAP.md.",
        "time_base": tb,
        "sections": out["sections"],
        "guitar_alone": [{"from": s["start"], "to": s["end"], "bars": s["bars"], "section": s["id"]}
                         for s in out["sections"] if s["drums"].startswith("out")],
        "bars_columns": ["bar", "t", "lufs", "drums_lufs", "nondrum_lufs", "gtr_minus_drums_db", "kick", "snare",
                         "racktom", "floortom", "hihat", "crash", "guitar_onsets", "groove_16ths"],
        "bars": [[b["bar"], b["t"], b["lufs"], b["drums_lufs"], b["nondrum_lufs"], b["gtr_minus_drums_db"],
                  b["hits"]["kick"], b["hits"]["snare"], b["hits"]["racktom"], b["hits"]["floortom"],
                  b["hits"]["hihat"], b["hits"]["crash"], b["guitar_onsets"], "|".join(x or "." for x in b["groove"])]
                 for b in out["bars"]],
        "first_3s_events": out["cands"]["first_3s_events"],
        "tiktok_15s_candidates": out["cands"]["tiktok_15s"],
    }
    with open(os.path.join(C.FILM_V5, "sections.json"), "w") as f:
        f.write("{\n")
        keys = list(secj)
        for i, k in enumerate(keys):
            v = secj[k]
            if k == "bars":
                body = "[\n" + ",\n".join("  " + json.dumps(r, separators=(",", ":")) for r in v) + "\n ]"
            elif isinstance(v, list):
                body = "[\n" + ",\n".join("  " + json.dumps(r, separators=(", ", ": ")) for r in v) + "\n ]"
            else:
                body = json.dumps(v)
            f.write(f' "{k}": {body}' + (",\n" if i < len(keys) - 1 else "\n"))
        f.write("}\n")


if __name__ == "__main__":
    main()
