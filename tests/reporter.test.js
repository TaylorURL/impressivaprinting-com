import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

/**
 * What the page's own error reporter does with a throw raised inside the
 * visitor's browser rather than by the site.
 *
 * An extension's messaging call fails with an Error the page can see and a
 * stack the page cannot: the extension APIs on iOS are a native bridge, so
 * Safari hands the rejection over with an empty stack and the message as the
 * whole of the evidence. The reporter decides those by where the frames point,
 * which is the right question with frames to read and no question at all
 * without them, so one of these filed as this site's fault.
 *
 * Both directions are asked, and the second matters more. The guard decides
 * what never reaches the collector, so one that widened onto the site's own
 * throws would be the reporter going quiet on real faults, and nothing
 * announces a filter that has started swallowing too much. The question is put
 * to the reporter as the page serves it rather than to the source, so a rule
 * that stops being reached fails here whatever the file looks like.
 */

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PAGE = readFileSync(path.join(ROOT, 'index.html'), 'utf8');

const inline = [...PAGE.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]);
const reporter = inline.find((source) => source.includes('/report'));

/**
 * Stands the reporter up on its own and hands back what it posted and what it
 * held. Nothing here offers a `Worker`, so reports fall through to
 * `sendBeacon`, which is the one transport a test can read.
 */
function collector() {
  const posted = [];
  const listeners = {};
  const sandbox = {
    JSON,
    String,
    Error,
    RegExp,
    location: {
      href: 'https://impressivaprinting.com/',
      search: '',
      origin: 'https://impressivaprinting.com',
    },
    navigator: {
      userAgent:
        'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.6.1 Mobile/15E148 Safari/604.1',
      sendBeacon(endpoint, body) {
        posted.push(JSON.parse(body));
        return true;
      },
    },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    addEventListener(type, handler) {
      (listeners[type] = listeners[type] || []).push(handler);
    },
    document: {
      querySelectorAll: () => [],
      createElement: () => ({}),
      head: { appendChild() {} },
    },
    console: { error() {}, warn() {}, trace() {}, assert() {}, log() {} },
    setTimeout: () => 0,
    clearTimeout() {},
  };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  sandbox.dispatchEvent = () => true;
  const context = vm.createContext(sandbox);
  new vm.Script(reporter, { filename: 'https://impressivaprinting.com/' }).runInContext(context);
  return {
    posted,
    /**
     * Hands the page's own `unhandledrejection` listener an event, which is the
     * only way to ask what it does with one. Reading the source instead is how
     * a filter gets to be documented, correct and never reached.
     */
    rejects(reason) {
      for (const handler of listeners.unhandledrejection || [])
        handler({ reason, preventDefault() {} });
    },
    /** The same question on the error handler, for a throw of the site's own. */
    throws(event) {
      for (const handler of listeners.error || [])
        handler({ preventDefault() {}, target: sandbox, ...event });
    },
    /** Everything the reporter swallowed is still readable on the page. */
    held() {
      return sandbox.window.__reporter.replay();
    },
  };
}

test('the stackless extension bridge failure is held rather than filed', () => {
  const page = collector();
  const bridge = new Error('Invalid call to runtime.sendMessage(). Tab not found.');
  delete bridge.stack;
  page.rejects(bridge);
  assert.deepEqual(page.posted, []);
});

test('the same failure stays readable on a live console', () => {
  const page = collector();
  const bridge = new Error('Invalid call to runtime.sendMessage(). Tab not found.');
  delete bridge.stack;
  page.rejects(bridge);
  assert.equal(page.held().length, 1);
  assert.match(page.held()[0].message, /runtime\.sendMessage/);
});

test('a bridge failure rejected with a bare string is held too', () => {
  const page = collector();
  page.rejects('Extension context invalidated');
  assert.deepEqual(page.posted, []);
});

test('an extension-only stack is still held', () => {
  const page = collector();
  page.rejects({
    message: 'Cannot read properties of null',
    stack: 'at safari-extension://a1b2/content.js:1:1\nat safari-extension://a1b2/content.js:2:9',
  });
  assert.deepEqual(page.posted, []);
});

test("the site's own rejection naming a sendMessage of its own is filed", () => {
  const page = collector();
  page.rejects({
    message: 'channel.sendMessage is not a function',
    stack: 'at https://impressivaprinting.com/assets/index-aaaa1111.js:4:17',
  });
  assert.equal(page.posted.length, 1);
  assert.equal(page.posted[0].kind, 'rejection');
});

test("the site's own stackless rejection is still filed", () => {
  const page = collector();
  page.rejects('Checkout quote came back empty');
  assert.equal(page.posted.length, 1);
  assert.match(page.posted[0].message, /Checkout quote/);
});

test("an uncaught throw of the site's own is still filed", () => {
  const page = collector();
  page.throws({
    target: null,
    message: 'orderTotal is not defined',
    error: { stack: 'at https://impressivaprinting.com/assets/index-aaaa1111.js:9:3' },
  });
  assert.equal(page.posted.length, 1);
  assert.equal(page.posted[0].kind, 'uncaught');
});
