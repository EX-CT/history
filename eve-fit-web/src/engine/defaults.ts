// Default engine backend of the hosted site. To switch it (e.g. after an engine round), change the fallback below or
// set the repository variable DEFAULT_ENGINE (pages.yml passes it as VITE_DEFAULT_ENGINE). Users who never picked a
// backend themselves follow the new default; an explicit choice is kept. Mainline = F (wasm-worker); ts-worker stays
// selectable as the fallback.
export const DEFAULT_BACKEND: string = (import.meta.env.VITE_DEFAULT_ENGINE as string | undefined) || 'wasm-worker';

/** Retired backend ids still found in saved settings or old links → their replacement. */
export const LEGACY_BACKENDS: Record<string, string> = { 'wasm-g4-worker': 'wasm-worker' };
export const canonicalBackend = (id: string): string => LEGACY_BACKENDS[id] ?? id;
