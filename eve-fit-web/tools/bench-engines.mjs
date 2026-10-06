// In-browser head-to-head of the WASM engines F (wasm-worker) and J (wasm-j-worker) on one page, same fits:
//   node tools/bench-engines.mjs <site-url> <bench-dir> [runs=5] [reps=5]
// Each run starts a fresh headless Chrome (empty cache) and loads both engines on the same page in alternating order.
// Load phases: F = fetch .wasm, compile + instantiate (dataset is compiled in), first calc; J = import evej.mjs, fetch
// .wasm, compile + instantiate (via instantiateWasm), fetch dataset + write to the virtual FS + evej_open, first calc.
// Latency: every case of <bench-dir>/cases (bench 1.8.0 FitRequests), one warm-up call then `reps` timed calls per case
// (block mean; performance.now() is 0.1 ms-coarsened), in the page's main thread (the site runs the same code in a Web Worker). Prints JSON + a Markdown table.
import puppeteer from 'puppeteer-core';
import { readFileSync, readdirSync } from 'node:fs';
import { loadavg, cpus } from 'node:os';

const [url = 'http://127.0.0.1:4173/eve-fit-web/', benchDir = '/tmp/bench-180', runsArg = '5', repsArg = '5'] = process.argv.slice(2);
const runs = +runsArg, reps = +repsArg;
const caseFiles = readdirSync(`${benchDir}/cases`).filter((f) => f.endsWith('.json')).sort();
const reqs = caseFiles.map((f) => JSON.stringify(JSON.parse(readFileSync(`${benchDir}/cases/${f}`, 'utf8'))));
const base = new URL(url);

async function inPage(p, which, reqs, reps) {
  return p.evaluate(async (which, reqs, reps, baseHref) => {
    const now = () => performance.now();
    const u = (x) => new URL(x, baseHref).href;
    const t = {}; let calc;
    const t0 = now();
    if (which === 'F') {
      const bytes = await (await fetch(u('engines/f/eve_wasm.wasm'), { cache: 'no-store' })).arrayBuffer(); t.fetch = now() - t0;
      const t1 = now(); const { instance } = await WebAssembly.instantiate(bytes, {}); t.instantiate = now() - t1;
      const x = instance.exports, enc = new TextEncoder(), dec = new TextDecoder();
      calc = (s) => { const inp = enc.encode(s); const p = x.alloc(inp.length); new Uint8Array(x.memory.buffer, p, inp.length).set(inp);
        const r = x.calc(p, inp.length); x.dealloc(p, inp.length); const op = Number(r >> 32n), ol = Number(r & 0xffffffffn);
        const out = dec.decode(new Uint8Array(x.memory.buffer, op, ol)); x.dealloc(op, ol); return out; };
      t.dataset = 0; t.dataset_fetch = 0; t.dataset_open = 0; t.glue_import = 0;
    } else {
      const mod = await import(u('engines/j/evej.mjs')); t.glue_import = now() - t0;
      const tf = now(); const bytes = await (await fetch(u('engines/j/evej.wasm'), { cache: 'no-store' })).arrayBuffer(); t.fetch = now() - tf;
      const t1 = now();
      const M = await mod.default({ instantiateWasm: (imports, ok) => { WebAssembly.instantiate(bytes, imports).then((r) => ok(r.instance)); return {}; } });
      t.instantiate = now() - t1;
      const t2 = now();
      const gz = new Uint8Array(await (await fetch(u('data/dataset.json.gz'), { cache: 'no-store' })).arrayBuffer()); t.dataset_fetch = now() - t2;
      const t4 = now();
      M.FS.writeFile('/d.json.gz', gz);
      const e = M.ccall('evej_open', 'string', ['string'], ['/d.json.gz']); if (e) throw new Error(e);
      t.dataset_open = now() - t4; t.dataset = now() - t2;
      const c = M.cwrap('evej_calc', 'string', ['string']); calc = (s) => c(s);
    }
    const t3 = now(); const first = JSON.parse(calc(reqs[0])); t.first_calc = now() - t3; t.total = now() - t0;
    if (!first.meta && !first.ship) throw new Error('bad first response');
    // performance.now() is coarsened to 0.1 ms without cross-origin isolation, so time blocks of `reps` calls per case
    const per = [];
    for (const q of reqs) { calc(q); const a = now(); for (let r = 0; r < reps; r++) calc(q); per.push((now() - a) / reps); }
    const one = reqs.find((q) => q.includes('"type_id":587')) ?? reqs[0]; const rifter = [];
    for (let i = 0; i < 50; i++) { const a = now(); for (let k = 0; k < 20; k++) calc(one); rifter.push((now() - a) / 20); }
    return { t, per, rifter, engine: first.meta?.engine };
  }, which, reqs, reps, base.href);
}

const q = (xs, p) => { const s = [...xs].sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.floor(p * (s.length - 1)))]; };
const med = (xs) => q(xs, 0.5);
const res = { F: [], J: [] };
const load = [loadavg()[0]];
for (let r = 0; r < runs; r++) {
  const b = await puppeteer.launch({ executablePath: process.env.CHROME ?? '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
  const p = await b.newPage();
  await p.goto(`${url}?engine=ts-worker`, { waitUntil: 'domcontentloaded' });
  for (const w of r % 2 ? ['J', 'F'] : ['F', 'J']) res[w].push(await inPage(p, w, reqs, reps));
  await b.close();
  load.push(loadavg()[0]);
}
const sum = {};
for (const w of ['F', 'J']) {
  const rs = res[w], all = rs.flatMap((x) => x.per), rif = rs.flatMap((x) => x.rifter);
  const ph = (k) => med(rs.map((x) => x.t[k]));
  sum[w] = { engine: rs[0].engine, load_ms: { glue_import: ph('glue_import'), fetch: ph('fetch'), dataset_fetch: ph('dataset_fetch'), dataset_open: ph('dataset_open'), instantiate: ph('instantiate'), dataset: ph('dataset'), first_calc: ph('first_calc'), total: ph('total'),
    total_min: Math.min(...rs.map((x) => x.t.total)), total_max: Math.max(...rs.map((x) => x.t.total)) },
    corpus_ms: { n: all.length, median: med(all), p95: q(all, 0.95), mean: all.reduce((a, b) => a + b, 0) / all.length },
    rifter_ms: { n: rif.length, median: med(rif), p95: q(rif, 0.95) } };
}
const env = { runs, reps, cases: reqs.length, cpus: cpus().length, cpu: cpus()[0]?.model, loadavg_1m: load, chrome: 'headless', url };
console.log(JSON.stringify({ env, sum }, null, 1));
const f = (x) => x.toFixed(x < 10 ? 2 : 0);
console.log(`\n| | F | J |\n|---|---|---|`);
for (const [k, lab] of [['glue_import', 'import JS glue (ms)'], ['fetch', 'fetch .wasm (ms)'], ['instantiate', 'compile + instantiate (ms)'], ['dataset_fetch', 'dataset fetch (ms)'], ['dataset_open', 'dataset init (FS write + open) (ms)'], ['first_calc', 'first calc (ms)'], ['total', 'load total, median (ms)']])
  console.log(`| ${lab} | ${f(sum.F.load_ms[k])} | ${f(sum.J.load_ms[k])} |`);
console.log(`| load total, min–max (ms) | ${f(sum.F.load_ms.total_min)}–${f(sum.F.load_ms.total_max)} | ${f(sum.J.load_ms.total_min)}–${f(sum.J.load_ms.total_max)} |`);
console.log(`| calc, mean of ${reps} calls per fit, ${reqs.length} fits × ${runs} runs: median / p95 over fits (ms) | ${f(sum.F.corpus_ms.median)} / ${f(sum.F.corpus_ms.p95)} | ${f(sum.J.corpus_ms.median)} / ${f(sum.J.corpus_ms.p95)} |`);
console.log(`| calc, one Rifter, 50 blocks of 20 × ${runs}: median / p95 (ms) | ${f(sum.F.rifter_ms.median)} / ${f(sum.F.rifter_ms.p95)} | ${f(sum.J.rifter_ms.median)} / ${f(sum.J.rifter_ms.p95)} |`);
