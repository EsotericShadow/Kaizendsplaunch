"""Section edit: which Choroboros render feeds each instrument in each section
(cues.json "sections"), joined with 20 ms equal-power cross-fades that end
exactly on the section boundary. Every render is full length and film-aligned,
so the outgoing and incoming renders are both already running at a join (it
behaves like the plugin's own engine switch).

The hard silences (sections whose "audio" is empty: 7.85-8.00, 49.85-50.00,
69.50-70.00) are not joins: the neighbouring render simply continues and the
silence is applied afterwards as a hard cut (3 ms fade to zero, digital
silence, hard restart), see common.hard_silence.
"""
from __future__ import annotations

import numpy as np

from common import Film, fit, hard_silence, read, section_edit


def silences(cues):
    return [(float(s["t0"]), float(s["t1"])) for s in cues["sections"] if not s["audio"]]


def stem_plan(cues, stem):
    """[(t0, t1, rid or None)] covering the film for one instrument, with
    silences merged into the preceding section and equal neighbours merged."""
    plan = []
    for s in cues["sections"]:
        t0, t1 = float(s["t0"]), float(s["t1"])
        if not s["audio"]:                      # hard silence: extend the previous section
            if plan:
                plan[-1] = (plan[-1][0], t1, plan[-1][2])
            else:
                plan.append((t0, t1, None))
            continue
        rid = s["audio"].get(stem)
        if plan and plan[-1][2] == rid:
            plan[-1] = (plan[-1][0], t1, rid)
        else:
            plan.append((t0, t1, rid))
    return plan


def joins(cues, stem):
    p = stem_plan(cues, stem)
    return [(p[i][1], p[i][2], p[i + 1][2]) for i in range(len(p) - 1)]


_CACHE = {}


def render(film: Film, rid):
    key = (film.name, rid)
    if key not in _CACHE:
        _CACHE[key] = read(film.render_path(rid))
    return _CACHE[key]


def edited(film: Film, stem, cues=None):
    """Stereo (n, 2) edit of one instrument, before any gain."""
    cues = cues or film.cues
    n = film.n
    plan = stem_plan(cues, stem)
    parts = [(t0, t1, fit(render(film, rid), n) if rid else None) for (t0, t1, rid) in plan]
    if all(p[2] is None for p in parts):
        return np.zeros((n, 2))
    y = section_edit(parts, n)
    for a, b in silences(cues):
        y = hard_silence(y, a, b)
    return y
