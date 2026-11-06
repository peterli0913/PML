const assert = require("assert");
const orders = require("./orders.js");

const state = orders.create();
assert.strictEqual(orders.driverView(state).current.instruction.indexOf("请等待") >= 0, true);
assert.strictEqual(orders.driverView(state).current.showWhere, false);
assert.strictEqual(orders.driverView(state).cars.length > 1, true);

const same = state.orders.filter(function (item) { return item.plate === "津A·W033"; });
assert.strictEqual(same.length, 2);
assert.notStrictEqual(same[0].material, same[1].material);
assert.notStrictEqual(same[0].id, same[1].id);

assert.strictEqual(orders.allow(state, "WO-04"), false);
orders.setPlate(state, "WO-04", "津A·W033");
assert.strictEqual(orders.confirm(state, "WO-04"), true);
assert.strictEqual(orders.orderView(state, "WO-04").status, "等候");
assert.strictEqual(orders.allow(state, "WO-04"), true);
assert.strictEqual(orders.bayView(state).rows.find(function (bay) { return bay.id === "B-WASTE"; }).occupant, "津A·W033");

const blocked = orders.create();
assert.strictEqual(blocked.orders.find(function (item) { return item.id === "WO-02"; }).status, "可进入");
blocked.orders.find(function (item) { return item.id === "WO-01"; }).bayId = "B-DMF";
blocked.orders.find(function (item) { return item.id === "WO-01"; }).status = "等候";
assert.strictEqual(orders.allow(blocked, "WO-01"), false);
assert.ok(blocked.toast.indexOf("不能进入") >= 0);

const fresh = orders.create();
const id = orders.createOrder(fresh, { material: "甲醇", qty: 10, planTime: "16:00" });
assert.strictEqual(orders.orderView(fresh, id).status, "待确认");
assert.strictEqual(orders.confirm(fresh, id), false);
fresh.orders.find(function (item) { return item.id === id; }).shipmentNo = "FH-2401";
assert.strictEqual(orders.pullPortal(fresh, id), true);
assert.strictEqual(orders.orderView(fresh, id).plate, "津A·D102");
assert.strictEqual(orders.confirm(fresh, id), true);
assert.strictEqual(orders.allow(fresh, id), true);
assert.strictEqual(orders.driverView(Object.assign(fresh, { focusId: id })).current.showWhere, true);
assert.strictEqual(orders.leave(fresh, id), true);
assert.strictEqual(orders.bayView(fresh).rows.find(function (bay) { return bay.id === "B-MEOH"; }).occupant, "");
assert.ok(fresh.log.some(function (line) { return line.orderId === id && line.to === "可进入" && line.who === "罐区"; }));

console.log("simple orders ok");
