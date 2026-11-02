const assert = require("assert");
const Dispatch = require("./dispatch_engine.js");
const Data = require("./dispatch_data.js");

const orders = Data.generate();
assert.strictEqual(orders.length, 100);
const codes = {};
orders.forEach(function (o) { codes[o.code] = true; });
assert.strictEqual(Object.keys(codes).length, 100);

const demoA = orders.find(function (o) { return o.code === "TJ4-DEMO-A"; });
const demoB = orders.find(function (o) { return o.code === "TJ4-DEMO-B"; });
assert.strictEqual(demoA.status, "待供应链下达");
assert.strictEqual(demoA.releaseHours, 1.5);
assert.strictEqual(demoB.releaseHours, 3.5);

const unqualified = orders.find(function (o) { return o.status === "待采购转发" && !o.supplierQualified; });
assert.ok(unqualified, "need an unqualified supplier still at procurement");
const blocked = Dispatch.act(unqualified, "forward_purchase");
assert.strictEqual(blocked.ok, false);

const short = Dispatch.runScript(demoA, Dispatch.shortScript(demoA));
assert.strictEqual(short.ok, true, short.trace.filter(function (t) { return !t.ok; }).map(function (t) { return t.message; }).join(";"));
assert.strictEqual(short.order.status, "已断管离场");
assert.ok(short.trace.some(function (t) { return t.order.status === "原地等待放行"; }));
assert.ok(short.trace.some(function (t) { return t.order.status === "到场预告"; }));
assert.ok(short.trace.some(function (t) { return t.order.status === "待门卫核查"; }));

const long = Dispatch.runScript(demoB, Dispatch.longScript(demoB));
assert.strictEqual(long.ok, true, JSON.stringify(long.trace[long.trace.length - 1]));
assert.strictEqual(long.order.status, "已断管离场");
assert.ok(long.trace.some(function (t) { return t.order.status === "出厂等待放行"; }));
assert.ok(long.trace.some(function (t) { return t.order.status === "待重新入厂"; }));

const noCoa = Dispatch.act(Object.assign(Dispatch.clone(demoA), { status: "待供应商上报" }), "supplier_report", {
  plate: "津A演示9", driver: "张师傅", phone: "13800000000", coa: false,
});
assert.strictEqual(noCoa.ok, false);

const wrongBay = Dispatch.act(Object.assign(Dispatch.clone(demoA), { status: "待罐区入厂指令", plate: "津A1", coa: true }), "tank_in", { bay: "鹤管A" });
assert.strictEqual(wrongBay.ok, false);

const far = Dispatch.act(Object.assign(Dispatch.clone(demoA), { status: "在途", distanceKm: 80, plate: "津A1", coa: true }), "set_distance", { km: 40 });
assert.strictEqual(far.order.status, "在途");
const near = Dispatch.act(far.order, "set_distance", { km: 12 });
assert.strictEqual(near.order.status, "到场预告");
const gate = Dispatch.act(near.order, "set_distance", { km: 4 });
assert.strictEqual(gate.order.status, "待门卫核查");

const waste = orders.find(function (o) { return o.kind === "废液装车" && o.status === "待供应链下达" && o.receiverReady; });
let w = waste;
["issue_plan", "forward_purchase"].forEach(function (a) {
  const r = Dispatch.act(w, a);
  assert.strictEqual(r.ok, true, a + r.message);
  w = r.order;
});
const reported = Dispatch.act(w, "supplier_report", { plate: "津C演示1", driver: "赵师傅", phone: "13800002222", coa: false });
assert.strictEqual(reported.ok, true);

console.log("dispatch tests ok");
