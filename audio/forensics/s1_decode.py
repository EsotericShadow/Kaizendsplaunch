"""Step 1: decode the master mp3 to /home/user/build/v5/master_src.wav at 48 kHz.

The mp3 is decoded gapless by ffmpeg (the LAME Info tag gives encoder delay 576 and padding 1036; ffmpeg
drops 576 + 529 decoder delay = 1105 samples at the start and 1036 - 529 = 507 at the end). libsndfile
(mpg123) decodes the same samples at offset 0 (max difference ~1e-6), so t = 0 is the song's first sample.
The 44.1 -> 48 kHz conversion is a linear-phase polyphase FIR (160/147, Kaiser, 52k taps, pass band to
20.5 kHz, stop band from 22.05 kHz at about -120 dB). resample_poly removes the filter's (integer) group
delay, which the impulse test below checks: a click at 44.1 kHz sample n lands at 48 kHz sample
n * 160 / 147 with no offset.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import firwin, resample_poly, kaiser_beta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

UPR, DNR = 160, 147


def aa_filter():
    fs_up = 44100 * UPR
    beta = kaiser_beta(120.0)
    trans = 22050 - 20500
    n = int(np.ceil((120 - 7.95) / (2.285 * 2 * np.pi * trans / fs_up)))
    n += 1 - n % 2                                  # odd length -> integer group delay, removed exactly
    h = firwin(n, (20500 + 22050) / 2, window=("kaiser", beta), fs=fs_up)          # resample_poly multiplies by up itself
    return h


def resample(x, h):
    return resample_poly(x, UPR, DNR, axis=0, window=h)


def main():
    os.makedirs(os.path.join(C.OUT, "work"), exist_ok=True)
    wg = os.path.join(C.OUT, "work", "master44_gapless.wav")
    wr = os.path.join(C.OUT, "work", "master44_raw.wav")
    g = C.decode_mp3(C.MASTER_MP3, wg, gapless=True)
    r = C.decode_mp3(C.MASTER_MP3, wr, gapless=False)
    shift = next(o for o in range(4000) if np.allclose(r[o:o + 20000], g[:20000], atol=1e-7))
    try:
        s, _ = sf.read(C.MASTER_MP3, dtype="float64", always_2d=True)   # libsndfile/mpg123
        n = min(len(s), len(g))
        lsf_err = float(np.max(np.abs(s[:n] - g[:n])))
        lsf_len = len(s)
    except Exception as e:                                                 # older libsndfile: no mp3
        lsf_err, lsf_len = None, str(e)
    h = aa_filter()
    # impulse timing test
    imp = np.zeros((44100, 1)); n0 = 14700; imp[n0] = 1.0                  # 14700 * 160/147 = 16000 exactly
    ri = resample(imp, h)[:, 0]
    peak = int(np.argmax(np.abs(ri)))
    # sub-sample centroid of the main lobe
    w = ri[peak - 3:peak + 4]
    cen = peak - 3 + float(np.sum(np.arange(7) * w ** 2) / np.sum(w ** 2))
    y = resample(g, h)
    peak_in, peak_out = float(np.max(np.abs(g))), float(np.max(np.abs(y)))
    sf.write(os.path.join(C.OUT, "master_src.wav"), y.astype(np.float32), C.SR, subtype="FLOAT")
    meta = {
        "source": os.path.basename(C.MASTER_MP3),
        "mp3_tag": {"encoder": "LAME3.100", "enc_delay": 576, "padding": 1036, "frames": 6473},
        "decoder": "ffmpeg mp3float, gapless (LAME tag honoured)",
        "gapless_trim_start_samples_44k1": shift,
        "gapless_trim_start_s": shift / 44100,
        "libsndfile_len": lsf_len, "libsndfile_max_abs_diff": lsf_err,
        "samples_44k1": len(g), "duration_s": len(g) / 44100,
        "resampler": {"up": UPR, "down": DNR, "taps": len(h), "window": "kaiser(beta for 120 dB)",
                      "passband_hz": 20500, "stopband_hz": 22050},
        "impulse_test": {"in_sample_44k1": n0, "expected_48k": n0 * UPR / DNR, "peak_48k": peak,
                         "centroid_48k": round(cen, 4)},
        "samples_48k": len(y), "duration_48k_s": len(y) / C.SR,
        "peak_in": peak_in, "peak_out": peak_out,
        "first_sample_abs": float(np.max(np.abs(g[0]))),
    }
    C.write_json(os.path.join(C.OUT, "master_src.json"), meta, indent=1)
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
