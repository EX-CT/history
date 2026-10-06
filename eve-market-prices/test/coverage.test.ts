// docs/22 type coverage (decision 14:56): every published type with a market group from CCP's SDE (JSONL zip or
// types.jsonl), recorded in `coverage`.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { deflateRawSync } from "node:zlib";
import { readCcpSde, unzipEntry } from "../src/node.js";

/** tiny zip writer for fixtures (CRC not checked by the reader, written as 0) */
function zip(files: Record<string, string>, deflate = true): Buffer {
  const locals: Buffer[] = [];
  const central: Buffer[] = [];
  let off = 0;
  for (const [name, text] of Object.entries(files)) {
    const raw = Buffer.from(text, "utf8");
    const data = deflate ? deflateRawSync(raw) : raw;
    const n = Buffer.from(name, "utf8");
    const lh = Buffer.alloc(30);
    lh.writeUInt32LE(0x04034b50, 0); lh.writeUInt16LE(20, 4); lh.writeUInt16LE(deflate ? 8 : 0, 8);
    lh.writeUInt32LE(data.length, 18); lh.writeUInt32LE(raw.length, 22); lh.writeUInt16LE(n.length, 26);
    const ch = Buffer.alloc(46);
    ch.writeUInt32LE(0x02014b50, 0); ch.writeUInt16LE(20, 4); ch.writeUInt16LE(20, 6); ch.writeUInt16LE(deflate ? 8 : 0, 10);
    ch.writeUInt32LE(data.length, 20); ch.writeUInt32LE(raw.length, 24); ch.writeUInt16LE(n.length, 28); ch.writeUInt32LE(off, 42);
    locals.push(lh, n, data);
    central.push(ch, n);
    off += 30 + n.length + data.length;
  }
  const cd = Buffer.concat(central);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(central.length / 2, 8); end.writeUInt16LE(central.length / 2, 10);
  end.writeUInt32LE(cd.length, 12); end.writeUInt32LE(off, 16);
  return Buffer.concat([...locals, cd, end]);
}

const TYPES = [
  { _key: 0, groupID: 0, published: false, name: { en: "#System" } },
  { _key: 34, groupID: 18, marketGroupID: 1857, published: true, name: { en: "Tritanium" } },
  { _key: 587, groupID: 25, marketGroupID: 64, published: true, name: { en: "Rifter" } },
  { _key: 588, groupID: 25, published: true, name: { en: "Reaper" } },
  { _key: 9999, groupID: 25, marketGroupID: 64, published: false, name: { en: "unpublished" } },
  { _key: 2048, groupID: 60, marketGroupID: 615, published: true, name: { en: "Damage Control II" } },
].map((t) => JSON.stringify(t)).join("\n") + "\n";

test("readCcpSde: CCP JSONL zip -> published types with a market group, sde_build from _sde.jsonl, file sha256", () => {
  const dir = mkdtempSync(join(tmpdir(), "emp-cov-"));
  for (const deflate of [true, false]) {
    const z = zip({ "marketGroups.jsonl": "{}\n", "types.jsonl": TYPES, "_sde.jsonl": '{"_key": "sde", "buildNumber": 3569502, "releaseDate": "2026-10-02T11:08:57Z"}\n' }, deflate);
    const f = join(dir, `eve-online-static-data-3569502-jsonl-${deflate}.zip`);
    writeFileSync(f, z);
    const d = readCcpSde(f);
    assert.deepEqual(d.types, [34, 587, 2048]);
    assert.equal(d.sde_build, 3569502);
    assert.equal(d.sha256, createHash("sha256").update(z).digest("hex"));
    assert.equal(d.name, `CCP SDE 3569502 (eve-online-static-data-3569502-jsonl-${deflate}.zip)`);
    assert.equal(unzipEntry(z, "nope.jsonl"), null);
  }
  const j = join(dir, "types.jsonl");
  writeFileSync(j, TYPES);
  const t = readCcpSde(j, "label");
  assert.deepEqual([t.types, t.sde_build, t.name], [[34, 587, 2048], null, "label"]);
  writeFileSync(join(dir, "bad.zip"), zip({ "other.jsonl": "{}\n" }));
  assert.throws(() => readCcpSde(join(dir, "bad.zip")), /no types.jsonl/);
});
