const USER_AGENT = 'eve-incursions.de@lars.naurath@gmail.de';
const BASE_URL = 'https://esi.evetech.net/latest';

export interface ESISystem {
  system_id: number;
  name: string;
  security_status: number;
  constellation_id: number;
}

export interface ESIConstellation {
  constellation_id: number;
  name: string;
  region_id: number;
  systems: number[];
}

export interface ESIRegion {
  region_id: number;
  name: string;
}

export async function esiRequest<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'User-Agent': USER_AGENT }
  });

  if (!res.ok) {
    throw new Error(`ESI request failed: ${res.status} ${res.statusText} for ${path}`);
  }

  return res.json() as Promise<T>;
}

export function fetchSystem(id: number) {
  return esiRequest<ESISystem>(`/universe/systems/${id}/`);
}

export function fetchConstellation(id: number) {
  return esiRequest<ESIConstellation>(`/universe/constellations/${id}/`);
}

export function fetchRegion(id: number) {
  return esiRequest<ESIRegion>(`/universe/regions/${id}/`);
}
