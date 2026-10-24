import { test } from "node:test";
import assert from "node:assert/strict";
import { destination } from "../redirect.mjs";
const root = "https://amaljithkuttamath.github.io/radar/";
test("latest and old section links reach the canonical briefing", () => {
  for (const hash of ["", "#briefing/latest", "#briefing/latest/action-items", "#status", "#https://evil.example"])
    assert.equal(destination(hash), root + "#briefing");
});
test("archives, evidence, and dated edition links keep their destination", () => {
  assert.equal(destination("#archive"), root + "#archive");
  assert.equal(destination("#evidence"), root + "#evidence");
  assert.equal(destination("#briefing/2026-10-23/action-items"), root + "#briefing/2026-10-23");
});
test("invalid or hostile dates cannot change the origin", () => {
  for (const date of ["2026-02-30", "2026-99-01", "//evil.example", "<script>"])
    assert.equal(destination("#briefing/" + date), root + "#briefing");
});
