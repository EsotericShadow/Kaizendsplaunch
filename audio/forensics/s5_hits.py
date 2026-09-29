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
  floor tom floor LF delta > -34 and 6 dB above max(kick LF, rack LF - 17), and its own stick crack (HF)
            no more than 2 dB under the rack/snare crack in its mic (the floor-tom mic rings in sympathy with
            the kick and rack tom; this last rule was added after the intro showed such resonance bumps)
  hi-hat    an onset in the hat mic itself, rising >= 10 dB within 8 ms, hat HF delta > -40 and 6 dB above
            the snare/tom crack the hat mic hears at that moment (transfer measured at the accepted snare and
            tom hits); open if the hat mic stays within 12 dB of its peak 60-140 ms later
  crash     overheads (L+R, 6-16 kHz, 20 ms smoothed): a peak >= -34 dBFS that stays within 10 dB of itself
            for >= 160 ms (bleed from snare, toms and hats falls 10 dB in < 120 ms); time = the kick/snare/tom
            attack it lands with (its own overhead rise starts ~10 ms earlier and is kept as overhead_rise_s)
  cymbal    other short overhead peaks (prominence >= 8 dB, >= -45 dBFS) with no snare/tom/hat hit within 25 ms
Features are read at the cluster start (the earliest onset of any mic within 6 ms), where the thresholds
were calibrated. Times: the attack, i.e. the first sample in [-6, +15] ms where the own-mic HF envelope
(full rate, 0.5 ms smoothing) reaches 25 % of its local peak. Velocity: own-mic peak level in dBFS (LF band for kick, snare,
toms; 6-16 kHz for hats and cymbals).
Same-piece hits closer than 35 ms are merged (neighbouring clusters can resolve to the same attack).
Fills are found in s6_map.py, against the grid and the sections.
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
        dl("floortom", i) - max(dl("kick", i), dl("racktom", i) - 17) > 6 and
        dh("floortom", i) - max(dh("racktom", i), dh("snare", i)) > -2,
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
    for i, mem in cl:
        if "hihat" not in mem or i < 30:
            continue
        hh = dh("hihat", i)
        pred = max(dh("snare", i), dh("racktom", i), dh("floortom", i)) + t_crack
        sharp = Hh[i:i + 8].max() - np.median(Hh[i - 25:i - 3])
        if hh > -40 and hh - pred > 6 and sharp >= 10:
            pk = Hh[i:i + 15].max()
            later = Hh[i + 60:i + 140].mean() if i + 140 < len(Hh) else -120
            out.append((attack(F["hihat"], i), float(pk), i, bool(later > pk - 12)))
    hits["hihat"] = out
    hits["crash"], hits["ride"] = cymbals(F, hits)
    for k in ("kick", "snare", "racktom", "floortom", "hihat"):
        hits[k] = dedupe(hits[k])
    return hits, cand, feats


def cymbals(F, hits):
    """Crashes and other cymbal hits from the overheads (L+R, 6-16 kHz), on a 20 ms smoothed level where a
    crash is a peak that stays within 10 dB of itself for >= 160 ms (snare, tom and hat bleed in the
    overheads falls 10 dB in < 120 ms); measured: every peak louder than -30 dBFS with such a decay, and
    nothing else, sits in that corner. Other cymbal hits ("ride"): short overhead peaks (prominence >= 8 dB,
    louder than -45 dBFS) with no snare, tom, hat or crash hit within 25 ms."""
    from scipy.signal import find_peaks
    p = F["ohl"].astype(np.float64) ** 2 + F["ohr"].astype(np.float64) ** 2
    c = np.convolve(p, np.ones(960) / 960, mode="same")
    n = len(c) // 48
    oh = 10 * np.log10(c[:n * 48].reshape(n, 48).mean(1) + 1e-15)
    pk, pr = find_peaks(oh, prominence=6, distance=60)
    fast = np.sqrt(p)
    crash, ride = [], []
    others = np.sort(np.concatenate([[h[0] for h in hits[k]] for k in ("snare", "racktom", "floortom", "hihat")]))
    drum_t = np.sort(np.concatenate([[h[0] for h in hits[k]] for k in ("kick", "snare", "racktom", "floortom")]))
    for q, prom in zip(pk, pr["prominences"]):
        lvl = oh[q]
        nxt = pk[pk > q][0] if (pk > q).any() else len(oh)
        seg = oh[q:min(nxt, q + 1500)]
        below = np.flatnonzero(seg < lvl - 10)
        t10 = int(below[0]) if len(below) else len(seg)
        a0, a1 = max(0, (q - 150) * 48), (q + 5) * 48
        e = 20 * np.log10(np.convolve(fast[a0:a1], np.ones(96) / 96, mode="same") + 1e-9)
        pre = np.median(e[:70 * 48])
        k0 = 70 * 48 + int(np.argmax(e[70 * 48:] > pre + 6))
        t_rise = (a0 + k0) / C.SR                               # overheads 6 dB over the wash before
        j = np.searchsorted(drum_t, t_rise)
        cand_t = drum_t[max(0, j - 2):j + 3]
        near = cand_t[np.abs(cand_t - t_rise) < 0.035]
        if len(near):
            t = float(near[np.argmin(np.abs(near - t_rise - 0.012))])
        else:                                                   # inside a wash: sharpest 3 ms rise nearby
            b0 = max(0, int((t_rise - 0.02) * C.SR))
            e2 = 20 * np.log10(np.convolve(fast[b0:b0 + 80 * 48], np.ones(48) / 48, mode="same") + 1e-9)
            t = (b0 + 144 + int(np.argmax(e2[144:] - e2[:-144]))) / C.SR
        side = float(10 * np.log10((F["ohl"][a0:a1].astype(np.float64) ** 2).sum() /
                                   ((F["ohr"][a0:a1].astype(np.float64) ** 2).sum() + 1e-20)))
        if t10 >= 160 and lvl >= -34:
            crash.append((t, round(float(lvl), 1), q, round(side, 1), t10, round(t_rise, 4)))
        elif lvl >= -45 and prom >= 8:
            j = np.searchsorted(others, t)
            near = min(abs(others[max(0, j - 1):j + 1] - t)) if len(others) else 1.0
            if near > 0.025 and (not crash or t - crash[-1][0] > 0.025):
                ride.append((t, round(float(lvl), 1), q, round(side, 1), t10, round(t_rise, 4)))
    return crash, ride


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
