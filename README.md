# eve-market-prices

Standalone EVE Online market price snapshot producer (Jita 4-4 sell orders, pluggable sources: ESI, Fuzzwork).
Snapshot format: `eve-price-snapshot` v1 per EX-CT/eve-fit-docs docs/22 §4. Engines embed one snapshot per release and
accept injected snapshots at run time; the engine (not this tool) applies prices and overrides.

**Status: work in progress** (see branch `wip/docs22-schema`).

License: MIT.
