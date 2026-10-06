// Source registry: add a source by implementing Source (types.ts) and registering a factory here.
import { EsiSource, type EsiOptions } from "./esi.js";
import { FuzzworkSource, type FuzzworkOptions } from "./fuzzwork.js";
import type { HttpOptions } from "./http.js";
import type { Source } from "./types.js";

export type SourceFactory = (o: HttpOptions & Record<string, unknown>) => Source;

export const SOURCES: Record<string, SourceFactory> = {
  esi: (o) => new EsiSource(o as EsiOptions),
  fuzzwork: (o) => new FuzzworkSource(o as FuzzworkOptions),
};

export function registerSource(id: string, f: SourceFactory) {
  if (SOURCES[id]) throw new Error(`source '${id}' already registered`);
  SOURCES[id] = f;
}

export function createSource(id: string, o: HttpOptions & Record<string, unknown>): Source {
  const f = SOURCES[id];
  if (!f) throw new Error(`unknown source '${id}' (known: ${Object.keys(SOURCES).join(", ")})`);
  return f(o);
}

export * from "./types.js";
export * from "./http.js";
export * from "./esi.js";
export * from "./fuzzwork.js";
