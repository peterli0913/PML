const assert = require("assert");
const Demand = require("./demand_engine.js");

const spread = Demand.hourlyDemand([
  { id: "A", project: "P", status: "未开始", mode: "持续", plannedStartHour: 0, durationHours: 10, qty: 10, progress: 0 },
], 24);
assert.strictEqual(Demand.round1(spread.demand[0]), 1);
assert.strictEqual(Demand.round1(spread.demand[9]), 1);
assert.strictEqual(Demand.round1(spread.demand[10]), 0);

const spike = Demand.hourlyDemand([
  { id: "B", project: "P", status: "未开始", mode: "单次", plannedStartHour: 5, durationHours: 1, qty: 8, progress: 0 },
], 12);
assert.strictEqual(spike.demand[5], 8);

const late = Demand.timing({ status: "未开始", plannedStartHour: -8, durationHours: 4, qty: 4, progress: 0 });
assert.strictEqual(late.start, 0);
assert.strictEqual(late.slip, 8);

const running = Demand.hourlyDemand([
  { id: "C", project: "P", status: "进行中", mode: "持续", plannedStartHour: -5, durationHours: 10, qty: 10, progress: 0.5 },
], 8);
assert.strictEqual(Demand.round1(running.demand[0]), 1);
assert.strictEqual(Demand.round1(running.demand[5]), 0);

const cycles = { arrival: 24, inspect: 6, release: 18, unload: 4, buffer: 2 };
const front = Demand.planSolvent({
  solvent: "甲醇",
  hours: 80,
  batches: [
    { id: "M1", project: "PRJ-甲醇", opNo: "OP1", status: "未开始", mode: "单次", plannedStartHour: 1, durationHours: 1, qty: 18, progress: 0 },
  ],
  inventory: { qty: 20, low: 8 },
  inbound: [],
  cycles: cycles,
  previous: null,
});
assert.strictEqual(front.leadHours, 52 > 48 ? 52 : front.leadHours);
assert.strictEqual(front.legacyQty, 0);
assert.ok(front.urgent);
assert.ok(front.suggestQty > 0);

const smooth = Demand.planSolvent({
  solvent: "DMF",
  hours: 30,
  batches: [
    { id: "D1", project: "P", status: "未开始", mode: "持续", plannedStartHour: 0, durationHours: 10, qty: 10, progress: 0 },
  ],
  inventory: { qty: 40, low: 10 },
  inbound: [{ hour: 4, qty: 0 }],
  cycles: { arrival: 2, inspect: 1, release: 1, unload: 1, buffer: 0 },
  previous: { qty: 0, arrivalHour: 5 },
});
assert.strictEqual(smooth.suggestQty, 0);

const changed = Demand.planSolvent({
  solvent: "ACN",
  hours: 40,
  batches: [
    { id: "E1", project: "P", status: "未开始", mode: "持续", plannedStartHour: 0, durationHours: 20, qty: 40, progress: 0 },
  ],
  inventory: { qty: 15, low: 8 },
  inbound: [],
  cycles: { arrival: 4, inspect: 1, release: 1, unload: 1, buffer: 2 },
  previous: { qty: 1, arrivalHour: 7 },
});
assert.ok(changed.suggestQty >= 1);
assert.ok(changed.arrivalChange);

console.log("demand tests ok", "甲醇建议", front.suggestQty, "加急", front.urgent);
