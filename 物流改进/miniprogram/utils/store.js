const Demand = require("./demand.js");

function create() {
  return {
    role: "生产经理",
    toast: "看板已抓取当前进度和周计划。改周计划后，这一页和小时需求一起变。",
    solvent: "甲醇",
    cycles: { arrival: 24, inspect: 6, release: 18, unload: 4, buffer: 5 },
    inventories: {
      DMF: { qty: 36, low: 12, level: 62 },
      ACN: { qty: 28, low: 10, level: 48 },
      IPAc: { qty: 14, low: 6, level: 22 },
      甲醇: { qty: 20, low: 8, level: 35 },
    },
    inbound: {
      DMF: [{ hour: 30, qty: 16 }],
      ACN: [{ hour: 18, qty: 8 }],
      IPAc: [],
      甲醇: [],
    },
    official: {},
    weekly: [
      { id: "W1", project: "PRJ-2408", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", manager: "王经理", weekQty: 24 },
      { id: "W2", project: "PRJ-2411", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", manager: "王经理", weekQty: 18 },
      { id: "W3", project: "PRJ-2412", workshop: "2号厂房", solvent: "ACN", materialCode: "SOL-ACN", manager: "赵经理", weekQty: 22 },
      { id: "W4", project: "PRJ-2418", workshop: "1号厂房", solvent: "IPAc", materialCode: "SOL-IPAc", manager: "陈经理", weekQty: 16 },
      { id: "W5", project: "PRJ-2404", workshop: "3号厂房", solvent: "甲醇", materialCode: "SOL-MEOH", manager: "周经理", weekQty: 18 },
    ],
    operations: [
      { id: "OP-12", step: "投料", mode: "持续", durationHours: 36 },
      { id: "OP-03", step: "补料", mode: "持续", durationHours: 30 },
      { id: "OP-07", step: "滴加", mode: "持续", durationHours: 48 },
      { id: "OP-02", step: "投料", mode: "持续", durationHours: 16 },
      { id: "OP-01", step: "一次投入", mode: "单次", durationHours: 1 },
    ],
    batches: [
      { id: "B01", weekId: "W1", opId: "OP-12", step: "投料", opNo: "OP-12", manager: "王经理", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", project: "PRJ-2408", qty: 24, mode: "持续", plannedStartHour: -8, durationHours: 36, progress: 0.4, status: "进行中" },
      { id: "B02", weekId: "W2", opId: "OP-03", step: "补料", opNo: "OP-03", manager: "王经理", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", project: "PRJ-2411", qty: 18, mode: "持续", plannedStartHour: 20, durationHours: 30, progress: 0, status: "未开始" },
      { id: "B04", weekId: "W3", opId: "OP-07", step: "滴加", opNo: "OP-07", manager: "赵经理", workshop: "2号厂房", solvent: "ACN", materialCode: "SOL-ACN", project: "PRJ-2412", qty: 22, mode: "持续", plannedStartHour: 8, durationHours: 48, progress: 0, status: "未开始" },
      { id: "B06", weekId: "W4", opId: "OP-02", step: "投料", opNo: "OP-02", manager: "陈经理", workshop: "1号厂房", solvent: "IPAc", materialCode: "SOL-IPAc", project: "PRJ-2418", qty: 16, mode: "持续", plannedStartHour: -10, durationHours: 16, progress: 0, status: "未开始" },
      { id: "B08", weekId: "W5", opId: "OP-01", step: "一次投入", opNo: "OP-01", manager: "周经理", workshop: "3号厂房", solvent: "甲醇", materialCode: "SOL-MEOH", project: "PRJ-2404", qty: 18, mode: "单次", plannedStartHour: 1, durationHours: 1, progress: 0, status: "未开始" },
    ],
  };
}

function round1(n) { return Demand.round1(n); }

function weekSum(state) {
  return round1(state.weekly.reduce(function (a, w) { return a + Number(w.weekQty); }, 0));
}

function batchSum(state) {
  return round1(state.batches.reduce(function (a, b) { return a + Number(b.qty); }, 0));
}

function setWeekQty(state, id, qty) {
  const row = state.weekly.find(function (w) { return w.id === id; });
  row.weekQty = Number(qty);
  const list = state.batches.filter(function (b) { return b.weekId === id && b.status !== "完成"; });
  const sum = list.reduce(function (a, b) { return a + Number(b.qty); }, 0);
  if (list.length && sum > 0) {
    const factor = Number(qty) / sum;
    list.forEach(function (b) { b.qty = round1(Number(b.qty) * factor); });
  } else if (list.length) {
    list[0].qty = Number(qty);
  }
  state.toast = row.project + " " + row.solvent + " 周计划改为 " + qty + " 吨，已分摊到未完成批次，看板和小时需求已更新。";
}

function setBatchField(state, id, field, value) {
  const batch = state.batches.find(function (b) { return b.id === id; });
  batch[field] = Number(value);
  if (field === "qty") {
    const row = state.weekly.find(function (w) { return w.id === batch.weekId; });
    row.weekQty = round1(state.batches.filter(function (b) { return b.weekId === row.id; }).reduce(function (a, b) { return a + Number(b.qty); }, 0));
    state.toast = batch.project + " 批次需求已改，周计划同步为 " + row.weekQty + " 吨。";
  } else {
    state.toast = batch.project + " 的批次清单已更新，看板会按新进度抓取。";
  }
}

function applyDuration(state, opId) {
  const op = state.operations.find(function (item) { return item.id === opId; });
  let n = 0;
  state.batches.forEach(function (b) {
    if (b.opId === op.id && b.status !== "完成") {
      b.durationHours = Number(op.durationHours);
      b.mode = op.mode;
      n += 1;
    }
  });
  state.toast = op.id + " 标准时长 " + op.durationHours + " 小时，已应用到 " + n + " 个未完成批次。";
}

function planOf(state, name) {
  return Demand.planSolvent({
    solvent: name,
    hours: 168,
    batches: state.batches.filter(function (b) { return b.solvent === name; }),
    inventory: state.inventories[name],
    inbound: state.inbound[name],
    cycles: state.cycles,
    previous: state.official[name] || null,
  });
}

function freeze(state) {
  ["DMF", "ACN", "IPAc", "甲醇"].forEach(function (name) {
    const plan = planOf(state, name);
    state.official[name] = { qty: plan.suggestQty, arrivalHour: plan.suggestArrivalHour };
  });
  state.toast = "12 小时计算已定稿。之后再改周计划或时长，会重新出现到货更改。";
}

module.exports = {
  create: create,
  weekSum: weekSum,
  batchSum: batchSum,
  setWeekQty: setWeekQty,
  setBatchField: setBatchField,
  applyDuration: applyDuration,
  planOf: planOf,
  freeze: freeze,
};
