// Components for the Still Life film. Scenes receive this namespace as ctx.lib.

export * as util from "./util.js";
export * as cues from "./cues.js";
export * as layout from "./layout.js";
export * as plate from "./plate.js";
export * as chorustype from "./chorustype.js";
export * as scope from "./scope.js";
export * as smear from "./smear.js";
export * as ring from "./ring.js";
export * as type from "./type.js";
export * as grain from "./grain.js";
export * as hero from "./hero.js";
export * as clips from "./clips.js";
export * as stage from "./stage.js";

export { loadCues, Cues } from "./cues.js";
export { createPlate, driftPx } from "./plate.js";
export { createChorusType } from "./chorustype.js";
export { createScope } from "./scope.js";
export { SmearGroup, smearU, smearParams } from "./smear.js";
export { createRing } from "./ring.js";
export { createGrain } from "./grain.js";
export { createHero } from "./hero.js";
export { clipSequence } from "./clips.js";

// v5 portrait kit
export * as beats from "./beats.js";
export * as motion from "./motion.js";
export * as portrait from "./portrait.js";
export { loadBeats, getBeats, Beats } from "./beats.js";
export * as demos from "./demos.js";
export * as flash from "./flash.js";
export * as chip from "./chip.js";
export * as montage from "./montage.js";
export * as slices from "./slices.js";
export { loadDemos, getDemos } from "./demos.js";
export { createFlash, registerFlash, resolveFlashes } from "./flash.js";
export { createChip } from "./chip.js";
export { createMontage } from "./montage.js";
export { createSlice } from "./slices.js";
