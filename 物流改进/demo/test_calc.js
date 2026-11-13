const assert = require("assert");
const Calc = require("./calc.js");

const ipac = { id: "TIF04", qty: 9, low: 15, online: true, point: "LI-TIF04" };
const ipacResult = Calc.solventSuggestion(ipac, 12, 0, 0);
assert.strictEqual(ipacResult.suggest, 6);
assert.strictEqual(ipacResult.priority, -3);
assert.strictEqual(ipacResult.blocked, false);

const offline = Calc.solventSuggestion({ id: "TIF04", qty: 9, low: 15, online: false, point: "LI" }, 12, 0, 0);
assert.strictEqual(offline.blocked, true);
assert.strictEqual(offline.suggest, 0);

const unmapped = Calc.solventSuggestion({ id: "TIF99", qty: 10, low: 5, online: true, point: "" }, 1, 0, 0);
assert.strictEqual(unmapped.blocked, true);

const dmf = Calc.solventSuggestion({ id: "TIF01", qty: 62, low: 20, online: true, point: "LI" }, 0, 20, 0);
assert.strictEqual(dmf.suggest, 0);

const waste = Calc.wasteSuggestion({ id: "WF01", qty: 31.2, cap: 40, high: 90, online: true }, 8);
assert.strictEqual(waste.suggest, 3.2);
assert.strictEqual(waste.ceiling, 36);

assert.strictEqual(Calc.canIssueSolvent({ name: "供应商乙", qualified: false }).ok, false);
assert.strictEqual(Calc.canIssueSolvent({ name: "供应商甲", qualified: true }).ok, true);

const poor = Calc.canIssueWaste({ name: "接收商乙", ready: false, quota: 20, used: 0 }, 3.2);
assert.strictEqual(poor.ok, false);
const rich = Calc.canIssueWaste({ name: "接收商甲", ready: true, quota: 40, used: 12 }, 3.2);
assert.strictEqual(rich.ok, true);
const short = Calc.canIssueWaste({ name: "接收商甲", ready: true, quota: 40, used: 39 }, 3.2);
assert.strictEqual(short.ok, false);

assert.strictEqual(Calc.bayCompatible({ bay: "鹤管A", solvent: "DMF", id: "TIF01", online: true }, "MTBE").ok, false);
assert.strictEqual(Calc.bayCompatible({ bay: "鹤管C", solvent: "MTBE", id: "TIF03", online: true }, "MTBE").ok, true);

const hours = Calc.hoursBetween("2026-11-01T08:00:00", "2026-11-02T10:40:00");
assert.strictEqual(hours, 26.7);

console.log("calc tests ok");
