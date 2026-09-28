// Shot 4, 7.85-8.00: nine frames of #050506 before the impact. Everything else is already hidden;
// this opaque layer on top guarantees it.
const T0 = 7.85;
const T1 = 8.0;

export default {
  id: "shot04-stop",
  t0: T0,
  t1: T1,
  build(ctx) {
    const { util } = ctx.lib;
    const layer = ctx.layer("black", 100);
    layer.style.background = "#050506";
    return {
      render(t) {
        util.show(layer, t >= T0 && t < T1);
      },
    };
  },
};
