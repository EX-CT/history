// Library entry (Node + browser): rule, snapshot format, sources. Node-only helpers (file cache, dataset reader,
// snapshot runner) are in "eve-market-prices/node".
export * from "./rule.js";
export * from "./canonical.js";
export * from "./snapshot.js";
export * from "./sources/index.js";
export const VERSION = "0.1.0";
