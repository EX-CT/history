// Live smoke (network; non-gating in CI): a few types from ESI and Fuzzwork, checked like an engine would.
// node dist/test/live-smoke.js   (EVE_MARKET_PRICES_CONTACT sets the User-Agent contact)
import assert from "node:assert/strict";
import { parseSnapshot, serializeSnapshot } from "../src/index.js";
import { makeSnapshot } from "../src/node.js";

const types = [34, 35, 587, 2048, 2889, 12345678];
const contact = process.env.EVE_MARKET_PRICES_CONTACT ?? "https://github.com/EX-CT/eve-market-prices/issues";
for (const source of ["esi", "fuzzwork"]) {
  const s = await makeSnapshot({ source, types, sde_build: 3569502, contact, log: (m) => console.error(`[${source}] ${m}`) });
  parseSnapshot(serializeSnapshot(s));
  assert.ok(s.types["34"] && s.types["34"].price > 0, `${source}: Tritanium priced`);
  assert.ok(s.missing.includes(12345678), `${source}: bogus type missing`);
  console.log(`${source}: ${s.snapshot_id} ${s.type_count} types, missing ${s.missing}, Tritanium ${JSON.stringify(s.types["34"])}`);
}
