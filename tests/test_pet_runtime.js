"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const webRoot = path.join(__dirname, "..", "web");
const html = fs.readFileSync(path.join(webRoot, "pet.html"), "utf8");
const manifestSource = fs.readFileSync(path.join(webRoot, "extras", "manifest.js"), "utf8");
const inlineScripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
  .filter((match) => !/\ssrc\s*=/.test(match[0]));
assert.strictEqual(inlineScripts.length, 1, "expected one inline script");

let now = 0;
let nextTimerId = 1;
const timers = new Map();
function fakeSetTimeout(callback, delay = 0) {
  const id = nextTimerId++;
  timers.set(id, { callback, due: now + Math.max(0, Number(delay) || 0) });
  return id;
}
function fakeClearTimeout(id) {
  timers.delete(id);
}
async function flushPromises() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}
async function advance(milliseconds) {
  const target = now + milliseconds;
  let iterations = 0;
  while (true) {
    let chosenId = null;
    let chosen = null;
    for (const [id, timer] of timers) {
      if (timer.due <= target && (!chosen || timer.due < chosen.due)) {
        chosenId = id;
        chosen = timer;
      }
    }
    if (!chosen) break;
    assert.ok(++iterations < 1000, "timer loop did not settle");
    now = chosen.due;
    timers.delete(chosenId);
    chosen.callback();
    await flushPromises();
  }
  now = target;
  await flushPromises();
}

function makeElement(id) {
  const attrs = new Map();
  const element = {
    id,
    style: {},
    children: [],
    textContent: "",
    appendChild(child) { this.children.push(child); },
    setAttribute(name, value) { attrs.set(name, String(value)); },
    getAttribute(name) { return attrs.has(name) ? attrs.get(name) : null; },
    removeAttribute(name) {
      attrs.delete(name);
      if (name === "src") this._src = "";
    }
  };
  Object.defineProperty(element, "src", {
    get() { return element._src || ""; },
    set(value) { element._src = String(value); attrs.set("src", String(value)); }
  });
  return element;
}

const elements = new Map([
  ["pet-stage", makeElement("pet-stage")],
  ["live2d-layer", makeElement("live2d-layer")],
  ["action-layer", makeElement("action-layer")],
  ["action-canvas", makeElement("action-canvas")],
  ["bubble-layer", makeElement("bubble-layer")],
  ["bubble-image", makeElement("bubble-image")],
  ["voice-caption", makeElement("voice-caption")]
]);
const canvas = elements.get("action-canvas");
canvas.width = 275;
canvas.height = 268;
canvas.draws = [];
canvas.getContext = () => ({
  clearRect(...args) { canvas.lastClear = args; },
  drawImage(...args) { canvas.draws.push(args); }
});

class MockImage {
  constructor() {
    this.naturalWidth = 190;
    this.naturalHeight = 250;
    this.onload = null;
    this.onerror = null;
  }
  set src(value) {
    this._src = value;
    queueMicrotask(() => this.onload && this.onload());
  }
  get src() { return this._src; }
}

const audioInstances = [];
class MockAudio {
  constructor(src) {
    this.src = src;
    this.paused = true;
    this.ended = false;
    this.currentTime = 0;
    this.volume = 1;
    this.playCount = 0;
    this.pauseCount = 0;
    audioInstances.push(this);
  }
  play() {
    this.paused = false;
    this.ended = false;
    this.playCount += 1;
    return Promise.resolve();
  }
  pause() { this.paused = true; this.pauseCount += 1; }
  removeAttribute(name) { if (name === "src") this.src = ""; }
  load() { this.loadedAfterClear = true; }
}

const soundManager = {
  volume: 1,
  destroyCount: 0,
  disposeCount: 0,
  add() { return {}; },
  play() { return Promise.resolve(); },
  dispose() { this.disposeCount += 1; },
  destroy() { this.destroyCount += 1; }
};
const motionCalls = [];
const expressionCalls = [];
const motionManager = {
  stopCount: 0,
  stopAllMotions() { this.stopCount += 1; },
  startMotion(...args) { return Promise.resolve(args); }
};
const model = {
  autoUpdate: false,
  internalModel: { originalWidth: 275, originalHeight: 268, motionManager },
  scale: { set(value) { model.scaleValue = value; } },
  x: 0,
  y: 0,
  motion(group, index, priority) {
    motionCalls.push({ group, index, priority });
    return motionManager.startMotion(group, index, priority);
  },
  expression(index) { expressionCalls.push(index); return Promise.resolve(true); },
  focus(x, y) { model.lastFocus = [x, y]; }
};
let application = null;
class MockApplication {
  constructor() {
    this.view = makeElement("pixi-canvas");
    this.stage = { addChild(child) { this.child = child; } };
    this.ticker = {
      started: true,
      stop() { this.started = false; },
      start() { this.started = true; }
    };
    application = this;
  }
}

const logs = [];
const eventHandlers = {};
const documentMock = {
  baseURI: "file:///C:/WorkspacePanel/web/pet.html",
  hidden: false,
  getElementById(id) { return elements.get(id); }
};
const mathMock = Object.create(Math);
mathMock.random = () => 0;
const context = {
  console: { log(message) { logs.push(String(message)); } },
  document: documentMock,
  Image: MockImage,
  Audio: MockAudio,
  URL,
  Promise,
  Object,
  Number,
  Math: mathMock,
  setTimeout: fakeSetTimeout,
  clearTimeout: fakeClearTimeout,
  queueMicrotask,
  performance: { now: () => now },
  innerWidth: 275,
  innerHeight: 268,
  addEventListener(type, handler) { (eventHandlers[type] ||= []).push(handler); },
  PIXI: {
    Application: MockApplication,
    live2d: {
      SoundManager: soundManager,
      Live2DModel: { from() { return Promise.resolve(model); } }
    }
  }
};
context.window = context;
context.globalThis = context;
vm.createContext(context);
vm.runInContext(manifestSource, context, { filename: "manifest.js" });
vm.runInContext(inlineScripts[0][1], context, { filename: "pet-inline.js" });

(async () => {
  await flushPromises();
  assert.strictEqual(context.petReady, true);
  assert.strictEqual(context.petExtrasReady, true);
  assert.ok(logs.some((line) => line.startsWith("PET_READY ")));
  let state = context.petDebugState();
  assert.strictEqual(state.tickerStarted, true);
  assert.strictEqual(state.modelAutoUpdate, true);
  assert.strictEqual(state.randomTimer, true);

  assert.strictEqual(context.petSetVolume(0.73), 0.73);
  assert.strictEqual(soundManager.volume, 0.73);

  assert.strictEqual(await context.petPlayAction("Standby"), true);
  state = context.petDebugState();
  assert.strictEqual(state.action, "Standby");
  assert.strictEqual(state.actionTimer, true);
  assert.strictEqual(state.tickerStarted, false);
  assert.strictEqual(elements.get("action-layer").style.display, "flex");
  assert.strictEqual(elements.get("live2d-layer").style.visibility, "hidden");
  assert.ok(canvas.draws.length >= 1);
  await advance(1200);
  state = context.petDebugState();
  assert.strictEqual(state.action, null);
  assert.strictEqual(state.tickerStarted, true);
  assert.strictEqual(elements.get("action-layer").style.display, "none");

  const first = context.petPlayAction("Standby");
  const second = context.petPlayAction("sleep");
  assert.strictEqual(await first, false, "stale action request must be ignored");
  assert.strictEqual(await second, true);
  assert.strictEqual(context.petDebugState().action, "sleep");
  context.petSetDragging(true);
  assert.strictEqual(context.petDebugState().actionTimer, false);
  await advance(1000);
  assert.strictEqual(context.petDebugState().action, "sleep");
  context.petSetDragging(false);
  assert.strictEqual(context.petDebugState().actionTimer, true);
  context.petStopAction();

  assert.strictEqual(context.petShowBubble("Happy", "happy", 700), true);
  assert.strictEqual(context.petDebugState().bubbleTimer, true);
  await advance(200);
  context.petSetDragging(true);
  assert.strictEqual(context.petDebugState().bubbleTimer, false);
  await advance(1000);
  assert.strictEqual(context.petDebugState().bubble, true);
  context.petSetDragging(false);
  await advance(499);
  assert.strictEqual(context.petDebugState().bubble, true);
  await advance(1);
  assert.strictEqual(context.petDebugState().bubble, false);

  const voiceId = context.PET_EXTRA_ASSETS.voices.greeting.items[0].id;
  assert.strictEqual(context.petPlayVoice(voiceId), true);
  const voice = audioInstances[audioInstances.length - 1];
  assert.strictEqual(voice.volume, 0.73);
  assert.strictEqual(voice.paused, false);
  assert.strictEqual(context.petDebugState().voice, true);
  context.petSetDragging(true);
  assert.strictEqual(voice.paused, true);
  const beforeResume = voice.playCount;
  context.petSetDragging(false);
  await flushPromises();
  assert.strictEqual(voice.playCount, beforeResume + 1);

  context.petShowBubble("Angry", "angry", 900);
  await context.petPlayAction("Love");
  context.petPlayVoice(voiceId);
  const suspendedVoice = audioInstances[audioInstances.length - 1];
  context.petSetDragging(true);
  context.petSetSuspended(true);
  state = context.petDebugState();
  assert.strictEqual(state.suspended, true);
  assert.strictEqual(state.action, null);
  assert.strictEqual(state.bubble, false);
  assert.strictEqual(state.voice, false);
  assert.strictEqual(state.actionTimer, false);
  assert.strictEqual(state.bubbleTimer, false);
  assert.strictEqual(state.tickerStarted, false);
  assert.strictEqual(suspendedVoice.src, "");
  const stoppedPlayCount = suspendedVoice.playCount;
  context.petSetDragging(false);
  context.petSetSuspended(false);
  await flushPromises();
  assert.strictEqual(suspendedVoice.playCount, stoppedPlayCount, "hard-stopped voice must not resume");
  assert.strictEqual(context.petDebugState().tickerStarted, true);

  context.petSetAutoInterval(30);
  const autoPicksBeforeSong = logs.filter((line) => line.startsWith("PET_RANDOM_PICK auto ")).length;
  assert.strictEqual(context.petPlayMotion(4, null, "manual"), true);
  state = context.petDebugState();
  assert.ok(state.autoBlockedFor >= 202.9 && state.autoBlockedFor <= 203);
  assert.strictEqual(state.autoTimer, true);
  assert.strictEqual(state.randomTimer, false, "ambient motion must not interrupt the manual long song");
  await advance(232999);
  assert.strictEqual(logs.filter((line) => line.startsWith("PET_RANDOM_PICK auto ")).length,
    autoPicksBeforeSong, "auto picker must wait for the song plus a full interval");
  await advance(1);
  assert.strictEqual(logs.filter((line) => line.startsWith("PET_RANDOM_PICK auto ")).length,
    autoPicksBeforeSong + 1);
  await flushPromises();
  context.petStopInteraction();
  context.petSetAutoInterval(0);

  motionCalls.length = 0;
  await advance(9000);
  assert.ok(motionCalls.length >= 1, "ambient timer should make a motion with deterministic random");
  assert.ok(motionCalls.every((call) => call.index === 2 || call.index === 3));
  assert.strictEqual(await context.petInteract("head"), true);
  assert.strictEqual(context.petDebugState().action, "Standby",
    "legacy petInteract must delegate to the unified random picker");
  context.petStopInteraction();

  assert.strictEqual(context.petPlayVoice("missing"), false);
  assert.strictEqual(await context.petPlayAction("missing"), false);
  context.petDestroy();
  state = context.petDebugState();
  assert.strictEqual(state.destroyed, true);
  assert.strictEqual(state.voice, false);
  assert.strictEqual(state.bubble, false);
  assert.strictEqual(state.action, null);
  assert.strictEqual(state.randomTimer, false);
  assert.strictEqual(state.tickerStarted, false);
  assert.strictEqual([...timers.values()].filter((timer) => timer.due >= now).length, 0);

  console.log(JSON.stringify({
    ok: true,
    actions: Object.keys(context.PET_EXTRA_ASSETS.actions).length,
    actionFrames: Object.values(context.PET_EXTRA_ASSETS.actions).reduce((n, item) => n + item.frames.length, 0),
    bubbleMoods: Object.values(context.PET_EXTRA_ASSETS.bubbles).reduce((n, group) => n + Object.keys(group.items).length, 0),
    bubbleFiles: Object.values(context.PET_EXTRA_ASSETS.bubbles).reduce((n, group) => n + Object.values(group.items).reduce((m, item) => m + item.files.length, 0), 0),
    voices: Object.values(context.PET_EXTRA_ASSETS.voices).reduce((n, group) => n + group.items.length, 0),
    audioInstances: audioInstances.length,
    draws: canvas.draws.length
  }));
})().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
