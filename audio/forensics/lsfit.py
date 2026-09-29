"""STFT-domain least squares: master(f, t) ~ sum_k H_k(f) X_k(f, t), one complex gain per stem per bin,
refit in overlapping windows (a slowly varying EQ + level per stem). Used to (a) remove the drums from the
master before aligning the non-drum mp3, and (b) test how well master = other + drums holds."""
import numpy as np
from scipy.signal import stft, istft

NFFT, HOP = 4096, 1024


def spec(x, sr=48000):
    """Zero-padded by NFFT on both sides so every sample is covered by full overlap-add."""
    x = np.concatenate([np.zeros(NFFT), x, np.zeros(NFFT)])
    f, t, Z = stft(x, fs=sr, nperseg=NFFT, noverlap=NFFT - HOP, boundary=None, padded=True)
    return f, t, Z


def ispec(Z, n, sr=48000):
    _, y = istft(Z, fs=sr, nperseg=NFFT, noverlap=NFFT - HOP, boundary=False)
    y = y[NFFT:NFFT + n]
    if len(y) < n:
        y = np.concatenate([y, np.zeros(n - len(y))])
    return y


def fit(M, Xs, win_frames=280, hop_frames=140, ridge=1e-3):
    """M: (F, T) target; Xs: list of (F, T) regressors. Returns fitted (F, T) and gains (nwin, F, K)."""
    F, T = M.shape
    K = len(Xs)
    X = np.stack(Xs, axis=-1)                                 # F, T, K
    out = np.zeros_like(M)
    wsum = np.zeros(T)
    starts = list(range(0, max(1, T - win_frames + 1), hop_frames))
    if starts[-1] + win_frames < T:
        starts.append(max(0, T - win_frames))
    gains = []
    taper = np.hanning(win_frames + 2)[1:-1]
    for s in starts:
        e = min(T, s + win_frames)
        Xw = X[:, s:e, :]                                    # F, W, K
        Mw = M[:, s:e]
        G = np.einsum("ftk,ftl->fkl", Xw.conj(), Xw)         # F, K, K
        tr = np.real(np.trace(G, axis1=1, axis2=2)) / K + 1e-20
        G = G + ridge * tr[:, None, None] * np.eye(K)[None]
        b = np.einsum("ftk,ft->fk", Xw.conj(), Mw)
        H = np.linalg.solve(G, b[..., None])[..., 0]          # F, K
        gains.append(H)
        w = taper[:e - s]
        out[:, s:e] += np.einsum("ftk,fk->ft", Xw, H) * w[None, :]
        wsum[s:e] += w
    out /= np.maximum(wsum, 1e-9)[None, :]
    return out, np.array(gains), starts
