// Slims eve-sde-pipeline's presets-pyfa-LGPL-GPL.json (release asset: Pyfa's built-in damage patterns and target
// profiles, data tables extracted from Pyfa; copyleft, kept separate from the MIT code) to what the web UI loads on
// request. The output keeps the file's notice and adds the attribution; it is deployed as its own file next to the
// site (never vendored in this repository) and only fetched when the user turns the Pyfa presets on.
//   node tools/slim-presets-pyfa.mjs presets-pyfa-LGPL-GPL.json public/data/presets-pyfa-LGPL-GPL.json
import { readFileSync, writeFileSync } from 'node:fs';

const [src, out] = process.argv.slice(2);
const p = JSON.parse(readFileSync(src, 'utf8'));
if (p.format !== 'exct-presets-pyfa') throw new Error(`${src}: not an exct-presets-pyfa file`);
const slim = {
  format: 'eve-fit-web-presets-pyfa', source: 'EX-CT/eve-sde-pipeline presets-pyfa-LGPL-GPL.json',
  notice: p.notice,
  attribution: 'Damage patterns and target profiles from Pyfa (https://github.com/pyfa-org/Pyfa), GPL-3.0; data only, no Pyfa code.',
  damage: p.damage_patterns.items.map((d) => ({ pyfa_id: d.pyfa_id, name: d.name, ratio: d.ratio })),
  targets: p.target_profiles.items.map((t) => ({ pyfa_id: t.pyfa_id, name: t.name, em: t.em, thermal: t.thermal, kinetic: t.kinetic, explosive: t.explosive,
    ...(t.signature_radius != null ? { signature_radius: t.signature_radius } : {}), ...(t.max_velocity != null ? { max_velocity: t.max_velocity } : {}), ...(t.radius != null ? { radius: t.radius } : {}) })),
};
writeFileSync(out, JSON.stringify(slim) + '\n');
console.log(`${out}: ${slim.damage.length} Pyfa damage patterns, ${slim.targets.length} target profiles`);
