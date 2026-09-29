#!/usr/bin/env python3
"""Choroboros editor geometry, computed exactly as the release-candidate editor lays itself out.

Port of PluginEditorSetup::applyLayout (factory-engine path, Source/UI/Shell/PluginEditorSetup,
RC f984c9a) fed with the layout block of the factory defaults the editor loads on macOS and Linux
(json_defaults_dump.json, embedded as BinaryData json_defaults_dump_json; DefaultsPersistence.cpp).
Note that Assets/defaults_factory_mac.json is NOT what the editor reads.

Output: editor pixels at 1x (window 638 x 386: header 0..56, body 56..386), integers as JUCE
computes them. With --check <dir> it compares against component dumps of the real editor
(choro-snap <state>.json, see film/UI_FIDELITY.md) and exits 1 on any mismatch.

  python3 film/tools/rc_layout.py [--src /home/user/choroboros-rc] [--check DIR] [--js]

--js prints the table that film/lib/plate.js embeds (RC_GEOMETRY).
"""

import argparse
import json
import math
import os
import sys

ENGINES = ["green", "blue", "red", "purple", "black"]
SUFFIX = ["Green", "Blue", "Red", "Purple", "Black"]
UI_SCALE = 638.0 / 700.0  # ChoroborosPluginEditor::kUiScale (editorScale 1)
HEADER_H = 56             # TopHeaderBar::kReservedDesignHeight


def jround(v):
    """juce::roundToInt: round half away from zero (for our magnitudes, floor(v + 0.5))."""
    return int(math.floor(v + 0.5)) if v >= 0 else -int(math.floor(-v + 0.5))


def s(v):
    return jround(v * UI_SCALE)


def idiv(a, b):
    """C++ integer division (truncation toward zero)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def with_size_keeping_centre(r, w, h):
    x, y, rw, rh = r
    return [x + idiv(rw - w, 2), y + idiv(rh - h, 2), w, h]


def set_centre(r, cx, cy):
    x, y, w, h = r
    return [cx - idiv(w, 2), cy - idiv(h, 2), w, h]


def centre_y(r):
    return r[1] + idiv(r[3], 2)


def centre_x(r):
    return r[0] + idiv(r[2], 2)


def layout_for(L, ci):
    E = SUFFIX[ci]
    pick = lambda k: L.get(k + E, L.get(k))
    yOff = HEADER_H
    mainKnobSize = s(pick("mainKnobSize"))
    topY = s(pick("knobTopY"))
    cx = {k: s(pick(k + "CenterX")) for k in ("rate", "depth", "offset", "width")}
    trackStartX, trackStartY = s(pick("sliderTrackStartX")), s(pick("sliderTrackStartY"))
    trackEndX, trackEndY = s(pick("sliderTrackEndX")), s(pick("sliderTrackEndY"))
    sizeScale = pick("sliderSize") / 100.0
    sliderH = max(s(24), jround(s(18) * sizeScale))
    mixKnobSize = s(pick("mixKnobSize"))
    mixCenterX = s(pick("mixCenterX"))
    vlw, vlh = s(L["valueLabelWidth"]), s(L["valueLabelHeight"])
    valueY = s(pick("valueLabelY"))
    voX = {k: s(pick(k + "ValueOffsetX")) for k in cx}
    voY = {k: s(pick(k + "ValueOffsetY")) for k in cx}
    cvw, cvh = s(L["colorValueWidth"]), s(L["colorValueHeight"])
    colorValueY = s(pick("colorValueY"))
    colorValueXOffset = s(pick("colorValueXOffset"))
    mvw, mvh = s(L["mixValueWidth"]), s(L["mixValueHeight"])
    mixValueY = s(pick("mixValueY"))
    mixValueOffsetX = s(pick("mixValueOffsetX"))
    colorValueCenterX = s(L["colorValueCenterX"])
    mixKnobY = s(pick("mixKnobY"))

    sliderX = min(trackStartX, trackEndX)
    sliderW = max(1, abs(trackEndX - trackStartX))
    trackCenterY = idiv(trackStartY + trackEndY, 2)
    sliderY = trackCenterY - idiv(sliderH, 2)

    def knob(centerX):
        base_cy = topY + idiv(mainKnobSize, 2)
        return [centerX - idiv(mainKnobSize, 2), base_cy + yOff - idiv(mainKnobSize, 2), mainKnobSize, mainKnobSize]

    out = {k: knob(cx[k]) for k in cx}
    colorW, colorH = max(s(32), sliderW), max(s(18), sliderH)
    out["color"] = [sliderX + idiv(sliderW, 2) - idiv(colorW, 2), sliderY + idiv(sliderH, 2) + yOff - idiv(colorH, 2), colorW, colorH]
    m = max(s(18), mixKnobSize)
    out["mix"] = [mixCenterX - idiv(m, 2), mixKnobY + idiv(mixKnobSize, 2) + yOff - idiv(m, 2), m, m]

    values = {}
    for k in cx:
        values[k] = [cx[k] - idiv(vlw, 2) + voX[k], valueY + voY[k] + yOff, vlw, vlh]
    values["color"] = [colorValueCenterX - idiv(cvw, 2) + colorValueXOffset, colorValueY + yOff, cvw, cvh]
    values["mix"] = [mixCenterX - idiv(mvw, 2) + mixValueOffsetX, mixValueY + yOff, mvw, mvh]

    # Factory panels: 0.96 footprint about the centre, lowered s(3); readouts centred on the
    # knob (rate/depth 2 px left), raised s(3), Justification::centred.
    for k in ("rate", "depth", "offset", "width", "mix"):
        r = out[k]
        size = jround(r[2] * 0.96)
        r = with_size_keeping_centre(r, size, size)
        out[k] = [r[0], r[1] + s(3), r[2], r[3]]
    centres = {"rate": cx["rate"] - s(2), "depth": cx["depth"] - s(2), "offset": cx["offset"], "width": cx["width"],
               "color": centre_x(out["color"]), "mix": mixCenterX}
    for k, c in centres.items():
        values[k] = set_centre(values[k], c, centre_y(values[k]) - s(3))
    out["values"] = values

    # HQ switch: themed factory switch, atlas margins -> size s(146 - 20), pivot at the lamp.
    hqSize = max(s(16), s(L["hqSwitchSize"] - 20))
    hx = s(353 if ci == 2 else 352) + s(pick("hqSwitchOffsetX"))
    hy = s(183 if ci == 2 else 180) + yOff + s(pick("hqSwitchOffsetY"))
    out["hq"] = [hx - idiv(hqSize, 2), hy - idiv(hqSize, 2), hqSize, hqSize]

    # Value fonts: ProductTypography::valueTextFont("technology", bold) = JetBrains Mono SemiBold,
    # height = size * uiScale, min 10.5.
    out["fontH"] = {
        "main": max(10.5, L["knobValueFontSize"] * UI_SCALE),
        "color": max(10.5, L["colorValueFontSize"] * UI_SCALE),
        "mix": max(10.5, L["mixValueFontSize"] * UI_SCALE),
    }
    fx = {}
    for i, k in enumerate(("rate", "depth", "offset", "width")):
        key = lambda suf: L.get("mainValue" + k.capitalize() + suf + E)
        fx[k] = readout_fx(key, flip_prefix=None)
    for k in ("color", "mix"):
        def key(suf, k=k):
            names = [k + "Value" + suf, "value" + suf]
            if suf.startswith("PerChar"):
                names = [k + "ValueFx" + suf, "valueFx" + suf]
            return next((L[n] for n in names if n in L), None)
        fx[k] = readout_fx(key, flip_prefix=k)
    out["fx"] = fx
    return out


def readout_fx(key, flip_prefix):
    g = lambda suf, d=0: key(suf) if key(suf) is not None else d
    return {
        "glowAlpha": g("GlowAlphaPct") * 0.01,
        "glowSpread": g("GlowSpreadPxTimes100") * 0.01,
        "charDX": g("PerCharOffsetXPxTimes100") * 0.01,
        "charDY": g("PerCharOffsetYPxTimes100") * 0.01,
        "top": [g("TopReflectAlphaPct") * 0.01, g("TopReflectOffsetXPxTimes100") * 0.01, g("TopReflectOffsetYPxTimes100") * 0.01,
                g("TopReflectShearPct") * 0.01, g("TopReflectRotateDeg")],
        "bottom": [g("BottomReflectAlphaPct") * 0.01, g("BottomReflectOffsetXPxTimes100") * 0.01, g("BottomReflectOffsetYPxTimes100") * 0.01,
                   g("BottomReflectShearPct") * 0.01, g("BottomReflectRotateDeg")],
        "blur": g("ReflectBlurPxTimes100") * 0.01,
        "squash": g("ReflectSquashPct") * 0.01,
    }


def grp_main(L):
    """Main readout flip (mainValue<Field>Flip*<Engine>; equal for every field and engine)."""
    v = lambda suf: L.get("mainValueRate" + suf + "Green")
    return {"ms": v("FlipDurationMs"), "travel": v("FlipTravelUpPxTimes100") * 0.01, "travelOut": v("FlipTravelOutPct") * 0.01,
            "travelIn": v("FlipTravelInPct") * 0.01, "shear": v("FlipShearPct") * 0.01, "minScale": 1 - v("FlipMinScalePct") * 0.01}


def check(table, d):
    """Compare with choro-snap component dumps (<engine>-*-1x.json or any *.json) in d."""
    bad = 0
    names = ["rate", "depth", "offset", "width", "color", "mix"]
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        t = json.load(open(os.path.join(d, f)))
        if t.get("w") != 638:
            continue
        kids = t["children"]
        label = next((c for c in kids if c["cls"].endswith("TopHeaderBar")), None)
        eng = None
        for c in kids:
            if c["cls"].endswith("TopHeaderBar"):
                for cc in c["children"]:
                    if cc["cls"].endswith("EngineSelectorComboBox"):
                        eng = cc["text"].lower()
        if eng not in table:
            continue
        T = table[eng]
        sliders = [c for c in kids if c["cls"].endswith("SmoothedSlider")]
        labels = [c for c in kids if c["cls"].endswith("LabelWithContainer") and c["visible"]]
        hq = next(c for c in kids if c["cls"].endswith("AnimatedToggleButton"))
        pairs = [(f"{n} knob", T[n], sl) for n, sl in zip(names, sliders)]
        pairs += [(f"{n} value", T["values"][n], lb) for n, lb in zip(names, labels)]
        pairs.append(("hq", T["hq"], hq))
        for what, ours, c in pairs:
            real = [c["x"], c["y"], c["w"], c["h"]]
            ok = ours == real
            bad += not ok
            print(f"{f:28s} {eng:7s} {what:14s} ours {ours} real {real} {'ok' if ok else 'MISMATCH'}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/home/user/choroboros-rc")
    ap.add_argument("--check")
    ap.add_argument("--js", action="store_true")
    a = ap.parse_args()
    L = json.load(open(os.path.join(a.src, "json_defaults_dump.json")))["layout"]
    table = {e: layout_for(L, i) for i, e in enumerate(ENGINES)}
    if a.check:
        bad = check(table, a.check)
        print("mismatches:", bad)
        return 1 if bad else 0
    out = {"engines": table, "flip": {"main": grp_main(L), "color": flip_group(L, "colorValueFlip"), "mix": flip_group(L, "mixValueFlip")}}
    if a.js:
        print(json.dumps(out, separators=(",", ":")))
    else:
        print(json.dumps(out, indent=1))
    return 0


def flip_group(L, prefix):
    v = lambda suf: L.get(prefix + suf)
    return {"ms": v("DurationMs"), "travel": v("TravelUpPxTimes100") * 0.01, "travelOut": v("TravelOutPct") * 0.01,
            "travelIn": v("TravelInPct") * 0.01, "shear": v("ShearPct") * 0.01, "minScale": 1 - v("MinScalePct") * 0.01}


if __name__ == "__main__":
    sys.exit(main())
