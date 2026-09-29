// STUB (Unit B, TREATMENT section 6): the portrait end card, main and TikTok variants, with the
// Buy button (the site's .btn--primary look, 856 x 140, cream #f5f2ea, Inter 600 56 px, radius
// 20 px, lucide ArrowRight), the secondary trial button (flag TRIAL_CTA), the offer and URL lines,
// the format row with the UNMODIFIED VST Compatible logo (type.formatRow; tiles 160 x 100) and the
// legal line (data-bleed, y 1552 to 1640). Boxes: TREATMENT 4.3 (main) and 7.4 (TikTok).
//
// Agreed API (Unit A's TikTok t07-buy.js calls it):
//   const card = createEndcard(layer, { variant: "main" | "tiktok", demos, beats, trialCta: true });
//   return { preload: card.preload, render(t) { card.render(t, { build: [t5181, t5229, t5278] }) } };
//   card.render(t, { build }) shows the pieces from their build times (hard cuts only); the VST tile
//   is never scaled, flashed, tinted or covered. card.buttonRect -> { x, y, w, h } for the flash mask.

export function createEndcard() {
  throw new Error("endcard.js is a stub: Unit B delivers it (TREATMENT section 6)");
}
