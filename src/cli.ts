#!/usr/bin/env node
// eve-market-prices CLI: make, validate and query price snapshots.
import { readFileSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { DEFAULT_RULE, parseSnapshot, priceOf, serializeSnapshot, VERSION, SOURCES } from "./index.js";
import { makeSnapshot, readDataset } from "./node.js";

const USAGE = `eve-market-prices ${VERSION}

usage:
  eve-market-prices snapshot [--source esi|fuzzwork] [--out FILE] [options]
  eve-market-prices validate FILE
  eve-market-prices price FILE TYPE_ID...

snapshot options:
  --source ID          price source: ${Object.keys(SOURCES).join(", ")} (default esi)
  --min-units N        ignore sell orders with fewer than N units remaining (default ${DEFAULT_RULE.min_units})
  --band X             average the sell orders priced within p0 * (1 + X) (default ${DEFAULT_RULE.band})
  --types IDS          comma-separated type ids to price (default: every type the source has; fuzzwork needs a list)
  --types-file FILE    type ids, one per line / comma separated
  --dataset FILE       eve-sde-pipeline dataset-<build>.json[.gz]: price its marketable types, record coverage
  --dataset-name S     label for the dataset in the snapshot (e.g. "eve-sde-pipeline sde-3569502-r5")
  --contact S          contact for the User-Agent (ESI asks for one), e.g. an e-mail or "EVE: <character>"
  --cache-dir DIR      keep ETag / Expires between runs (default: no cache)
  --generated-at ISO   fix the timestamp (reproducible output)
  --region ID --location ID   ESI region / station (default 10000002 / 60003760, Jita 4-4)
  --station ID         Fuzzwork station (default 60003760)
  --quiet              no progress on stderr
`;

async function main(argv: string[]) {
  const [cmd, ...rest] = argv;
  if (!cmd || cmd === "-h" || cmd === "--help") return void process.stdout.write(USAGE);
  if (cmd === "--version") return void process.stdout.write(VERSION + "\n");
  if (cmd === "validate") {
    if (!rest[0]) throw new Error("validate FILE");
    const s = parseSnapshot(readFileSync(rest[0], "utf8"));
    const again = serializeSnapshot(s);
    const canonical = again === readFileSync(rest[0], "utf8");
    process.stdout.write(`${rest[0]}: ok (${s.source.id}, ${Object.keys(s.prices).length} prices, generated ${s.generated_at}, canonical: ${canonical})\n`);
    return;
  }
  if (cmd === "price") {
    const [file, ...ids] = rest;
    const s = parseSnapshot(readFileSync(file, "utf8"));
    for (const id of ids) process.stdout.write(`${id}\t${priceOf(s, Number(id)) ?? "-"}\n`);
    return;
  }
  if (cmd !== "snapshot") throw new Error(`unknown command '${cmd}'\n\n${USAGE}`);
  const { values: v } = parseArgs({
    args: rest,
    options: {
      source: { type: "string", default: "esi" },
      out: { type: "string" },
      "min-units": { type: "string" },
      band: { type: "string" },
      types: { type: "string" },
      "types-file": { type: "string" },
      dataset: { type: "string" },
      "dataset-name": { type: "string" },
      contact: { type: "string" },
      "cache-dir": { type: "string" },
      "generated-at": { type: "string" },
      region: { type: "string" },
      location: { type: "string" },
      station: { type: "string" },
      quiet: { type: "boolean", default: false },
    },
  });
  const ids = (s: string) => s.split(/[\s,]+/).filter(Boolean).map((x) => {
    const n = Number(x);
    if (!Number.isInteger(n) || n <= 0) throw new Error(`bad type id '${x}'`);
    return n;
  });
  const types = v.types ? ids(v.types) : v["types-file"] ? ids(readFileSync(v["types-file"], "utf8")) : null;
  const log = v.quiet ? undefined : (m: string) => process.stderr.write(m + "\n");
  const so: Record<string, unknown> = {};
  if (v.region) so.region_id = Number(v.region);
  if (v.location) so.location_id = Number(v.location);
  if (v.station) so.station = Number(v.station);
  const snap = await makeSnapshot({
    source: v.source!,
    rule: { ...(v["min-units"] !== undefined ? { min_units: Number(v["min-units"]) } : {}), ...(v.band !== undefined ? { band: Number(v.band) } : {}) },
    types,
    dataset: v.dataset ? readDataset(v.dataset, v["dataset-name"] ?? null) : null,
    generated_at: v["generated-at"],
    contact: v.contact ?? process.env.EVE_MARKET_PRICES_CONTACT ?? null,
    cache_dir: v["cache-dir"] ?? null,
    source_options: so,
    log,
  });
  const text = serializeSnapshot(snap);
  if (v.out) writeFileSync(v.out, text);
  else process.stdout.write(text);
  log?.(`${snap.source.id}: ${snap.coverage.types_priced} types priced, ${snap.coverage.types_unpriced.length} unpriced${snap.coverage.types_requested !== null ? ` of ${snap.coverage.types_requested} requested` : ""}; data as of ${snap.data_as_of ?? "?"}`);
}

main(process.argv.slice(2)).catch((e) => {
  process.stderr.write(`eve-market-prices: ${e instanceof Error ? e.message : e}\n`);
  process.exit(1);
});
