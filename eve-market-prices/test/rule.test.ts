// Rule jita_sell_band_weighted v1 (docs/22 §3.2 / §4.5): min_units by units, inclusive band edges, ties,
// single order, no order, determinism, rounding.
import assert from "node:assert/strict";
import { test } from "node:test";
import { applyRule, priceAll, priceOrders, roundIsk, validateRule, DEFAULT_RULE, type Order, type RuleParams, type TypePrice } from "../src/rule.js";

const o = (price: number, volume_remain: number, type_id = 34): Order => ({ type_id, price, volume_remain });
const R1: RuleParams = { min_units: 1, band: 0.05 };
const core = (p: TypePrice | null) => p && { p0: p.p0, price: p.price, units: p.units, orders: p.orders };

/** docs/22 §4.5 invariants, as engines check them on load */
function invariants(p: TypePrice) {
  assert.ok(p.p0 <= p.price && p.price <= p.band_max, JSON.stringify(p));
  assert.ok(0 < p.units && p.units <= p.units_considered, JSON.stringify(p));
  assert.ok(0 < p.orders && p.orders <= p.orders_considered && p.orders_considered <= p.orders_total, JSON.stringify(p));
}

test("rule: p0 and unit-weighted average within the 5% band; every §4.5 field", () => {
  const p = priceOrders([o(100, 10), o(104, 30), o(105, 60), o(106, 1000), o(90, 3)], { min_units: 10, band: 0.05 })!;
  // 90 x3 dropped (3 < 10 units); band [100, 105]: (100*10 + 104*30 + 105*60) / 100 = 104.2
  assert.deepEqual(p, { price: 104.2, p0: 100, band_max: 105, units: 100, orders: 3, units_considered: 1100, orders_considered: 4, orders_total: 5 });
  invariants(p);
});

test("rule: band edges are inclusive: exactly p0 * (1 + band) is in, one cent above is out", () => {
  assert.deepEqual(core(priceOrders([o(200, 1), o(210, 1)], R1)), { p0: 200, price: 205, units: 2, orders: 2 });
  assert.deepEqual(core(priceOrders([o(200, 1), o(210.01, 1)], R1)), { p0: 200, price: 200, units: 1, orders: 1 });
  // binary edges: 0.1 * 1.1 = 0.11000000000000001, 3 * 1.1 = 3.3000000000000003, 4.0 * 1.05 = 4.2 (noise trimmed)
  assert.equal(priceOrders([o(0.1, 1), o(0.11, 1)], { min_units: 1, band: 0.1 })!.orders, 2);
  assert.equal(priceOrders([o(3, 1), o(3.3, 1)], { min_units: 1, band: 0.1 })!.orders, 2);
  const e = priceOrders([o(4, 1), o(4.2, 1)], R1)!;
  assert.equal(e.band_max, 4.2);
  assert.equal(e.orders, 2);
  invariants(e);
});

test("rule: band 0 averages only the orders tied at p0", () => {
  assert.deepEqual(core(priceOrders([o(50, 3), o(50, 7), o(50.01, 100)], { min_units: 1, band: 0 })), { p0: 50, price: 50, units: 10, orders: 2 });
});

test("rule: min_units filters each order by its own unit count, not a share of orders", () => {
  // the cheap 5-unit order is dropped; p0 moves to 120
  const p = priceOrders([o(100, 5), o(120, 50), o(125, 50), o(130, 50)], { min_units: 10, band: 0.05 })!;
  assert.deepEqual(core(p), { p0: 120, price: 122.5, units: 100, orders: 2 });
  assert.equal(p.orders_considered, 3);
  assert.equal(p.orders_total, 4);
  // exactly min_units is kept
  assert.equal(priceOrders([o(100, 10)], { min_units: 10, band: 0.05 })!.p0, 100);
  // 90% of the orders are small: still only the unit count matters
  const many = [...Array.from({ length: 9 }, (_, i) => o(10 + i, 1)), o(50, 1000)];
  assert.deepEqual(core(priceOrders(many, { min_units: 2, band: 0.05 })), { p0: 50, price: 50, units: 1000, orders: 1 });
});

test("rule: all orders below min_units -> no price, listed missing", () => {
  assert.equal(priceOrders([o(1, 1), o(2, 9)], { min_units: 10, band: 0.05 }), null);
  const r = priceAll([o(1, 1, 34), o(5, 100, 35)], { min_units: 10, band: 0.05 });
  assert.deepEqual([...r.prices.keys()], [35]);
  assert.deepEqual(r.missing, [34]);
});

test("rule: single order; empty list; buy orders and bad prices ignored", () => {
  const s = priceOrders([o(42.12, 7)], R1)!;
  assert.deepEqual(s, { price: 42.12, p0: 42.12, band_max: 44.226, units: 7, orders: 1, units_considered: 7, orders_considered: 1, orders_total: 1 });
  invariants(s);
  assert.equal(priceOrders([]), null);
  assert.equal(priceOrders([{ ...o(10, 5), is_buy_order: true }, o(0, 5), o(Number.NaN, 5)], R1), null);
});

test("rule: result does not depend on input order", () => {
  const os = [o(4.0, 1000), o(4.1, 3000), o(4.05, 7), o(4.19, 13), o(3.99, 1)];
  const a = priceOrders(os, R1)!;
  for (let i = 1; i < os.length; i++) assert.deepEqual(priceOrders([...os.slice(i), ...os.slice(0, i)], R1), a);
  assert.deepEqual(priceOrders([...os].reverse(), R1), a);
  invariants(a);
});

test("rule: price rounded to 0.01 ISK half to even, robust to binary noise; sub-cent averages clamp to the band", () => {
  assert.equal(roundIsk(4.075), 4.08); // 407.5 -> 408 (even)
  assert.equal(roundIsk(4.085), 4.08); // 408.5 -> 408 (even)
  assert.equal(roundIsk(1.005), 1.0);
  assert.equal(roundIsk(1.015), 1.02);
  assert.equal(roundIsk(2.004999), 2);
  assert.equal(roundIsk(10.1128333), 10.11);
  assert.equal(roundIsk(123456789.125), 123456789.12);
  // (4.0 * 1000 + 4.1 * 3000) / 4000 = 4.075 -> 4.08
  assert.equal(priceOrders([o(4.0, 1000), o(4.1, 3000)], R1)!.price, 4.08);
  // sub-cent order prices: the rounded average would fall below p0; clamped to p0
  const c = priceOrders([o(10.004, 1000), o(10.006, 1)], R1)!;
  assert.equal(c.price, 10.004);
  invariants(c);
});

test("rule: priceAll groups by type, ascending type ids", () => {
  const r = priceAll([o(5, 1, 587), o(4, 1, 34), o(5.2, 3, 587)], R1);
  assert.deepEqual([...r.prices.keys()], [34, 587]);
  assert.equal(r.prices.get(587)!.price, 5.15);
});

test("rule: parameters and defaults (docs/22: min_units 10, band 0.05)", () => {
  assert.deepEqual(validateRule({}), DEFAULT_RULE);
  assert.deepEqual(DEFAULT_RULE, { min_units: 10, band: 0.05 });
  assert.deepEqual(validateRule({ min_units: 1, band: undefined }), { min_units: 1, band: 0.05 });
  assert.throws(() => validateRule({ min_units: 0 }), /min_units/);
  assert.throws(() => validateRule({ min_units: 1.5 }), /min_units/);
  assert.throws(() => validateRule({ band: -0.1 }), /band/);
  assert.throws(() => validateRule({ band: Number.NaN }), /band/);
});

test("rule: an order one ulp above band_max is outside the band (order prices are not rounded; bench d22 band_edge_just_above)", () => {
  const p = priceOrders([o(1000, 10), o(1050.0000000000002, 30), o(1050, 5)], { min_units: 5, band: 0.05 })!;
  assert.deepEqual(core(p), { p0: 1000, price: 1016.67, units: 15, orders: 2 });
  assert.equal(p.band_max, 1050);
});

test("applyRule: rule descriptor + raw ESI book (CLI `rule`): location / buy filter, descriptor checks", () => {
  const book = [
    { type_id: 34, price: 5, volume_remain: 100, location_id: 60003760, is_buy_order: false },
    { type_id: 34, price: 4, volume_remain: 100, location_id: 60008494, is_buy_order: false },
    { type_id: 34, price: 6, volume_remain: 100, location_id: 60003760, is_buy_order: true },
  ];
  const rule = { name: "jita_sell_band_weighted", version: 1, order_side: "sell", location_id: 60003760, min_units: 10, band: 0.05, weighting: "units" };
  assert.deepEqual(applyRule({ rule, orders: book }), { price: 5, p0: 5, band_max: 5.25, units: 100, orders: 1, units_considered: 100, orders_considered: 1, orders_total: 1 });
  assert.equal(applyRule({ rule, orders: [] }), null);
  assert.throws(() => applyRule({ rule: { ...rule, version: 2 }, orders: book }), /version/);
  assert.throws(() => applyRule({ rule: { ...rule, weighting: "orders" }, orders: book }), /weighting/);
  assert.throws(() => applyRule({ rule: { ...rule, name: "x" }, orders: book }), /unknown rule/);
});

// Python reference: float(Decimal(f"{v:.12g}").quantize(Decimal("0.01"), ROUND_HALF_EVEN)) (bench d22/README.md step 7).
// The first entries are the spec's examples; 55174443703.65 … 28213005439.55 are values where the earlier
// trim(v * 100) rounding disagreed with the spec (> 10 integer digits: the 12-digit value has < 2 decimals).
const ROUND_VECTORS: [string, string][] = [["100.335", "100.34"], ["100.345", "100.34"], ["2.675", "2.68"], ["4.085", "4.08"], ["4.075", "4.08"], ["1.005", "1.0"], ["1.015", "1.02"], ["0.00405", "0.0"], ["0.005", "0.0"], ["0.015", "0.02"], ["0.025", "0.02"], ["1e-09", "0.0"], ["123456789.125", "123456789.12"], ["999999999999.995", "1000000000000.0"], ["1234567.8949999998", "1234567.9"], ["1057.9379999999999", "1057.94"], ["3.9100000000000006", "3.91"], ["0.30000000000000004", "0.3"], ["5e-324", "0.0"], ["1000000000000000.1", "1000000000000000.0"], ["55174443703.65", "55174443703.7"], ["93403376482.95", "93403376482.9"], ["63960408154.95", "63960408154.9"], ["9656027428.935", "9656027428.93"], ["4417839264.575", "4417839264.57"], ["28213005439.55", "28213005439.5"], ["23796.462709189138", "23796.46"], ["13042279608.514273", "13042279608.5"], ["6039200.385961945", "6039200.39"], ["580852.0843500559", "580852.08"], ["131679915.54874137", "131679915.55"], ["46923.233761902164", "46923.23"], ["23433096.104669638", "23433096.1"], ["4702635075.22448", "4702635075.22"], ["549.6311670270055", "549.63"], ["0.0639068140544162", "0.06"], ["0.023192200537667164", "0.02"], ["86804.53071432968", "86804.53"], ["0.0003899367208872129", "0.0"], ["0.006714114753695925", "0.01"], ["159399.93976228117", "159399.94"], ["42789029.33945994", "42789029.34"], ["310117514.69749993", "310117514.7"], ["269431.6690619967", "269431.67"], ["71882392406.5803", "71882392406.6"], ["387608585.61195046", "387608585.61"], ["921.0986675838744", "921.1"], ["728125.9730525968", "728125.97"], ["44462105605.076065", "44462105605.1"], ["13.414911090483262", "13.41"], ["0.009745430973087721", "0.01"], ["4.94883412249289", "4.95"], ["965.480138898203", "965.48"], ["7789725856.978318", "7789725856.98"], ["30102.61984255054", "30102.62"], ["833477.1199961472", "833477.12"]];

test("roundIsk: half-even on the 12-significant-digit decimal value, exactly like the spec (Python Decimal vectors)", () => {
  for (const [v, want] of ROUND_VECTORS) assert.equal(roundIsk(Number(v)), Number(want), v);
  assert.equal(Object.is(roundIsk(-0.001), 0), true, "no negative zero");
  assert.equal(roundIsk(-2.675), -2.68);
  assert.throws(() => roundIsk(NaN), /non-finite/);
});
