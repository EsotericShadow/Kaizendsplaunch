"""Step 5: per-drum hit map in master time, with bleed removed, cymbals from the overheads, and fills.

Inputs: the aligned drum stems (/home/user/build/v5/stems, written by s2_align.py). No stem is gated, and
every close mic hears the rest of the kit, so a hit is only accepted when its own mic is louder than the bleed
the other mics predict. Everything below was calibrated on scatter plots of one mic against another at
every onset in the song (the bleed and the real hits form separate clusters); the thresholds sit in the
gaps between those clusters.

Envelopes (1 ms hop): LF = Hilbert magnitude of the drum's fundamental band smoothed over 10 ms (kick
40-100 Hz, snare 150-400 Hz, rack tom 90-170 Hz, floor tom 45-90 Hz; measured pitches: kick ~65 Hz, floor
tom ~55-70 Hz, rack tom ~105-130 Hz with a downward glide, snare ~285 Hz). HF = Hilbert magnitude of the
stick/beater attack band smoothed over 1 ms (kick 1.5-6 kHz, snare and toms 2-8 kHz, hi-hat and overheads
6-16 kHz). Onset "delta" = power added by the event: peak in [-2, +12] ms minus the median of [-25, -3] ms.

Candidates: in each mic, local maxima of the 3 ms HF rise above 6 dB (>= 30 ms apart).
Rules (dB):
  kick      kick LF delta > -29 and kick HF - LF > -26 (beater click; floor-tom bleed has none)
  snare     snare LF delta > -28 and snare HF - LF > -22 (kick/tom bleed in the snare mic has no crack)
  rack tom  rack LF delta > -24 and 4 dB above max(kick LF - 15, snare LF - 10) (their bleed in the rack mic)
  floor tom floor LF delta > -34 and 6 dB above max(kick LF, rack LF - 17)
  hi-hat    hat HF delta > -46 and 6 dB above the snare/tom crack the hat mic hears at that moment
            (open if the hat mic stays within 12 dB of its peak 60-140 ms later)
  cymbal    overhead (L+R, 6-16 kHz) level 80-300 ms after the onset > -47 dBFS, 5 dB above the 10-60 ms
            before it, and at least 2 dB above the hat mic's own sustain (hat mic - 15 dB); "crash" when the
            sustained rise is >= 9 dB or the sustained level >= -36 dBFS, otherwise "ride/wash".
Times: the attack, i.e. the first sample in [-6, +15] ms where the own-mic HF envelope (full rate, 0.5 ms
smoothing) reaches 25 % of its local peak. Velocity: own-mic peak level in dBFS (LF band for kick, snare,
toms; 6-16 kHz for hats and cymbals).
Fills: runs of tom and snare hits (plus kicks inside them) at 8th-note density or faster that break the
section's groove, found against the beat grid (film/v5/grid.json) when it exists.
"""
import json
import os
import sys

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

K = ["kick", "snare", "racktom", "floortom", "hihat", "ohl", "ohr"]
HB = {"kick": (1500, 6000), "snare": (2000, 8000), "racktom": (2000, 8000), "floortom": (2000, 8000),
      "hihat": (6000, 16000), "ohl": (6000, 16000), "ohr": (6000, 16000)}
LB = {"kick": (40, 100), "snare": (150, 400), "racktom": (90, 170), "floortom": (45, 90)}
CACHE = os.path.join(C.OUT, "work", "hits_env.npz")


def _env(x, lo, hi, smooth, order=4):
    y = sosfiltfilt(butter(order, [lo, hi], btype="band", fs=C.SR, output="sos"), x)
    return np.convolve(np.abs(hilbert(y)), np.ones(smooth) / smooth, mode="same")


def envelopes():
    if os.path.exists(CACHE):
        z = np.load(CACHE)
        return {k: z["H_" + k] for k in K}, {k: z["L_" + k] for k in LB}, {k: z["F_" + k] for k in K}
    H, L, F = {}, {}, {}
    for k in K:
        x = C.stem(k)[:, 0]
        e = _env(x, *HB[k], 24)                                    # 0.5 ms, full rate (attack times)
        F[k] = e.astype(np.float32)
        e1 = np.convolve(e, np.ones(24) / 24, mode="same")          # ~1 ms, the calibrated detector envelope
        n = len(e1) // 48
        H[k] = (20 * np.log10(e1[:n * 48].reshape(n, 48).max(1) + 1e-9)).astype(np.float32)
        if k in LB:
            el = _env(x, *LB[k], 480, order=3)
            L[k] = (20 * np.log10(el[:n * 48].reshape(n, 48).max(1) + 1e-9)).astype(np.float32)
    np.savez(CACHE, **{"H_" + k: v for k, v in H.items()}, **{"L_" + k: v for k, v in L.items()},
             **{"F_" + k: v for k, v in F.items()})
    return H, L, F


def candidates(h, rise_db=6.0, sep=30):
    h = h.astype(np.float64)
    r = h - np.concatenate([np.full(3, h[0]), h[:-3]])
    top = np.percentile(h, 99.5)
    ok = (r > rise_db) & (r >= np.roll(r, 1)) & (r >= np.roll(r, -1))
    out = []
    for i in np.flatnonzero(ok):
        if h[i:i + 15].max() <= top - 50:
            continue
        if out and i - out[-1] < sep:
            if r[i] > r[out[-1]]:
                out[-1] = i
        else:
            out.append(i)
    return np.array(out, dtype=int)


def delta(x, i):
    pre = np.median(x[max(0, i - 25):max(1, i - 3)])
    post = x[max(0, i - 2):i + 12].max()
    return 10 * np.log10(max(10 ** (post / 10) - 10 ** (pre / 10), 1e-12))


def peak_db(x, i, a=0, b=40):
    return float(x[max(0, i + a):i + b].max())


def attack(F, i):
    """Attack time (s) near 1 ms index i: first sample reaching 25 % of the local peak."""
    a, b = max(0, (i - 6) * 48), (i + 15) * 48
    seg = F[a:b]
    if len(seg) == 0:
        return i / 1000
    k = int(np.argmax(seg >= 0.25 * seg.max()))
    return (a + k) / C.SR


def pw(x):
    return 10 ** (np.asarray(x, dtype=np.float64) / 10)


def clusters(cand):
    """All mics' candidates merged when within 6 ms of the cluster's first one; features are read at the
    cluster start (the earliest onset in any mic), which is where the thresholds were calibrated."""
    allc = sorted((int(i), k) for k in K for i in cand[k])
    out, cur = [], []
    for i, k in allc:
        if cur and i - cur[0][0] > 6:
            out.append(cur)
            cur = []
        cur.append((i, k))
    if cur:
        out.append(cur)
    return [(c[0][0], {k for _, k in c}) for c in out]


def classify(H, L, F):
    cand = {k: candidates(H[k]) for k in K}
    cl = clusters(cand)
    hits = {}
    feats = {"clusters": len(cl)}

    def dl(k, i):
        return delta(L[k], i) if k in L else -120.0

    def dh(k, i):
        return delta(H[k], i)

    rules = {
        "kick": lambda i: dl("kick", i) > -29 and dh("kick", i) - dl("kick", i) > -26,
        "snare": lambda i: dl("snare", i) > -28 and dh("snare", i) - dl("snare", i) > -22,
        "racktom": lambda i: dl("racktom", i) > -24 and
        dl("racktom", i) - max(dl("kick", i) - 15, dl("snare", i) - 10) > 4,
        "floortom": lambda i: dl("floortom", i) > -34 and
        dl("floortom", i) - max(dl("kick", i), dl("racktom", i) - 17) > 6,
    }
    for k, rule in rules.items():
        hits[k] = [(attack(F[k], i), peak_db(L[k], i), i) for i, _ in cl if rule(i)]
    # hi-hat: bleed transfer of snare/tom crack into the hat mic, measured at accepted snare/tom hits
    crack = []
    for k in ("snare", "racktom", "floortom"):
        for _, _, i in hits[k]:
            crack.append(dh("hihat", i) - dh(k, i))
    t_crack = float(np.median(crack))
    feats["hat_crack_transfer_db"] = round(t_crack, 1)
    out = []
    Hh = H["hihat"].astype(np.float64)
    for i, _ in cl:
        hh = dh("hihat", i)
        pred = max(dh("snare", i), dh("racktom", i), dh("floortom", i)) + t_crack
        if hh > -46 and hh - pred > 6:
            pk = Hh[i:i + 15].max()
            later = Hh[i + 60:i + 140].mean() if i + 140 < len(Hh) else -120
            out.append((attack(F["hihat"], i), float(pk), i, bool(later > pk - 12)))
    hits["hihat"] = out
    # cymbals from the overheads
    oh = pw(H["ohl"]) + pw(H["ohr"])
    hat = pw(H["hihat"])
    out = []
    for i, mem in cl:
        if not mem & {"ohl", "ohr", "hihat"}:
            continue
        if i < 70 or i + 300 > len(oh):
            continue
        a = 10 * np.log10(oh[i + 80:i + 300].mean() + 1e-15)
        b = 10 * np.log10(oh[i - 60:i - 10].mean() + 1e-15)
        c = 10 * np.log10(hat[i + 80:i + 300].mean() + 1e-15) - 15
        if a > -47 and a - b > 5 and a - c > 2:
            j = i if H["ohl"][i:i + 15].max() >= H["ohr"][i:i + 15].max() else i
            side = float(H["ohl"][i:i + 40].max() - H["ohr"][i:i + 40].max())
            fl = F["ohl"] + F["ohr"]
            crash = (a - b >= 9) or (a >= -36)
            out.append((attack(fl, j), float(10 * np.log10(oh[i:i + 40].max())), i, crash, round(side, 1), round(a - b, 1)))
    # merge cymbal onsets closer than 60 ms (keep the first, loudest level)
    merged = []
    for h in out:
        if merged and h[0] - merged[-1][0] < 0.06:
            if h[1] > merged[-1][1]:
                merged[-1] = (merged[-1][0],) + h[1:]
            continue
        merged.append(h)
    hits["cymbal"] = merged
    for k in ("kick", "snare", "racktom", "floortom", "hihat"):
        hits[k] = dedupe(hits[k])
    return hits, cand, feats


def dedupe(v, sep=0.035):
    """Neighbouring clusters can resolve to the same attack: keep one hit per 35 ms (first attack, max level)."""
    v = sorted(v, key=lambda h: h[0])
    out = []
    for h in v:
        if out and h[0] - out[-1][0] < sep:
            if h[1] > out[-1][1]:
                out[-1] = (out[-1][0], h[1]) + tuple(h[2:])
            continue
        out.append(h)
    return out


def main():
    H, L, F = envelopes()
    hits, cand, feats = classify(H, L, F)
    for k, v in hits.items():
        lv = np.array([h[1] for h in v])
        print(f"{k:9s} candidates {len(cand.get(k, [])):5d}  hits {len(v):4d}  level p10/p50/p90 "
              f"{np.percentile(lv, 10):6.1f} {np.percentile(lv, 50):6.1f} {np.percentile(lv, 90):6.1f}")
    np.save(os.path.join(C.OUT, "work", "hits_raw.npy"), {"hits": hits, "feats": feats}, allow_pickle=True)
    return hits, feats


if __name__ == "__main__":
    main()
