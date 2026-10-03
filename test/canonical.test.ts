// RFC 8785 (JCS) vectors for canonicalJson, the content_hash serialisation (docs/22 §4.6). Expected strings are the
// RFC's own examples plus outputs of the independent Python `jcs` package (pip install jcs, 2026-10-03).
import assert from "node:assert/strict";
import { test } from "node:test";
import { canonicalJson } from "../src/canonical.js";
import { sha256Hex } from "../src/sha256.js";

test("JCS: RFC 8785 §3.2.2 example (numbers, string escapes, literals)", () => {
  const input = JSON.parse('{"numbers": [333333333.33333329, 1E30, 4.50, 2e-3, 0.000000000000000000000000001], "string": "\\u20ac$\\u000F\\u000aA\'\\u0042\\u0022\\u005c\\\\\\"\\/", "literals": [null, true, false]}');
  assert.equal(canonicalJson(input), '{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}');
});

test("JCS: RFC 8785 §3.2.3 key order by UTF-16 code units (not code points, not numeric)", () => {
  const o = JSON.parse('{"\\u20ac":"Euro Sign","\\r":"Carriage Return","\\ufb33":"Hebrew Letter Dalet With Dagesh","1":"One","\\ud83d\\ude00":"Emoji: Grinning Face","\\u0080":"Control","\\u00f6":"Latin Small Letter O With Diaeresis"}');
  // (JSON.parse would reorder the integer-like key "1"; read the keys off the string)
  const keys = [...canonicalJson(o).matchAll(/"((?:[^"\\]|\\.)*)":/g)].map((m) => JSON.parse(`"${m[1]}"`) as string);
  assert.deepEqual(keys.map((k) => k.codePointAt(0)), [0x0d, 0x31, 0x80, 0xf6, 0x20ac, 0x1f600, 0xfb33]);
  assert.equal(canonicalJson({ "34": 1, "1000": 2, "587": 3 }), '{"1000":2,"34":1,"587":3}');
});

test("JCS: ECMAScript number form (RFC 8785 Appendix B samples)", () => {
  const cases: [number, string][] = [
    [0, "0"], [-0, "0"], [1240000, "1240000"], [1240000.0, "1240000"], [4988.83, "4988.83"], [1e21, "1e+21"],
    [1e20, "100000000000000000000"], [1e-7, "1e-7"], [0.000001, "0.000001"], [5e-324, "5e-324"],
    [1.7976931348623157e308, "1.7976931348623157e+308"], [9007199254740992, "9007199254740992"],
    [-9007199254740992, "-9007199254740992"], [295147905179352830000, "295147905179352830000"], [0.1 + 0.2, "0.30000000000000004"],
  ];
  for (const [v, s] of cases) assert.equal(canonicalJson(v), s, String(v));
  assert.throws(() => canonicalJson(NaN), /non-finite/);
  assert.throws(() => canonicalJson(Infinity), /non-finite/);
});

test("JCS: strings — control escapes lowercase, '/' and non-ASCII literal, lone surrogates rejected", () => {
  assert.equal(canonicalJson("\b\t\n\f\r\u0001\u001f/é€😀"), '"\\b\\t\\n\\f\\r\\u0001\\u001f/é€😀"');
  assert.throws(() => canonicalJson("\ud800"), /lone surrogate/);
  assert.throws(() => canonicalJson({ ["\udc00"]: 1 }), /lone surrogate/);
});

test("JCS: a snapshot-shaped object hashes like the Python jcs package", () => {
  const body = { types: { "34": { price: 4.99, p0: 4.9, band_max: 5.145, units: 1000000, orders: 3 }, "1000": { price: 1251234.56, p0: 1240000, band_max: 1302000, units: 412, orders: 9 } }, missing: [35], schema_version: 1 };
  const c = canonicalJson(body);
  assert.equal(c, '{"missing":[35],"schema_version":1,"types":{"1000":{"band_max":1302000,"orders":9,"p0":1240000,"price":1251234.56,"units":412},"34":{"band_max":5.145,"orders":3,"p0":4.9,"price":4.99,"units":1000000}}}');
  assert.equal(sha256Hex(c), "45a2d25a9f19cc6795751938e5528b87072a2daa7739e8d4a459b289c655a7e1");
});
