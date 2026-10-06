// Web Worker hosting an in-browser engine so calculations never block the UI.
//  kind 'ts':   variant D bundle (ES module exporting loadDatasetUrl + calc), dataset fetched from datasetUrl.
//  kind 'wasm': variant F wasm32-unknown-unknown module with C-ABI exports alloc/dealloc/calc (data compiled in);
//               an `rpc` export (variant F: methods graph / graph_specs) is used for engine-computed graphs.
//  kind 'emjs': Emscripten ES module (variant J: createEvej(), C functions evej_open / evej_calc / evej_rpc via cwrap);
//               the dataset (.json.gz) is fetched and written to the module's virtual FS, then opened.
/// <reference lib="webworker" />

type CalcFn = (req: unknown) => unknown;
let calcFn: CalcFn | null = null;
/** The full engine RPC response ({id, result} or {id, error}) for any method (batch, prices_load, ...); WASM backends. */
let rpcRawFn: ((method: string, params: unknown) => any) | null = null;
/** The same response as the engine's JSON text (number formatting as the engine wrote it; tools/browser-rpc.mjs). */
let rpcTextFn: ((method: string, params: unknown) => string) | null = null;
/** JSONL-style RPC ({id, method, params} -> {id, result}) when the module exports `rpc` (graph-capable builds). */
let rpcFn: ((method: string, params: unknown) => unknown) | null = null;

async function initTs(engineUrl: string, datasetUrl: string): Promise<string> {
  const mod: any = await import(/* @vite-ignore */ engineUrl);
  const ds = await mod.loadDatasetUrl(datasetUrl);
  calcFn = (req) => mod.calc(ds, req);
  rpcFn = typeof mod.rpc === 'function' ? (method, params) => mod.rpc(ds, method, params) : null;
  const m = mod.meta ? mod.meta(ds) : {};
  return `${m.engine ?? mod.ENGINE ?? 'eve-dogma-ts'} · SDE ${m.sde_build ?? '?'}`;
}

async function initEmjs(engineUrl: string, datasetUrl: string): Promise<string> {
  const mod: any = await import(/* @vite-ignore */ engineUrl);
  const create = mod.default ?? mod.createEvej;
  const M = await create({ locateFile: (f: string) => new URL(f, engineUrl).href });
  M.FS.writeFile('/dataset.json.gz', new Uint8Array(await (await fetch(datasetUrl)).arrayBuffer()));
  const err = M.ccall('evej_open', 'string', ['string'], ['/dataset.json.gz']);
  if (err) throw new Error(`evej_open: ${err}`);
  const calc = M.cwrap('evej_calc', 'string', ['string']);
  const rpc = M.cwrap('evej_rpc', 'string', ['string']);
  calcFn = (req) => JSON.parse(calc(JSON.stringify(req)));
  rpcTextFn = (method, params) => rpc(JSON.stringify({ id: 1, method, params }));
  rpcRawFn = (method, params) => JSON.parse(rpcTextFn!(method, params));
  rpcFn = (method, params) => { const r = rpcRawFn!(method, params); return r.result ?? r.error ?? null; };
  let label = 'eve-dogma-j (wasm)';
  try { const m: any = rpcFn('meta', {}); if (m?.engine) label = `${m.engine} (wasm) · SDE ${m.sde_build ?? '?'}`; } catch { /* ignore */ }
  return label;
}

async function initWasm(wasmUrl: string): Promise<string> {
  const { instance } = await WebAssembly.instantiateStreaming(fetch(wasmUrl), {}).catch(async () => {
    const buf = await (await fetch(wasmUrl)).arrayBuffer();
    return WebAssembly.instantiate(buf, {});
  });
  const x: any = instance.exports;
  const enc = new TextEncoder(), dec = new TextDecoder();
  const call = (fn: string, s: string) => {
    const inp = enc.encode(s);
    const p = x.alloc(inp.length);
    new Uint8Array(x.memory.buffer, p, inp.length).set(inp);
    const r: bigint = x[fn](p, inp.length);
    x.dealloc(p, inp.length);
    const op = Number(r >> 32n), ol = Number(r & 0xffffffffn);
    const out = dec.decode(new Uint8Array(x.memory.buffer, op, ol));
    x.dealloc(op, ol);
    return out;
  };
  calcFn = (req) => JSON.parse(call('calc', JSON.stringify(req)));
  rpcTextFn = typeof x.rpc === 'function' ? (method, params) => call('rpc', JSON.stringify({ id: 1, method, params })) : null;
  rpcRawFn = rpcTextFn ? (method, params) => JSON.parse(rpcTextFn!(method, params)) : null;
  rpcFn = rpcRawFn ? (method, params) => { const resp = rpcRawFn!(method, params); return resp.result ?? resp.error ?? null; } : null;
  let label = 'eve-wasm (F)';
  try { const probe: any = calcFn({ schema_version: 1, ship: { type_id: 587 } }); if (probe?.meta?.engine) label = `${probe.meta.engine} (wasm) · SDE ${probe.meta.sde_build}`; } catch { /* ignore */ }
  return label;
}

self.onmessage = async (ev: MessageEvent) => {
  const { id, op } = ev.data;
  try {
    if (op === 'init') {
      const r = ev.data.kind === 'wasm' ? await initWasm(ev.data.wasmUrl)
        : ev.data.kind === 'emjs' ? await initEmjs(ev.data.engineUrl, ev.data.datasetUrl) : await initTs(ev.data.engineUrl, ev.data.datasetUrl);
      (self as any).postMessage({ id, result: r });
    } else if (op === 'rpc') {
      if (!rpcFn) throw new Error('engine has no rpc export');
      (self as any).postMessage({ id, result: rpcFn(ev.data.method, ev.data.params) });
    } else if (op === 'rpc_text') {
      if (!rpcTextFn) throw new Error('engine has no rpc export');
      (self as any).postMessage({ id, result: rpcTextFn(ev.data.method, ev.data.params) });
    } else if (op === 'rpc_raw') {
      if (!rpcRawFn) throw new Error('engine has no rpc export');
      (self as any).postMessage({ id, result: rpcRawFn(ev.data.method, ev.data.params) });
    } else if (op === 'calc') {
      if (!calcFn) throw new Error('engine not initialised');
      (self as any).postMessage({ id, result: calcFn(ev.data.request) });
    }
  } catch (e) {
    (self as any).postMessage({ id, error: (e as Error)?.message ?? String(e) });
  }
};
