// STUB (Unit B, TREATMENT section 6 and S18): the A/B toggle, a film graphic (not plugin UI): a
// segmented pill 856 x 96 at x 72, y 560 to 656 reading "BYPASS │ CHOROBOROS", mono 40 px. The
// active segment is filled #79b8ff with text #0b1420; BYPASS active is a #a8a7a0 outline. It
// slides over 3 frames (power3.out) on each slam; snares pulse its border +60 % for 6 frames.
//
// Agreed API:
//   const ab = createABToggle(layer, { x: 72, y: 560, w: 856, h: 96, hue: COLOR.fill.blue });
//   ab.render(t, { on: !demos.bypassAt(t), slamHit, pulse });

export function createABToggle() {
  throw new Error("abtoggle.js is a stub: Unit B delivers it (TREATMENT section 6)");
}
