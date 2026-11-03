const assert = require("assert");
const store = require("./store.js");

const state = store.create();
store.freeze(state);
const before = store.planOf(state, "甲醇").suggestQty;
assert.strictEqual(store.weekSum(state), 98);
store.setWeekQty(state, "W5", 30);
assert.strictEqual(store.weekSum(state), 110);
assert.strictEqual(state.batches.find(function (b) { return b.id === "B08"; }).qty, 30);
const after = store.planOf(state, "甲醇");
assert.notStrictEqual(after.suggestQty, before);
assert.ok(after.arrivalChange);
store.applyDuration(state, "OP-02");
assert.strictEqual(state.batches.find(function (b) { return b.id === "B06"; }).durationHours, 16);
console.log("miniprogram store ok", before, "->", after.suggestQty);
