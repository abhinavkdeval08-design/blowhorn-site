import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

// download.js is a classic script, so it runs in a fake page with only the
// Windows card. Without #download-status the Mac release lookup does nothing.
const source = readFileSync(new URL("./download.js", import.meta.url), "utf8");
const markup = readFileSync(new URL("../../layouts/download.html", import.meta.url), "utf8");

const CONFIRMATION = "You are on the list! We will email you when Blowhorn for Windows is ready.";
const GENERIC_ERROR = "Something went wrong. Please try again.";

function loadPage({ respond, withFetch = true } = {}) {
  const page = { focused: null, posts: [] };

  function node(id, props = {}) {
    const listeners = {};
    return {
      id,
      hidden: false,
      textContent: "",
      addEventListener(type, fn) {
        listeners[type] = fn;
      },
      fire(type, ev = {}) {
        return listeners[type](ev);
      },
      focus() {
        page.focused = this;
      },
      setAttribute(name, value) {
        this[name] = value;
      },
      ...props,
    };
  }

  const toggle = node("windows-notify-toggle", { hidden: true });
  const email = node("windows-notify-email", { value: "major@example.com" });
  const row = node("row");
  const note = node("note");
  const status = node("windows-notify-status");
  const submit = node("submit", { disabled: false });
  const form = node("windows-notify-form", {
    action: "https://api.blowhorn.ai/api/waitlist",
    fields: { email: "major@example.com", topic: "windows", source_page: "/download/", website: "" },
    resets: 0,
    reset() {
      this.resets += 1;
    },
    querySelector(selector) {
      assert.equal(selector, "[type=submit]");
      return submit;
    },
    querySelectorAll(selector) {
      assert.equal(selector, ".newsletter-row, .caption");
      return [row, note];
    },
  });
  const byId = { [toggle.id]: toggle, [form.id]: form, [email.id]: email, [status.id]: status };

  class FormData {
    constructor(f) {
      this.entries = Object.entries(f.fields);
    }
    forEach(fn) {
      this.entries.forEach(([key, value]) => fn(value, key));
    }
  }

  function fetch(url, init) {
    page.posts.push({ url, init });
    return respond();
  }

  const window = withFetch ? { fetch } : {};
  const context = vm.createContext({
    window,
    fetch,
    FormData,
    document: { getElementById: (id) => byId[id] || null },
  });
  vm.runInContext(source, context);
  return { page, toggle, form, email, row, note, status, submit };
}

function reply(ok, body) {
  return () => Promise.resolve({ ok, json: () => Promise.resolve(body) });
}

const settle = () => new Promise((resolve) => setImmediate(resolve));

test("with JavaScript the button shows and the form waits behind it", () => {
  const { toggle, form } = loadPage({ respond: reply(true, { ok: true }) });
  assert.equal(toggle.hidden, false);
  assert.equal(form.hidden, true);
});

test("the button gives way to the form and focus moves to the field", () => {
  const { page, toggle, form, email } = loadPage({ respond: reply(true, { ok: true }) });
  toggle.fire("click");
  assert.equal(toggle.hidden, true);
  assert.equal(form.hidden, false);
  assert.equal(page.focused, email);
});

test("a successful signup leaves only the confirmation and focuses it", async () => {
  const { page, toggle, form, row, note, status, submit } = loadPage({ respond: reply(true, { ok: true }) });
  toggle.fire("click");
  let prevented = false;
  form.fire("submit", { preventDefault: () => (prevented = true) });
  await settle();

  assert.equal(prevented, true);
  assert.equal(page.posts.length, 1);
  assert.equal(page.posts[0].url, form.action);
  assert.deepEqual(JSON.parse(page.posts[0].init.body), form.fields);
  assert.equal(form.resets, 1);
  assert.equal(row.hidden, true);
  assert.equal(note.hidden, true);
  assert.equal(form.hidden, false, "the status line lives in the form, so the form stays");
  assert.equal(status.textContent, CONFIRMATION);
  assert.equal(page.focused, status);
  assert.equal(submit.disabled, true);
});

test("the submit button is disabled while the signup is in flight", () => {
  const { toggle, form, submit } = loadPage({ respond: () => new Promise(() => {}) });
  toggle.fire("click");
  form.fire("submit", { preventDefault() {} });
  assert.equal(submit.disabled, true);
});

test("a rejected signup keeps the field and shows the service's error", async () => {
  const { page, toggle, form, email, row, note, status, submit } = loadPage({
    respond: reply(false, { ok: false, error: "Enter a valid email address." }),
  });
  toggle.fire("click");
  form.fire("submit", { preventDefault() {} });
  await settle();

  assert.equal(status.textContent, "Enter a valid email address.");
  assert.equal(row.hidden, false);
  assert.equal(note.hidden, false);
  assert.equal(form.resets, 0, "the entered address stays for a retry");
  assert.equal(page.focused, email);
  assert.equal(submit.disabled, false);
});

test("a network failure keeps the field and shows the generic error", async () => {
  const { toggle, form, row, status, submit } = loadPage({ respond: () => Promise.reject(new Error("offline")) });
  toggle.fire("click");
  form.fire("submit", { preventDefault() {} });
  await settle();

  assert.equal(status.textContent, GENERIC_ERROR);
  assert.equal(row.hidden, false);
  assert.equal(form.resets, 0);
  assert.equal(submit.disabled, false);
});

test("without fetch the button stays hidden and the form stays visible", () => {
  const { toggle, form } = loadPage({ withFetch: false });
  assert.equal(toggle.hidden, true);
  assert.equal(form.hidden, false);
});

test("the field keeps its accessible name and placeholder without a visible label", () => {
  assert.match(markup, /<label class="visually-hidden" for="windows-notify-email">Email address<\/label>/);
  assert.match(markup, /id="windows-notify-email"[^>]*placeholder="Email address"/);
  assert.match(markup, /id="windows-notify-status"[^>]*role="status"[^>]*tabindex="-1"/);
});
