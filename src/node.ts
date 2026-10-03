// Node-only helpers: on-disk HTTP cache (ETag / Expires survive between runs), eve-sde-pipeline dataset reader
// (the type universe for coverage), and makeSnapshot (source -> snapshot).
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { gunzipSync } from "node:zlib";
import { validateRule, type RuleParams } from "./rule.js";
import { buildSnapshot, type DatasetRef, type Snapshot } from "./snapshot.js";
import { createSource, type CacheEntry, type HttpCache, type HttpOptions } from "./sources/index.js";
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

/**
 * The marketable types of an eve-sde-pipeline dataset (dataset-<build>.json[.gz]): published types with a market
 * group. Returns the dataset reference recorded in the snapshot's coverage.
 */
export function readDataset(path: string, name?: string | null): { ref: DatasetRef; types: number[] } {
  const raw = readFileSync(path);
  const sha256 = createHash("sha256").update(raw).digest("hex");
  const d = JSON.parse((path.endsWith(".gz") ? gunzipSync(raw) : raw).toString("utf8"));
  const types: number[] = [];
  for (const [id, t] of Object.entries<any>(d.types ?? {})) if (t.published && t.market_group !== null && t.market_group !== undefined) types.push(Number(id));
  types.sort((a, b) => a - b);
  return { ref: { name: name ?? null, sde_build: d.sde?.build ?? null, sha256 }, types };
}

export interface MakeSnapshotOptions extends Partial<HttpOptions> {
  source: string;
  rule?: Partial<RuleParams>;
  types?: number[] | null;
  dataset?: { ref: DatasetRef; types: number[] } | null;
  generated_at?: Date | string;
  contact?: string | null;
  cache_dir?: string | null;
  source_options?: Record<string, unknown>;
}

export async function makeSnapshot(o: MakeSnapshotOptions): Promise<Snapshot> {
  const rule = validateRule(o.rule ?? {});
  const contact = o.contact ? `${o.contact.trim()}; ` : "";
  const src = createSource(o.source, {
    userAgent: o.userAgent ?? `eve-market-prices/${VERSION} (${contact}+https://github.com/EX-CT/eve-market-prices)`,
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
    result.unpriced = result.unpriced.filter((t) => want.has(t));
  }
  return buildSnapshot({
    result,
    source: src.descriptor,
    generated_at: o.generated_at ?? new Date(),
    generator: { name: "eve-market-prices", version: VERSION },
    dataset: o.dataset?.ref ?? null,
    types_requested: types ? new Set(types).size : null,
  });
}
