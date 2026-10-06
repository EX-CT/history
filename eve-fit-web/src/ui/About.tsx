// About / engine page: which engine computes the numbers, exact versions of engines, dataset and site, and repo links.
import type { Dataset } from '../data/dataset';
import { BACKENDS, type EngineConfig, type FitStats } from '../engine/adapter';
import { DEFAULT_BACKEND } from '../engine/defaults';
import { formatsStatus } from '../formats';
import { t } from '../i18n';

export interface BuildInfo { dataset_tag?: string; engine_d?: string; engine_f?: string; engine_f_repo?: string; engine_f_dir?: string; engine_j?: string; engine_j_repo?: string; engine_j_dir?: string; web?: string; built_at?: string; run?: string; default_engine?: string; prices_snapshot?: string }

const GH = 'https://github.com/EX-CT';
const commit = (repo: string, sha?: string) => (sha ? <a href={`${GH}/${repo}/commit/${sha}`}><code>{sha}</code></a> : <span className="muted">n/a</span>);
const local = (iso?: string) => (iso ? new Date(iso).toLocaleString(undefined, { hour12: false, timeZoneName: 'short' }) : '—');

export function About({ cfg, status, st, ds, build, graphBackend }: { cfg: EngineConfig; status: string; st: FitStats | null; ds: Dataset; build: BuildInfo | null; graphBackend?: string | null }) {
  const be = BACKENDS.find((b) => b.id === cfg.backend);
  const raw: any = ds.raw;
  const rows: [string, React.ReactNode][] = [
    [t('Engine backend'), <><code className="about-backend">{cfg.backend}</code> {be?.label}{cfg.backend === 'http' ? <> · <code>{cfg.httpUrl}</code></> : null}</>],
    [t('Engine status'), <span className="about-status">{status}</span>],
    [t('Engine (reported)'), <span className="about-engine">{st?.meta?.engine ?? '—'}{st?.meta?.sde_build ? ` · SDE ${st.meta.sde_build}` : ''}</span>],
    [t('Provenance (engine)'), <span className="about-prov">{st?.provenance ? <>SDE {st.provenance.sde_build}{st.provenance.sde_revision ? ` r${st.provenance.sde_revision}` : ''} ({st.provenance.sde_source ?? '?'}) · <code title={st.provenance.sde_hash}>{String(st.provenance.sde_hash ?? '').slice(0, 19)}</code>
      {' · '}{t('prices')}: {st.provenance.price_source ?? '—'}{st.provenance.price_snapshot_id ? ` ${st.provenance.price_snapshot_id}` : ''} · {local(st.provenance.snapshot_time)}</> : t('not reported by this engine')}</span>],
    [t('Graphs computed by'), <span className="about-graphs">{graphBackend ? <><code>{graphBackend}</code>{graphBackend !== cfg.backend ? ` (${t('graph RPC fallback; fit stats from')} ${cfg.backend})` : ''}</> : t('UI approximation (backend has no graph RPC)')}</span>],
    [t('Fit formats'), <span className="about-formats" data-provider={formatsStatus().provider}>{formatsStatus().provider === 'eve-fit-formats'
      ? <>eve-fit-formats (WASM) · {commit((build?.engine_f_repo ?? 'EX-CT/eve-dogma').replace('EX-CT/', ''), build?.engine_f)} (crate eve-fit-formats-wasm)</>
      : <>{formatsStatus().label}{formatsStatus().note ? ` · ${formatsStatus().note}` : ''}</>}</span>],
    [t('Default backend'), <code>{build?.default_engine || DEFAULT_BACKEND}</code>],
    [t('Engine F (mainline; Rust → WASM, stats + graphs)'), <>{commit((build?.engine_f_repo ?? 'EX-CT/eve-dogma').replace('EX-CT/', ''), build?.engine_f)} · <a href={`https://github.com/${build?.engine_f_repo ?? 'EX-CT/eve-dogma'}/tree/${build?.engine_f ?? 'main'}/${build?.engine_f_dir ?? ''}`}>{(build?.engine_f_repo ?? 'eve-dogma').replace('EX-CT/', '')}{build?.engine_f_dir ? `/${build.engine_f_dir}` : ''}</a> (crate eve-wasm) · LGPL-3.0-or-later</>],
    [t('Engine J (C++20 → WASM, optional speed reference)'), <>{commit((build?.engine_j_repo ?? 'EX-CT/eve-dogma-lab').replace('EX-CT/', ''), build?.engine_j)} · <a href={`https://github.com/${build?.engine_j_repo ?? 'EX-CT/eve-dogma-lab'}/tree/${build?.engine_j ?? 'variant-j'}/${build?.engine_j_dir ?? ''}`}>{(build?.engine_j_repo ?? 'eve-dogma-lab').replace('EX-CT/', '')}{build?.engine_j_dir ? `/${build.engine_j_dir}` : ''}</a> · LGPL-3.0-or-later</>],
    [t('Engine D (TypeScript)'), <>{commit('eve-dogma-lab', build?.engine_d)} · <a href={`${GH}/eve-dogma-lab/tree/variant-d`}>variant-d</a></>],
    [t('Dataset'), <span className="about-dataset">SDE {raw.sde?.build} ({raw.sde?.release_date?.slice(0, 10)}) · r{raw.dataset_revision ?? 1} · {raw.generator}
      {build?.dataset_tag ? <> · <a href={`${GH}/eve-sde-pipeline/releases/tag/${build.dataset_tag}`}>{build.dataset_tag}</a></> : null}</span>],
    [t('Price snapshot for "update prices"'), <span className="about-prices">{build?.prices_snapshot ? <a href={`${GH}/eve-market-prices/releases/tag/${build.prices_snapshot}`}>{build.prices_snapshot}</a> : '—'}</span>],
    [t('Site build'), <>{commit('eve-fit-web', build?.web)} · {local(build?.built_at)}{build?.run ? <> · <a href={build.run}>{t('CI run')}</a></> : null}</>],
  ];
  return (
    <div className="about">
      <h4>{t('About this site')}</h4>
      <table className="grid small"><tbody>{rows.map(([k, v]) => <tr key={k}><th>{k}</th><td>{v}</td></tr>)}</tbody></table>
      <h4>{t('Repositories')}</h4>
      <ul className="about-links">
        <li><a href={`${GH}/eve-fit-web`}>eve-fit-web</a> — {t('this web UI')}</li>
        <li><a href={`${GH}/eve-dogma-rs`}>eve-dogma-rs</a> — {t('reference engine (Rust)')}</li>
        <li><a href={`${GH}/eve-dogma`}>eve-dogma</a> — {t('mainline engine (Rust, F)')}</li>
        <li><a href={`${GH}/eve-dogma-lab`}>eve-dogma-lab</a> — {t('engine variants')}</li>
        <li><a href={`${GH}/eve-dogma-bench`}>eve-dogma-bench</a> — {t('correctness / speed bench vs Pyfa')}</li>
        <li><a href={`${GH}/eve-sde-pipeline`}>eve-sde-pipeline</a> — {t('SDE dataset and presets')}</li>
        <li><a href={`${GH}/eve-fit-mcp`}>eve-fit-mcp</a> — {t('MCP server for AI agents')}</li>
        <li><a href={`${GH}/eve-fit-docs`}>eve-fit-docs</a> — {t('design docs and licensing')}</li>
      </ul>
      <p className="muted small">{t('EVE Online data © CCP hf.')} {t('Engines: LGPL-3.0-or-later; this site: MIT.')} <a href={`${GH}/eve-fit-docs/blob/main/LICENSING.md`}>LICENSING.md</a></p>
    </div>
  );
}
