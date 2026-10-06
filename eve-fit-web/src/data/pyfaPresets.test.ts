import { describe, expect, it } from 'vitest';
import { pyfaPresetsFrom } from './pyfaPresets';

describe('Pyfa presets (opt-in file)', () => {
  it('web.unit.pyfa-presets-map: Pyfa ratios become percent shares (0.1 % steps) with pyfa: ids; other files rejected', () => {
    // synthetic entries in the slimmed file's shape (tools/slim-presets-pyfa.mjs), not Pyfa data
    const p = pyfaPresetsFrom({ format: 'eve-fit-web-presets-pyfa', attribution: 'a', notice: 'n',
      damage: [{ pyfa_id: -7, name: '[Test]Mix', ratio: [0, 0.197814, 0.802186, 0] }],
      targets: [{ pyfa_id: -3, name: '[Test]T', em: 0.5, thermal: 0.25, kinetic: 0, explosive: 1, signature_radius: 40 }] });
    expect(p.damage).toEqual([{ id: 'pyfa:-7', name: '[Test]Mix', em: 0, thermal: 19.8, kinetic: 80.2, explosive: 0, builtin: true }]);
    expect(p.targets[0]).toEqual({ id: 'pyfa:-3', name: '[Test]T', em: 0.5, thermal: 0.25, kinetic: 0, explosive: 1, signature_radius: 40, max_velocity: null, radius: null, builtin: true });
    expect(() => pyfaPresetsFrom({ format: 'exct-presets-pyfa' })).toThrow(/Pyfa presets/);
  });
});
