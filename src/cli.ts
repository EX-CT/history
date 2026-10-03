#!/usr/bin/env node
// eve-market-prices CLI: make, validate and query price snapshots.
import { readFileSync, writeFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { parseArgs } from "node:util";
import { applyRule, DEFAULT_RULE, priceOf, serializeSnapshot, snapshotFileName, VERSION, SOURCES } from "./index.js";
import { makeSnapshot, readDataset, readSnapshotFile, writeSnapshotFiles } from "./node.js";

const USAGE = `eve-market-prices ${VERSION}

usage:
  eve-market-prices snapshot [--source esi|fuzzwork] [--out FILE | --out-dir DIR] [options]
  eve-market-prices validate FILE
  eve-market-prices price FILE TYPE_ID...
  eve-market-prices rule < {"rule": {...}, "orders": [ESI orders]}
      apply the pricing rule to one type's order book; prints the docs/22 §4.5 entry or null
      (rule: name jita_sell_band_weighted, version 1, order_side sell, location_id, min_units, band, weighting units;
      orders: ESI market orders; buy orders and orders at other locations are ignored)

snapshot options:
  --source ID          price source: ${Object.keys(SOURCES).join(", ")} (default esi)
  --min-units N        ignore sell orders with fewer than N units remaining (default ${DEFAULT_RULE.min_units})
  --band X             average the sell orders priced within p0 * (1 + X) (default ${DEFAULT_RULE.band})
  --types IDS          comma-separated type ids to price (default: every type the source has; fuzzwork needs a list)
  --types-file FILE    type ids, one per line / comma separated
  --dataset FILE       eve-sde-pipeline dataset-<build>.json[.gz]: price its marketable types, record coverage
  --dataset-name S     label for the dataset in the snapshot (default: the file name)
  --sde-build N        SDE build of the type list (required without --dataset; docs/22 sde_build)
  --out FILE           write the snapshot here (.json, or .json.gz for gzip); default stdout
  --out-dir DIR        write prices-<market>-<market_time>.json and .json.gz into DIR
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
    const s = readSnapshotFile(rest[0]);
    process.stdout.write(`${rest[0]}: ok ${s.snapshot_id} (${s.source.kind}, ${s.type_count} types, ${s.missing.length} missing, min_units ${s.rule.min_units}, band ${s.rule.band}, exact ${s.rule.exact}, ${s.content_hash})\n`);
    return;
  }
  if (cmd === "price") {
    const [file, ...ids] = rest;
    const s = readSnapshotFile(file);
    for (const id of ids) process.stdout.write(`${id}\t${priceOf(s, Number(id)) ?? "-"}\n`);
    return;
  }
  if (cmd === "rule") {
    const input = JSON.parse(readFileSync(0, "utf8"));
    process.stdout.write(JSON.stringify(applyRule(input)) + "\n");
    return;
  }
  if (cmd !== "snapshot") throw new Error(`unknown command '${cmd}'\n\n${USAGE}`);
  const { values: v } = parseArgs({
    args: rest,
    options: {
      source: { type: "string", default: "esi" },
      out: { type: "string" },
      "out-dir": { type: "string" },
      "sde-build": { type: "string" },
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
    sde_build: v["sde-build"] !== undefined ? Number(v["sde-build"]) : null,
    generated_at: v["generated-at"],
    contact: v.contact ?? process.env.EVE_MARKET_PRICES_CONTACT ?? null,
    cache_dir: v["cache-dir"] ?? null,
    source_options: so,
    log,
  });
  const text = serializeSnapshot(snap);
  if (v["out-dir"]) {
    const w = writeSnapshotFiles(snap, v["out-dir"]);
    log?.(`wrote ${w.json} and ${w.gz}`);
  } else if (v.out) writeFileSync(v.out, v.out.endsWith(".gz") ? gzipSync(Buffer.from(text, "utf8"), { level: 9 }) : text);
  else process.stdout.write(text);
  log?.(`${snap.snapshot_id} (${snapshotFileName(snap)}): ${snap.type_count} types priced, ${snap.missing.length} missing${snap.coverage?.types_requested != null ? ` of ${snap.coverage.types_requested} requested` : ""}; ${snap.content_hash}`);
}

main(process.argv.slice(2)).catch((e) => {
  process.stderr.write(`eve-market-prices: ${e instanceof Error ? e.message : e}\n`);
  process.exit(1);
});
