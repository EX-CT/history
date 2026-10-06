// Pyfa's built-in damage patterns and target profiles, opt-in. The data comes from Pyfa (GPL-3.0) via
// eve-sde-pipeline's separate copyleft asset presets-pyfa-LGPL-GPL.json; CI deploys a slimmed copy next to the site
// (tools/slim-presets-pyfa.mjs), it is not part of this MIT repository, and the site only fetches it when the user
// turns it on (Profiles). Ids are 'pyfa:<Pyfa id>'.
import type { DamagePattern, TargetProfile } from '../fit/model';

export const PYFA_PRESETS_URL = `${import.meta.env?.BASE_URL ?? '/'}data/presets-pyfa-LGPL-GPL.json`;
export const PYFA_PRESETS_KEY = 'eve-fit-web-pyfa-presets';

export interface PyfaPresets { damage: DamagePattern[]; targets: TargetProfile[]; attribution: string; notice: string }

/** Damage share in percent, 0.1 % steps (the engine uses the ratio). */
const pct = (x: number) => Math.round(x * 1000) / 10;

export function pyfaPresetsFrom(p: any): PyfaPresets {
  if (p?.format !== 'eve-fit-web-presets-pyfa') throw new Error('not an eve-fit-web Pyfa presets file');
  return {
    attribution: String(p.attribution ?? ''), notice: String(p.notice ?? ''),
    damage: (p.damage ?? []).map((d: any) => ({ id: `pyfa:${d.pyfa_id}`, name: d.name, em: pct(d.ratio[0]), thermal: pct(d.ratio[1]), kinetic: pct(d.ratio[2]), explosive: pct(d.ratio[3]), builtin: true })),
    targets: (p.targets ?? []).map((t: any) => ({ id: `pyfa:${t.pyfa_id}`, name: t.name, em: t.em, thermal: t.thermal, kinetic: t.kinetic, explosive: t.explosive,
      signature_radius: t.signature_radius ?? null, max_velocity: t.max_velocity ?? null, radius: t.radius ?? null, builtin: true })),
  };
}

let cache: Promise<PyfaPresets> | null = null;
export function loadPyfaPresets(url = PYFA_PRESETS_URL): Promise<PyfaPresets> {
  return (cache ??= fetch(url).then((r) => { if (!r.ok) throw new Error(`Pyfa presets: HTTP ${r.status}`); return r.json(); }).then(pyfaPresetsFrom)
    .catch((e) => { cache = null; throw e; }));
}
export const pyfaPresetsOn = () => { try { return localStorage.getItem(PYFA_PRESETS_KEY) === '1'; } catch { return false; } };
export const setPyfaPresetsOn = (on: boolean) => { try { localStorage.setItem(PYFA_PRESETS_KEY, on ? '1' : '0'); } catch { /* ignore */ } };
