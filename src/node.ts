// Node-only helpers: on-disk HTTP cache (ETag / Expires survive between runs), eve-sde-pipeline dataset reader
// (the type universe for coverage), and makeSnapshot (source -> snapshot).
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { basename, join } from "node:path";
import { gunzipSync, gzipSync } from "node:zlib";
import { validateRule, type RuleParams } from "./rule.js";
import { buildSnapshot, parseSnapshot, serializeSnapshot, snapshotFileName, type Snapshot } from "./snapshot.js";
import { createSource, userAgent, type CacheEntry, type HttpCache, type HttpOptions } from "./sources/index.js";
import { VERSION } from "./index.js";

export class FileCache implements HttpCache {
  constructor(private readonly dir: string) {
    mkdirSync(dir, { recursive: true });
  }
  private file(k: string) {
    return join(this.dir, createHash("sha1").update(k).digest("hex") + ".json");
  }
  async get(k: string): Promise<CacheEntry | undefined> {
    const f = this.file(k);
    if (!existsSync(f)) return undefined;
    try {
      return JSON.parse(readFileSync(f, "utf8")) as CacheEntry;
    } catch {
      return undefined;
    }
  }
  async set(k: string, e: CacheEntry) {
    writeFileSync(this.file(k), JSON.stringify(e));
  }
}

export interface DatasetTypes {
  /** label recorded in coverage.dataset (default: the file name) */
  name: string;
  sha256: string;
  sde_build: number | null;
  types: number[];
}

/**
 * The marketable types of an eve-sde-pipeline dataset (dataset-<build>-r<rev>.json[.gz]): published types with a
 * market group, plus the dataset's sde_build (the snapshot's required `sde_build`).
 */
export function readDataset(path: string, name?: string | null): DatasetTypes {
  const raw = readFileSync(path);
  const sha256 = createHash("sha256").update(raw).digest("hex");
  const d = JSON.parse((path.endsWith(".gz") ? gunzipSync(raw) : raw).toString("utf8"));
  const types: number[] = [];
  for (const [id, t] of Object.entries<any>(d.types ?? {})) if (t.published && t.market_group !== null && t.market_group !== undefined) types.push(Number(id));
  types.sort((a, b) => a - b);
  return { name: name ?? basename(path), sha256, sde_build: d.sde?.build ?? null, types };
}

export interface MakeSnapshotOptions extends Partial<HttpOptions> {
  source: string;
  rule?: Partial<RuleParams>;
  types?: number[] | null;
  dataset?: DatasetTypes | null;
  /** required unless the dataset carries it */
  sde_build?: number | null;
  generated_at?: Date | string;
  contact?: string | null;
  cache_dir?: string | null;
  source_options?: Record<string, unknown>;
}

export async function makeSnapshot(o: MakeSnapshotOptions): Promise<Snapshot> {
  const rule = validateRule(o.rule ?? {});
  const sde_build = o.sde_build ?? o.dataset?.sde_build ?? null;
  if (!sde_build) throw new Error("sde_build is required (docs/22 §4.2): pass --dataset or --sde-build");
  const src = createSource(o.source, {
    userAgent: o.userAgent ?? userAgent(VERSION, o.contact),
    cache: o.cache ?? (o.cache_dir ? new FileCache(o.cache_dir) : undefined),
    fetch: o.fetch,
    log: o.log,
    sleep: o.sleep,
    now: o.now,
    ...(o.source_options ?? {}),
  });
  const types = o.types ?? o.dataset?.types ?? null;
  const result = await src.fetchPrices({ types, rule, log: o.log });
  if (types) {
    // coverage is relative to the requested universe: types the source returned that were not asked for are dropped
    const want = new Set(types);
    for (const t of [...result.prices.keys()]) if (!want.has(t)) result.prices.delete(t);
    result.missing = result.missing.filter((t) => want.has(t));
  }
  o.log?.(`${src.descriptor.kind}: ${JSON.stringify(result.stats)}`);
  return buildSnapshot({
    result,
    source: src.descriptor,
    rule,
    sde_build,
    generated_at: o.generated_at ?? new Date(o.now ? o.now() : Date.now()),
    updater: { name: "eve-market-prices", version: VERSION },
    coverage: { dataset: o.dataset?.name ?? null, dataset_sha256: o.dataset?.sha256 ?? null, types_requested: types ? new Set(types).size : null },
  });
}

/** Write `<dir>/prices-<market>-<time>.json` and `.json.gz` (gzip mtime 0, deterministic). Returns both paths. */
export function writeSnapshotFiles(s: Snapshot, dir: string): { json: string; gz: string } {
  mkdirSync(dir, { recursive: true });
  const json = join(dir, snapshotFileName(s));
  const text = serializeSnapshot(s);
  writeFileSync(json, text);
  writeFileSync(json + ".gz", gzipSync(Buffer.from(text, "utf8"), { level: 9 }));
  return { json, gz: json + ".gz" };
}

/** Read a snapshot file (.json or .json.gz) and check it like an engine would. */
export function readSnapshotFile(path: string): Snapshot {
  const raw = readFileSync(path);
  return parseSnapshot((path.endsWith(".gz") ? gunzipSync(raw) : raw).toString("utf8"));
}
