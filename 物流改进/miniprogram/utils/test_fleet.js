const assert = require("assert");
const fleet = require("./fleet.js");

function fresh() { return fleet.create(); }

const walk = fresh();
assert.strictEqual(fleet.driverView(walk).current.instruction.indexOf("批号") < 0, true);
assert.ok(fleet.driverView(walk).current.instruction.indexOf("按导航来厂") >= 0);
assert.strictEqual(fleet.driverView(walk).current.bay, "甲醇位");
assert.strictEqual(fleet.driverView(walk).current.tank, "PS01");
assert.ok(fleet.driverView(walk).current.queueText.indexOf("第 1 位") >= 0);

assert.strictEqual(fleet.act(walk, "D102", "set_distance", { km: 12 }), true);
assert.strictEqual(fleet.orderView(walk, "D102").status, "到场预告");
assert.strictEqual(fleet.act(walk, "D102", "set_distance", { km: 3 }), true);
assert.strictEqual(fleet.orderView(walk, "D102").status, "待门卫核查");
assert.strictEqual(fleet.act(walk, "D102", "gate_pass"), true);
assert.strictEqual(fleet.orderView(walk, "D102").status, "待罐区入厂指令");

const blocked = fresh();
assert.strictEqual(fleet.act(blocked, "I006", "tank_in", { bayId: "B-IPAC" }), false);
assert.ok(blocked.toast.indexOf("可用") >= 0);
assert.strictEqual(fleet.orderView(blocked, "I006").status, "待罐区入厂指令");

const noCoa = fresh();
noCoa.orders[0].coa = false;
noCoa.orders[0].status = "待门卫核查";
assert.strictEqual(fleet.act(noCoa, "D102", "gate_pass"), false);

const release = fresh();
assert.strictEqual(fleet.act(release, "A221", "pull_release"), false);
assert.strictEqual(fleet.act(release, "A221", "mark_release"), true);
assert.strictEqual(fleet.act(release, "A221", "pull_release"), true);
assert.strictEqual(fleet.orderView(release, "A221").status, "待重新入厂");
assert.strictEqual(fleet.act(release, "A221", "reenter"), true);
assert.strictEqual(fleet.act(release, "A221", "start_unload"), true);
assert.strictEqual(fleet.orderView(release, "A221").status, "卸车中");

const mix = fresh();
const before = mix.tanks.find(function (tank) { return tank.id === "PS03"; }).qty;
assert.ok(fleet.orderView(mix, "F018").mix.indexOf("BN-DMF-1114-M-PS03") >= 0);
assert.strictEqual(fleet.act(mix, "F018", "start_unload"), true);
assert.strictEqual(fleet.act(mix, "F018", "disconnect"), true);
const ps03 = mix.tanks.find(function (tank) { return tank.id === "PS03"; });
assert.strictEqual(ps03.batch, "BN-DMF-1114-M-PS03");
assert.strictEqual(ps03.qty, before + 18);
assert.ok(fleet.driverView(mix).cars);

const waste = fresh();
assert.strictEqual(fleet.act(waste, "W033", "tank_in"), true);
assert.strictEqual(fleet.orderView(waste, "W033").status, "装车中");
assert.strictEqual(fleet.act(waste, "W033", "weigh"), true);
assert.strictEqual(fleet.act(waste, "W033", "manifest"), true);
assert.strictEqual(waste.receivers["甲"].quota, 12);
assert.strictEqual(waste.tanks.find(function (tank) { return tank.id === "WF01"; }).qty, 23);
assert.strictEqual(fleet.driverView(Object.assign(waste, { focusId: "W033" })).current.instruction.indexOf("可以出厂") >= 0, true);

const queue = fresh();
queue.orders.push(Object.assign({}, queue.orders[0], {
  id: "D199", plate: "津A·D199", rank: 10, status: "在途", closed: false,
}));
assert.strictEqual(fleet.driverView(queue).current.queueText.indexOf("第 2 位") >= 0, true);
assert.strictEqual(fleet.move(queue, "D102", "top"), true);
assert.ok(fleet.driverView(queue).current.queueText.indexOf("第 1 位") >= 0);

const sample = fresh();
sample.orders[0].status = "待取样";
sample.orders[0].releaseHours = 1.5;
assert.strictEqual(fleet.act(sample, "D102", "sample_done"), true);
assert.strictEqual(fleet.orderView(sample, "D102").status, "原地等待放行");

console.log("tanker fleet ok");
