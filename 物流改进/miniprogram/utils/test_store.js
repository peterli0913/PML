const assert = require("assert");
const fs = require("fs");
const path = require("path");
const store = require("./store.js");

const state = store.create();
store.freeze(state);
const before = store.planOf(state, "甲醇");
assert.strictEqual(before.suggestQty, 11);
assert.strictEqual(before.legacyQty, 0);
assert.strictEqual(before.urgent, true);
assert.strictEqual(before.stockoutHour, 1);
assert.strictEqual(before.leadHours, 52);
assert.strictEqual(store.weekSum(state), 98);
assert.strictEqual(store.boardView(state).diff, 0);
assert.strictEqual(store.boardView(state).late, 1);
assert.strictEqual(store.hourlyView(state, "甲醇").days[0].qty, 18);
assert.strictEqual(store.hourlyView(state, "甲醇").days[1].qty, 0);
assert.strictEqual(store.hourlyView(state, "IPAc").delays.length, 1);
assert.ok(store.hourlyView(state, "甲醇").samples.length >= 28);

store.setWeekQty(state, "W5", 30);
assert.strictEqual(store.weekSum(state), 110);
assert.strictEqual(state.batches.find(function (b) { return b.id === "B08"; }).qty, 30);
assert.strictEqual(store.demandView(state).rows.find(function (w) { return w.id === "W5"; }).batchQty, 30);
assert.strictEqual(store.boardView(state).total, 110);
assert.strictEqual(store.boardView(state).diff, 0);
const after = store.planOf(state, "甲醇");
assert.strictEqual(after.suggestQty, 23);
assert.ok(after.arrivalChange);
assert.ok(store.hourlyView(state, "甲醇").changeText.indexOf("23") >= 0);

assert.strictEqual(store.setWeekQty(state, "W5", "abc"), false);
assert.strictEqual(state.weekly.find(function (w) { return w.id === "W5"; }).weekQty, 30);

const dmfBefore = store.planOf(state, "DMF").demand[0];
assert.strictEqual(store.setDuration(state, "OP-12", 12), true);
assert.strictEqual(store.applyDuration(state, "OP-12"), true);
assert.strictEqual(state.batches.find(function (b) { return b.id === "B01"; }).durationHours, 12);
assert.notStrictEqual(store.planOf(state, "DMF").demand[0], dmfBefore);

assert.strictEqual(store.setBatchField(state, "B02", "plannedStartHour", -6), true);
assert.ok(store.planOf(state, "DMF").delays.some(function (item) { return item.id === "B02"; }));
assert.strictEqual(store.setBatchField(state, "B02", "progress", 2), false);
assert.strictEqual(state.batches.find(function (b) { return b.id === "B02"; }).progress, 0);

state.role = "物流计划员";
assert.strictEqual(store.demandView(state).canEdit, false);
assert.strictEqual(store.setWeekQty(state, "W5", 40), false);
assert.strictEqual(state.weekly.find(function (w) { return w.id === "W5"; }).weekQty, 30);
state.role = "生产经理";

const root = path.join(__dirname, "..");
const titles = [
  "更新溶剂需求",
  "更新批次清单",
  "更新单操作时长",
  "看板抓取当前进度及周计划",
  "未来一周小时需求",
];
const shell = fs.readFileSync(path.join(root, "components/shell/shell.js"), "utf8");
titles.forEach(function (title) { assert.ok(shell.indexOf(title) >= 0, title); });
assert.ok(fs.readFileSync(path.join(root, "pages/hourly/index.wxml"), "utf8").indexOf("执行 12 小时重算") >= 0);
assert.ok(fs.readFileSync(path.join(root, "pages/board/index.wxml"), "utf8").indexOf("bindblur=\"onQty\"") >= 0);
assert.ok(fs.readFileSync(path.join(root, "project.config.json"), "utf8").indexOf("miniprogram") >= 0);

console.log("miniprogram store ok", before.suggestQty, "->", after.suggestQty);
