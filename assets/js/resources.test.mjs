import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(new URL("./resources.js", import.meta.url), "utf8");
const videosHtml = fs.readFileSync(new URL("../../layouts/videos.html", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../../assets/css/resources.css", import.meta.url), "utf8");

function createMockElement(tag, attrs = {}) {
  const listeners = {};
  const el = {
    tagName: tag.toUpperCase(),
    type: attrs.type || (tag === "button" ? "button" : ""),
    hidden: false,
    textContent: "",
    attrs: { ...attrs },
    children: [],
    parentNode: null,
    listeners,
    addEventListener(evt, fn) {
      if (!listeners[evt]) listeners[evt] = [];
      listeners[evt].push(fn);
    },
    click() {
      if (listeners["click"]) {
        listeners["click"].forEach((fn) => fn({ target: el }));
      }
    },
    getAttribute(name) {
      return this.attrs[name] !== undefined ? this.attrs[name] : null;
    },
    setAttribute(name, val) {
      this.attrs[name] = String(val);
    },
    removeAttribute(name) {
      delete this.attrs[name];
    },
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
  };
  return el;
}

function createEnvironment(hash = "") {
  // Category buttons matching layouts/videos.html
  const allBtn = createMockElement("button", {
    type: "button",
    class: "category-tab",
    "data-category-tab": "all",
    "aria-pressed": "true",
  });
  const wtBtn = createMockElement("button", {
    type: "button",
    class: "category-tab",
    "data-category-tab": "walkthroughs",
    "aria-pressed": "false",
  });
  const ftBtn = createMockElement("button", {
    type: "button",
    class: "category-tab",
    "data-category-tab": "features",
    "aria-pressed": "false",
  });
  const categoryButtons = [allBtn, wtBtn, ftBtn];

  // Cards matching layouts/videos.html video cards
  const card1 = createMockElement("li", {
    "data-card": "",
    "data-category": "walkthroughs",
    "data-tags": "quickstart desktop",
    "data-search": "getting started walkthrough",
  });
  const card2 = createMockElement("li", {
    "data-card": "",
    "data-category": "features",
    "data-tags": "cloud sync",
    "data-search": "cloud sync feature overview",
  });
  const card3 = createMockElement("li", {
    "data-card": "",
    "data-category": "walkthroughs",
    "data-tags": "scheduling",
    "data-search": "how to schedule posts",
  });
  const cards = [card1, card2, card3];

  const grid = createMockElement("ul", {
    "data-collection-grid": "",
    "data-collection-noun": "videos",
  });
  grid.querySelectorAll = (sel) => {
    if (sel === "[data-card]") return cards;
    return [];
  };

  const status = createMockElement("p", {
    "data-collection-status": "",
  });

  let cardDealCalled = 0;
  const window = {
    location: { hash, pathname: "/resources/videos/" },
    history: {
      replaceState: () => {},
    },
    blowhornCardDeal: () => {
      cardDealCalled++;
    },
  };

  const document = {
    querySelector: (sel) => {
      if (sel === "[data-collection-grid]") return grid;
      if (sel === "[data-video-dialog]") return null;
      if (sel === "[data-collection-search]") return null;
      if (sel === "[data-collection-status]") return status;
      return null;
    },
    querySelectorAll: (sel) => {
      if (sel === "[data-category-tab]") return categoryButtons;
      if (sel === "[data-tag-chip]") return [];
      if (sel === "[data-play-video]") return [];
      return [];
    },
  };

  vm.runInNewContext(source, {
    window,
    document,
    location: window.location,
    history: window.history,
    Array,
    Object,
    JSON,
  });

  return {
    allBtn,
    wtBtn,
    ftBtn,
    categoryButtons,
    cards,
    card1,
    card2,
    card3,
    status,
    getCardDealCount: () => cardDealCalled,
  };
}

test("category buttons do not have tab roles and use aria-pressed for active state", () => {
  const env = createEnvironment();

  for (const btn of env.categoryButtons) {
    assert.equal(btn.getAttribute("role"), null, "Category button must not have role='tab'");
    assert.equal(btn.getAttribute("aria-selected"), null, "Category button must not use aria-selected");
    assert.equal(btn.type, "button", "Category control must be a native button");
  }

  assert.equal(env.allBtn.getAttribute("aria-pressed"), "true", "Initial active category 'all' must have aria-pressed='true'");
  assert.equal(env.wtBtn.getAttribute("aria-pressed"), "false", "Inactive category must have aria-pressed='false'");
  assert.equal(env.ftBtn.getAttribute("aria-pressed"), "false", "Inactive category must have aria-pressed='false'");
});

test("clicking another category updates aria-pressed so only the active category is pressed", () => {
  const env = createEnvironment();

  env.wtBtn.click();

  assert.equal(env.wtBtn.getAttribute("aria-pressed"), "true", "Clicked category must have aria-pressed='true'");
  assert.equal(env.allBtn.getAttribute("aria-pressed"), "false", "Previous category must now have aria-pressed='false'");
  assert.equal(env.ftBtn.getAttribute("aria-pressed"), "false", "Unselected category must have aria-pressed='false'");

  assert.equal(env.wtBtn.getAttribute("aria-selected"), null, "Must not set aria-selected");
  assert.equal(env.allBtn.getAttribute("aria-selected"), null, "Must not set aria-selected");

  env.ftBtn.click();

  assert.equal(env.ftBtn.getAttribute("aria-pressed"), "true", "Newly clicked category must have aria-pressed='true'");
  assert.equal(env.wtBtn.getAttribute("aria-pressed"), "false", "Previously active category must have aria-pressed='false'");
  assert.equal(env.allBtn.getAttribute("aria-pressed"), "false", "Other category must remain aria-pressed='false'");
});

test("video grid filtering works when switching categories", () => {
  const env = createEnvironment();

  assert.equal(env.card1.hidden, false);
  assert.equal(env.card2.hidden, false);
  assert.equal(env.card3.hidden, false);

  env.wtBtn.click();

  assert.equal(env.card1.hidden, false, "Walkthrough card 1 must be visible");
  assert.equal(env.card2.hidden, true, "Feature card 2 must be hidden");
  assert.equal(env.card3.hidden, false, "Walkthrough card 3 must be visible");
  assert.equal(env.status.textContent, "2 of 3 videos shown");

  env.allBtn.click();

  assert.equal(env.card1.hidden, false, "All cards must be visible again");
  assert.equal(env.card2.hidden, false, "All cards must be visible again");
  assert.equal(env.card3.hidden, false, "All cards must be visible again");
  assert.equal(env.status.textContent, "");
});

test("deep-linking via location hash activates category and sets aria-pressed", () => {
  const env = createEnvironment("#walkthroughs");

  assert.equal(env.wtBtn.getAttribute("aria-pressed"), "true", "Hash-selected category must have aria-pressed='true'");
  assert.equal(env.allBtn.getAttribute("aria-pressed"), "false", "'all' category must have aria-pressed='false'");
  assert.equal(env.card1.hidden, false);
  assert.equal(env.card2.hidden, true);
  assert.equal(env.card3.hidden, false);
});

test("layouts/videos.html does not use role='tablist', role='tab', or aria-selected", () => {
  assert.doesNotMatch(videosHtml, /role=["']tablist["']/, "layouts/videos.html must not use role='tablist'");
  assert.doesNotMatch(videosHtml, /role=["']tab["']/, "layouts/videos.html must not use role='tab'");
  assert.doesNotMatch(videosHtml, /aria-selected/, "layouts/videos.html must not use aria-selected");

  assert.match(videosHtml, /role=["']group["']\s+aria-label=["']Filter by category["']/,
    "Category filter must be wrapped in a group with aria-label='Filter by category'");
  assert.match(videosHtml, /data-category-tab=["']all["']\s+aria-pressed=["']true["']/,
    "'all' category button must have initial aria-pressed='true'");
  assert.match(videosHtml, /aria-pressed=["']false["']/,
    "Other category buttons must have initial aria-pressed='false'");
});

test("assets/css/resources.css styles .category-tab[aria-pressed='true']", () => {
  assert.match(css, /\.category-tab\[aria-pressed="true"\]/,
    "CSS must style .category-tab[aria-pressed='true']");
  assert.doesNotMatch(css, /\.category-tab\[aria-selected="true"\]/,
    "CSS must not retain obsolete .category-tab[aria-selected='true']");
});
