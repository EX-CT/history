import {describe, it, expect, vi, beforeEach} from 'vitest';
import {esiRequest, fetchSystem, fetchConstellation, fetchRegion} from './esi';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('esiRequest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls the correct URL with User-Agent header', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({test: true}),
    });

    await esiRequest('/universe/systems/30000142/');

    expect(mockFetch).toHaveBeenCalledWith(
      'https://esi.evetech.net/latest/universe/systems/30000142/',
      {headers: {'User-Agent': 'eve-incursions.de@lars.naurath@gmail.de'}}
    );
  });

  it('returns parsed JSON on success', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({system_id: 30000142, name: 'Jita'}),
    });

    const result = await esiRequest('/universe/systems/30000142/');
    expect(result).toEqual({system_id: 30000142, name: 'Jita'});
  });

  it('throws on non-2xx response', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    });

    await expect(esiRequest('/universe/systems/999999/')).rejects.toThrow('ESI request failed: 404 Not Found');
  });
});

describe('typed helpers', () => {
  beforeEach(() => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });
  });

  it('fetchSystem calls correct path', async () => {
    await fetchSystem(30000142);
    expect(mockFetch).toHaveBeenCalledWith(
      'https://esi.evetech.net/latest/universe/systems/30000142/',
      expect.any(Object)
    );
  });

  it('fetchConstellation calls correct path', async () => {
    await fetchConstellation(20000001);
    expect(mockFetch).toHaveBeenCalledWith(
      'https://esi.evetech.net/latest/universe/constellations/20000001/',
      expect.any(Object)
    );
  });

  it('fetchRegion calls correct path', async () => {
    await fetchRegion(10000001);
    expect(mockFetch).toHaveBeenCalledWith(
      'https://esi.evetech.net/latest/universe/regions/10000001/',
      expect.any(Object)
    );
  });
});
