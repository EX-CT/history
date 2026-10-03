// Small HTTP helper shared by the sources: injectable fetch (mocks in tests), User-Agent, retries with backoff,
// an optional ETag / Expires cache, and ESI's error-limit headers (X-ESI-Error-Limit-Remain / -Reset).

export type FetchFn = (url: string, init?: { headers?: Record<string, string>; signal?: AbortSignal }) => Promise<{
  status: number;
  headers: { get(name: string): string | null };
  text(): Promise<string>;
}>;

export interface CacheEntry {
  etag: string | null;
  /** epoch ms; the entry may be served without a request until then */
  expires: number;
  last_modified: string | null;
  headers: Record<string, string>;
  body: string;
}

export interface HttpCache {
  get(key: string): Promise<CacheEntry | undefined>;
  set(key: string, e: CacheEntry): Promise<void>;
}

export class MemoryCache implements HttpCache {
  readonly map = new Map<string, CacheEntry>();
  async get(k: string) {
    return this.map.get(k);
  }
  async set(k: string, e: CacheEntry) {
    this.map.set(k, e);
  }
}

export interface HttpOptions {
  userAgent: string;
  fetch?: FetchFn;
  cache?: HttpCache;
  /** retries on network errors, 5xx, 429 and 420 (default 4) */
  retries?: number;
  /** pause before the next request when fewer errors than this are left in ESI's window (default 20) */
  errorLimitFloor?: number;
  /** injectable clock / sleep for tests */
  now?: () => number;
  sleep?: (ms: number) => Promise<void>;
  log?: (msg: string) => void;
}

export interface HttpResponse {
  status: number;
  body: string;
  headers: Record<string, string>;
  last_modified: string | null;
  fromCache: "fresh" | "revalidated" | false;
}

const HEADERS_KEPT = ["x-pages", "last-modified", "expires", "etag"];

export class HttpClient {
  readonly stats = { requests: 0, cache_fresh: 0, cache_revalidated: 0, retries: 0, error_limit_waits: 0 };
  private readonly f: FetchFn;
  private readonly now: () => number;
  private readonly sleep: (ms: number) => Promise<void>;
  /** ms epoch before which no request is sent (error-limit back-off) */
  private pauseUntil = 0;

  constructor(private readonly o: HttpOptions) {
    if (!o.userAgent || !/\S/.test(o.userAgent)) throw new Error("a User-Agent with contact information is required");
    this.f = o.fetch ?? (globalThis.fetch as unknown as FetchFn);
    this.now = o.now ?? Date.now;
    this.sleep = o.sleep ?? ((ms) => new Promise((r) => setTimeout(r, ms)));
  }

  /** GET with cache. `revalidate`: ignore a fresh entry's Expires and ask the server (If-None-Match). */
  async get(url: string, opts: { revalidate?: boolean; signal?: AbortSignal } = {}): Promise<HttpResponse> {
    const cached = await this.o.cache?.get(url);
    if (cached && !opts.revalidate && cached.expires > this.now()) {
      this.stats.cache_fresh++;
      return { status: 200, body: cached.body, headers: cached.headers, last_modified: cached.last_modified, fromCache: "fresh" };
    }
    const retries = this.o.retries ?? 4;
    for (let attempt = 0; ; attempt++) {
      const wait = this.pauseUntil - this.now();
      if (wait > 0) {
        this.stats.error_limit_waits++;
        this.o.log?.(`error limit low: waiting ${Math.ceil(wait / 1000)} s`);
        await this.sleep(wait);
      }
      const headers: Record<string, string> = { "User-Agent": this.o.userAgent, Accept: "application/json" };
      if (cached?.etag) headers["If-None-Match"] = cached.etag;
      let res: Awaited<ReturnType<FetchFn>> | undefined;
      let err: unknown;
      try {
        this.stats.requests++;
        res = await this.f(url, { headers, signal: opts.signal });
      } catch (e) {
        err = e;
      }
      if (res) this.noteErrorLimit(res.headers);
      const status = res?.status ?? 0;
      if (res && status === 304 && cached) {
        this.stats.cache_revalidated++;
        const e = { ...cached, expires: this.expiresOf(res.headers), headers: { ...cached.headers, ...pick(res.headers) } };
        await this.o.cache?.set(url, e);
        return { status: 200, body: e.body, headers: e.headers, last_modified: e.last_modified, fromCache: "revalidated" };
      }
      if (res && status >= 200 && status < 300) {
        const body = await res.text();
        const h = pick(res.headers);
        const e: CacheEntry = { etag: res.headers.get("etag"), expires: this.expiresOf(res.headers), last_modified: res.headers.get("last-modified"), headers: h, body };
        await this.o.cache?.set(url, e);
        return { status, body, headers: h, last_modified: e.last_modified, fromCache: false };
      }
      const retryable = !res || status >= 500 || status === 429 || status === 420;
      if (!retryable || attempt >= retries) {
        const text = res ? (await res.text()).slice(0, 300) : String(err);
        throw new Error(`GET ${url}: ${res ? `HTTP ${status}` : "network error"}: ${text}`);
      }
      this.stats.retries++;
      if (status === 420) this.pauseUntil = Math.max(this.pauseUntil, this.now() + this.resetMs(res!.headers, 60));
      const ra = Number(res?.headers.get("retry-after"));
      if (status === 429 && Number.isFinite(ra) && ra > 0) this.pauseUntil = Math.max(this.pauseUntil, this.now() + ra * 1000);
      const back = Math.min(30_000, 500 * 2 ** attempt);
      this.o.log?.(`GET ${url}: ${res ? `HTTP ${status}` : "network error"}, retry ${attempt + 1}/${retries} in ${back} ms`);
      await this.sleep(back);
    }
  }

  private expiresOf(h: { get(n: string): string | null }): number {
    const e = h.get("expires");
    const t = e ? Date.parse(e) : NaN;
    return Number.isFinite(t) ? t : 0;
  }

  private resetMs(h: { get(n: string): string | null }, dflt: number): number {
    const r = Number(h.get("x-esi-error-limit-reset"));
    return (Number.isFinite(r) && r >= 0 ? r : dflt) * 1000 + 1000;
  }

  private noteErrorLimit(h: { get(n: string): string | null }) {
    const remain = h.get("x-esi-error-limit-remain");
    if (remain === null) return;
    if (Number(remain) < (this.o.errorLimitFloor ?? 20)) this.pauseUntil = Math.max(this.pauseUntil, this.now() + this.resetMs(h, 60));
  }
}

function pick(h: { get(n: string): string | null }): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of HEADERS_KEPT) {
    const v = h.get(k);
    if (v !== null) out[k] = v;
  }
  return out;
}

export const DEFAULT_USER_AGENT = "eve-market-prices (+https://github.com/EX-CT/eve-market-prices)";

/** "<tool>/<version> (<contact>; +repo)": ESI asks for a way to reach the operator. */
export function userAgent(version: string, contact?: string | null): string {
  const c = contact && contact.trim() ? `${contact.trim()}; ` : "";
  return `eve-market-prices/${version} (${c}+https://github.com/EX-CT/eve-market-prices)`;
}
