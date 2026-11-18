import { test } from "node:test";
import assert from "node:assert/strict";
import {
  PAGE_SIZE,
  matchesQuery,
  cardMatches,
  pageOf,
  searchCountText,
} from "./asset-catalog.js";

function card(over = {}) {
  return { kind: "logo", status: "ready", text: "Major Blowhorn logo svg", ...over };
}

test("matchesQuery is a case-insensitive substring match, and empty matches all", () => {
  assert.equal(matchesQuery("Major Blowhorn logo", ""), true);
  assert.equal(matchesQuery("Major Blowhorn logo", "blowhorn"), true);
  assert.equal(matchesQuery("Major Blowhorn logo", "LOGO"), true);
  assert.equal(matchesQuery("Major Blowhorn logo", "cast"), false);
});

test("cardMatches follows the kind and status radios and the search", () => {
  assert.equal(cardMatches(card(), { kind: "all", status: "all", q: "" }), true);
  assert.equal(cardMatches(card(), { kind: "logo", status: "all", q: "" }), true);
  assert.equal(cardMatches(card(), { kind: "cast", status: "all", q: "" }), false);
  assert.equal(cardMatches(card(), { kind: "all", status: "ready", q: "" }), true);
  assert.equal(cardMatches(card(), { kind: "all", status: "held", q: "" }), false);
  assert.equal(cardMatches(card(), { kind: "all", status: "all", q: "blowhorn" }), true);
  assert.equal(cardMatches(card(), { kind: "all", status: "all", q: "thunderlung" }), false);
  // The clips choice hides the whole files section, so no card matches.
  assert.equal(cardMatches(card(), { kind: "clips", status: "all", q: "" }), false);
});

test("pageOf pages 48 at a time and clamps the page", () => {
  const items = Array.from({ length: 1078 }, (_, i) => i);
  const first = pageOf(items, 1);
  assert.equal(first.items.length, PAGE_SIZE);
  assert.equal(first.items[0], 0);
  assert.equal(first.pages, 23);
  assert.equal(first.page, 1);
  const last = pageOf(items, 23);
  assert.equal(last.items.length, 1078 - 22 * PAGE_SIZE);
  assert.equal(last.items[0], 22 * PAGE_SIZE);
  assert.equal(pageOf(items, 0).page, 1);
  assert.equal(pageOf(items, 99).page, 23);
  const empty = pageOf([], 1);
  assert.deepEqual(empty, { items: [], page: 1, pages: 1 });
});

test("searchCountText names the match and stays empty without a query", () => {
  assert.equal(searchCountText(3, 1078, 1, 17, "ox"), '3 of 1078 files, 1 of 17 clips match "ox"');
  assert.equal(searchCountText(0, 1078, 0, 17, ""), "");
});
