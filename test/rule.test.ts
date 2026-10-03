// Rule jita_sell_band_weighted v1 (docs/22 §3.2 / §4.5): min_units by units, inclusive band edges, ties,
// single order, no order, determinism, rounding.
import assert from "node:assert/strict";
import { test } from "node:test";
import { priceAll, priceOrders, roundIsk, validateRule, DEFAULT_RULE, type Order, type RuleParams, type TypePrice } from "../src/rule.js";

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
