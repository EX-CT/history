// The pricing rule `jita_sell_band_weighted` v1 (eve-fit-docs docs/22 §3.2). Pure, no I/O; Node and browser.
//
// Per type, over the SELL orders at one location (sources filter region / location / side first):
//   1. drop every order with volume_remain < min_units (a filter on each order's unit count, not a percentage);
//   2. p0 = the lowest price among the remaining orders;
//   3. band: every remaining order with p0 <= price <= band_max, band_max = p0 * (1 + band) (both edges inclusive);
//   4. price = sum(price_i * volume_remain_i) / sum(volume_remain_i) over the band, rounded to 0.01 ISK half-to-even.
// The type gets no price (snapshot `missing`) when no order survives step 1.

export interface Order {
  type_id: number;
  price: number;
  volume_remain: number;
  /** ESI station / structure id; sources filter on it before the rule runs */
  location_id?: number;
  order_id?: number;
  is_buy_order?: boolean;
}

export interface RuleParams {
  /** orders with fewer units remaining are dropped (integer >= 1; default 10, docs/22 §3.2) */
  min_units: number;
  /** relative band above p0 that is averaged (default 0.05 = 5%) */
  band: number;
}

export const RULE_NAME = "jita_sell_band_weighted";
export const RULE_VERSION = 1;
export const DEFAULT_RULE: Readonly<RuleParams> = Object.freeze({ min_units: 10, band: 0.05 });

/** docs/22 §4.5 per-type entry */
export interface TypePrice {
  /** snapshot price, ISK per unit, 0.01 ISK half-to-even */
  price: number;
  /** lowest price after the min_units filter */
  p0: number;
  /** p0 * (1 + band) */
  band_max: number;
  /** units in the band (the weights) */
  units: number;
  /** orders in the band */
  orders: number;
  /** units of all orders left after the min_units filter */
  units_considered: number;
  /** orders left after the min_units filter */
  orders_considered: number;
  /** sell orders at the location before any filtering */
  orders_total: number;
}

export function validateRule(r: Partial<RuleParams>): RuleParams {
  const out = { ...DEFAULT_RULE, ...Object.fromEntries(Object.entries(r).filter(([, v]) => v !== undefined)) } as RuleParams;
  if (!Number.isInteger(out.min_units) || out.min_units < 1) throw new Error(`min_units must be an integer >= 1 (got ${out.min_units})`);
  if (!Number.isFinite(out.band) || out.band < 0 || out.band > 10) throw new Error(`band must be a number in [0, 10] (got ${out.band})`);
  return { min_units: out.min_units, band: out.band };
}

/** Strip binary noise (4.2000000000000002 -> 4.2) so decimal edges compare as written. */
export const trim = (v: number) => Number(v.toPrecision(12));

/**
 * Round to 0.01 ISK, half to even, on the **12-significant-digit decimal value** of v (docs/22 §4.5; bench
 * eve-dogma-bench d22/README.md "Pricing rule spec" step 7, Python
 * `float(Decimal(f"{v:.12g}").quantize(Decimal("0.01"), ROUND_HALF_EVEN))`): 100.335 -> 100.34, 100.345 -> 100.34,
 * 2.675 -> 2.68, 4.085 -> 4.08. Exact decimal arithmetic (BigInt); the result is the double nearest that decimal.
 */
export function roundIsk(v: number): number {
  if (!Number.isFinite(v)) throw new Error(`roundIsk: non-finite ${v}`);
  const m = /^(-?)(\d+)(?:\.(\d+))?(?:e([+-]\d+))?$/.exec(v.toPrecision(12));
  if (!m) throw new Error(`roundIsk: cannot parse ${v.toPrecision(12)}`);
  const [, sign, ip, fp = "", ex = "0"] = m;
  const digits = BigInt(ip + fp);
  const k = Number(ex) - fp.length + 2; // value * 100 = digits * 10^k
  let n: bigint;
  if (k >= 0) n = digits * 10n ** BigInt(k);
  else {
    const d = 10n ** BigInt(-k);
    n = digits / d;
    const r2 = (digits % d) * 2n;
    if (r2 > d || (r2 === d && n % 2n === 1n)) n += 1n;
  }
  const t = n.toString().padStart(3, "0");
  return Number(`${sign}${t.slice(0, -2)}.${t.slice(-2)}`) || 0;
}

/** Price one type from its sell orders; null when no order has at least min_units units. */
export function priceOrders(orders: readonly Order[], rule: RuleParams = DEFAULT_RULE): TypePrice | null {
  const sells = orders.filter((o) => !o.is_buy_order);
  const kept = sells
    .filter((o) => o.volume_remain >= rule.min_units && o.price > 0 && Number.isFinite(o.price))
    // fixed summation order: the result must not depend on the order the source delivered the orders in
    .sort((a, b) => a.price - b.price || a.volume_remain - b.volume_remain);
  if (!kept.length) return null;
  const p0 = kept[0].price;
  const band_max = trim(p0 * (1 + rule.band));
  let units = 0;
  let isk = 0;
  let n = 0;
  let units_considered = 0;
  for (const o of kept) {
    units_considered += o.volume_remain;
    // docs/22 §4.5: band_max (12 significant digits) is the inclusive edge; the order price is compared as given
    if (o.price <= band_max) {
      units += o.volume_remain;
      isk += o.price * o.volume_remain;
      n++;
    }
  }
  // the average lies in [p0, highest band price]; rounding can only cross an edge for sub-cent prices: clamp
  const price = Math.min(Math.max(roundIsk(isk / units), p0), band_max);
  return { price, p0, band_max, units, orders: n, units_considered, orders_considered: kept.length, orders_total: sells.length };
}

/** Group orders by type and price each type. Types without a surviving order are returned in `missing`. */
export function priceAll(orders: Iterable<Order>, rule: RuleParams = DEFAULT_RULE): { prices: Map<number, TypePrice>; missing: number[] } {
  const by = new Map<number, Order[]>();
  for (const o of orders) {
    if (o.is_buy_order) continue;
    let a = by.get(o.type_id);
    if (!a) by.set(o.type_id, (a = []));
    a.push(o);
  }
  const prices = new Map<number, TypePrice>();
  const missing: number[] = [];
  for (const [t, os] of [...by].sort((a, b) => a[0] - b[0])) {
    const p = priceOrders(os, rule);
    if (p) prices.set(t, p);
    else missing.push(t);
  }
  return { prices, missing };
}

/** docs/22 §3.2 rule descriptor as written in a snapshot (`rule`) or handed to the `rule` CLI command */
export interface RuleSpec {
  name?: string;
  version?: number;
  order_side?: string;
  location_id?: number;
  min_units?: number;
  band?: number;
  weighting?: string;
}

/**
 * Apply a full rule descriptor to one type's raw order book (the `eve-market-prices rule` command and the bench
 * d22/price_rule transport): checks name / version / side / weighting, keeps the sell orders at `location_id` (when
 * given), then runs priceOrders. Returns the §4.5 entry or null (the type would be `missing`).
 */
export function applyRule(input: { rule?: RuleSpec; orders?: readonly Order[] }): TypePrice | null {
  const r = input.rule ?? {};
  if (r.name !== undefined && r.name !== RULE_NAME) throw new Error(`unknown rule '${r.name}' (only ${RULE_NAME})`);
  if (r.version !== undefined && r.version !== RULE_VERSION) throw new Error(`unsupported rule version ${r.version} (only ${RULE_VERSION})`);
  if (r.order_side !== undefined && r.order_side !== "sell") throw new Error(`order_side must be 'sell' (got ${r.order_side})`);
  if (r.weighting !== undefined && r.weighting !== "units") throw new Error(`weighting must be 'units' (got ${r.weighting})`);
  const params = validateRule({ min_units: r.min_units, band: r.band });
  const orders = (input.orders ?? []).filter((o) => r.location_id === undefined || o.location_id === r.location_id);
  return priceOrders(orders, params);
}
