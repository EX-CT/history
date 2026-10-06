// Node-only helpers: on-disk HTTP cache (ETag / Expires survive between runs), type universes for coverage (CCP SDE
// types.jsonl / its jsonl zip, docs/22 decision 14:56; eve-sde-pipeline dataset), and makeSnapshot (source -> snapshot).
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { basename, join } from "node:path";
import { gunzipSync, gzipSync, inflateRawSync } from "node:zlib";
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

/** Read one member of a zip archive (stored or deflate; no zip64, no encryption). Minimal, no dependencies. */
export function unzipEntry(zip: Buffer, name: string): Buffer | null {
  let eocd = -1;
  for (let i = zip.length - 22; i >= Math.max(0, zip.length - 22 - 0xffff); i--) if (zip.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  if (eocd < 0) throw new Error("not a zip file (no end of central directory)");
  const count = zip.readUInt16LE(eocd + 10);
  let p = zip.readUInt32LE(eocd + 16);
  if (p === 0xffffffff) throw new Error("zip64 archives are not supported");
  for (let k = 0; k < count; k++) {
    if (zip.readUInt32LE(p) !== 0x02014b50) throw new Error("corrupt zip central directory");
    const method = zip.readUInt16LE(p + 10);
    const csize = zip.readUInt32LE(p + 20);
    const nlen = zip.readUInt16LE(p + 28), xlen = zip.readUInt16LE(p + 30), clen = zip.readUInt16LE(p + 32);
    const local = zip.readUInt32LE(p + 42);
    const n = zip.toString("utf8", p + 46, p + 46 + nlen);
    if (n === name) {
      if (zip.readUInt32LE(local) !== 0x04034b50) throw new Error("corrupt zip local header");
      const start = local + 30 + zip.readUInt16LE(local + 26) + zip.readUInt16LE(local + 28);
      const data = zip.subarray(start, start + csize);
      if (method === 0) return Buffer.from(data);
      if (method === 8) return inflateRawSync(data);
      throw new Error(`zip method ${method} not supported (${name})`);
    }
    p += 46 + nlen + xlen + clen;
  }
  return null;
}

/**
 * docs/22 type coverage (decision 2026-10-03 14:56): every **published type with a market group** in CCP's SDE.
 * `path` is CCP's JSONL SDE zip (eve-online-static-data-<build>-jsonl.zip from developers.eveonline.com; sde_build from
 * its _sde.jsonl) or a bare types.jsonl (then sde_build is null and must be passed). sha256 = of the given file.
 */
export function readCcpSde(path: string, name?: string | null): DatasetTypes {
  const raw = readFileSync(path);
  const sha256 = createHash("sha256").update(raw).digest("hex");
  let typesText: string;
  let sde_build: number | null = null;
  if (raw.readUInt32LE(0) === 0x04034b50) {
    const t = unzipEntry(raw, "types.jsonl");
    if (!t) throw new Error(`${path}: no types.jsonl in the zip (expected CCP's JSONL SDE)`);
    typesText = t.toString("utf8");
    const meta = unzipEntry(raw, "_sde.jsonl");
    if (meta) for (const l of meta.toString("utf8").split("\n")) if (l.trim()) { const m = JSON.parse(l); if (m._key === "sde" && Number.isInteger(m.buildNumber)) sde_build = m.buildNumber; }
  } else typesText = (path.endsWith(".gz") ? gunzipSync(raw) : raw).toString("utf8");
  const types: number[] = [];
  for (const l of typesText.split("\n")) {
    if (!l.trim()) continue;
    const t = JSON.parse(l);
    if (t.published === true && t.marketGroupID !== undefined && t.marketGroupID !== null) types.push(Number(t._key));
  }
  if (!types.length) throw new Error(`${path}: no published types with a market group (not a CCP types.jsonl?)`);
  types.sort((a, b) => a - b);
  return { name: name ?? `CCP SDE${sde_build ? " " + sde_build : ""} (${basename(path)})`, sha256, sde_build, types };
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
