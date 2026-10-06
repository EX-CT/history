import { describe, expect, it } from 'vitest';
import { canonicalBackend } from './defaults';
import { createEngine, GRAPH_FALLBACK } from './adapter';

describe('engine defaults', () => {
  it('web.unit.backend-aliases: the retired wasm-g4-worker maps to wasm-worker; unknown ids pass through', () => {
    expect(canonicalBackend('wasm-g4-worker')).toBe('wasm-worker');
    expect(canonicalBackend('ts-worker')).toBe('ts-worker');
  });
  it('web.unit.graph-fallback: only J borrows F graphs', () => {
    expect(GRAPH_FALLBACK).toEqual({ 'wasm-j-worker': 'wasm-worker' });
    expect(createEngine({ backend: 'http', httpUrl: 'http://x', datasetUrl: '', engineUrl: '', wasmUrl: '' }).info.id).toBe('http');
  });
});
