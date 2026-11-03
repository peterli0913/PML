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

function canEdit(state) { return state.role === "生产经理"; }

function finite(value) {
  if (value === "" || value == null) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function weekSum(state) {
  return round1(state.weekly.reduce(function (a, w) { return a + Number(w.weekQty); }, 0));
}

function batchSum(state) {
  return round1(state.batches.reduce(function (a, b) { return a + Number(b.qty); }, 0));
}

function setWeekQty(state, id, qty) {
  if (!canEdit(state)) {
    state.toast = "物流计划员只读。周计划由生产经理修改。";
    return false;
  }
  const n = finite(qty);
  if (n == null || n < 0) {
    state.toast = "周计划需要填大于等于 0 的吨数。";
    return false;
  }
  const row = state.weekly.find(function (w) { return w.id === id; });
  row.weekQty = n;
  const list = state.batches.filter(function (b) { return b.weekId === id && b.status !== "完成"; });
  const sum = list.reduce(function (a, b) { return a + Number(b.qty); }, 0);
  if (list.length && sum > 0) {
    const factor = n / sum;
    list.forEach(function (b) { b.qty = round1(Number(b.qty) * factor); });
  } else if (list.length) {
    list[0].qty = n;
  }
  state.toast = row.project + " " + row.solvent + " 周计划改为 " + n + " 吨，已分摊到未完成批次，看板和小时需求已更新。";
  return true;
}

function setBatchField(state, id, field, value) {
  if (!canEdit(state)) {
    state.toast = "物流计划员只读。批次清单由生产经理修改。";
    return false;
  }
  const batch = state.batches.find(function (b) { return b.id === id; });
  const n = finite(value);
  if (n == null) {
    state.toast = "请填写数字。距开始可以为负数，表示计划时点已过。";
    return false;
  }
  if (field === "qty" && n < 0) {
    state.toast = "需求量不能为负。";
    return false;
  }
  if (field === "durationHours" && n <= 0) {
    state.toast = "操作时长要大于 0 小时。";
    return false;
  }
  if (field === "progress" && (n < 0 || n > 1)) {
    state.toast = "进度填 0 到 1，例如完成四成填 0.4。";
    return false;
  }
  batch[field] = n;
  if (field === "qty") {
    const row = state.weekly.find(function (w) { return w.id === batch.weekId; });
    row.weekQty = round1(state.batches.filter(function (b) { return b.weekId === row.id; }).reduce(function (a, b) { return a + Number(b.qty); }, 0));
    state.toast = batch.project + " 批次需求已改，周计划同步为 " + row.weekQty + " 吨。";
  } else {
    state.toast = batch.project + " 的批次清单已更新，看板和小时需求会按新进度计算。";
  }
  return true;
}

function setDuration(state, opId, hours) {
  if (!canEdit(state)) {
    state.toast = "物流计划员只读。操作时长由生产经理修改。";
    return false;
  }
  const n = finite(hours);
  if (n == null || n <= 0) {
    state.toast = "标准时长要大于 0 小时。";
    return false;
  }
  const op = state.operations.find(function (item) { return item.id === opId; });
  op.durationHours = n;
  return true;
}

function applyDuration(state, opId) {
  if (!canEdit(state)) {
    state.toast = "物流计划员只读。操作时长由生产经理修改。";
    return false;
  }
  const op = state.operations.find(function (item) { return item.id === opId; });
  if (!op || !(Number(op.durationHours) > 0)) {
    state.toast = "标准时长要大于 0 小时。";
    return false;
  }
  let n = 0;
  state.batches.forEach(function (b) {
    if (b.opId === op.id && b.status !== "完成") {
      b.durationHours = Number(op.durationHours);
      b.mode = op.mode;
      n += 1;
    }
  });
  state.toast = op.id + " 标准时长 " + op.durationHours + " 小时，已应用到 " + n + " 个未完成批次。";
  return true;
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

function demandView(state) {
  return {
    role: state.role,
    toast: state.toast,
    canEdit: canEdit(state),
    total: weekSum(state),
    rows: state.weekly.map(function (w) {
      const sum = state.batches.filter(function (b) { return b.weekId === w.id; }).reduce(function (a, b) { return a + Number(b.qty); }, 0);
      return Object.assign({}, w, { batchQty: round1(sum) });
    }),
  };
}

function batchView(state) {
  return { role: state.role, toast: state.toast, canEdit: canEdit(state), rows: state.batches };
}

function durationView(state) {
  return {
    role: state.role,
    toast: state.toast,
    canEdit: canEdit(state),
    rows: state.operations.map(function (op) {
      return Object.assign({}, op, {
        count: state.batches.filter(function (b) { return b.opId === op.id && b.status !== "完成"; }).length,
      });
    }),
  };
}

function boardView(state) {
  const running = state.batches.filter(function (b) { return b.status === "进行中"; }).length;
  const late = state.batches.filter(function (b) { return b.status === "未开始" && Number(b.plannedStartHour) <= -4; }).length;
  const weeks = state.weekly.map(function (w) {
    const list = state.batches.filter(function (b) { return b.weekId === w.id; });
    const qty = list.reduce(function (a, b) { return a + Number(b.qty); }, 0) || 1;
    const pct = Math.round(list.reduce(function (a, b) { return a + Number(b.qty) * Number(b.progress || 0); }, 0) / qty * 100);
    return Object.assign({}, w, { pct: pct, low: pct < 30 });
  });
  const progress = state.batches.map(function (b) {
    const slip = b.status === "未开始" && b.plannedStartHour < 0;
    return {
      id: b.id,
      title: b.project + " " + b.opNo,
      solvent: b.solvent,
      qty: b.qty,
      pct: Math.round(Number(b.progress) * 100),
      slip: slip,
      statusText: slip ? "延误 " + (-b.plannedStartHour) + " 小时" : b.status,
    };
  });
  const stocks = ["DMF", "ACN", "IPAc", "甲醇"].map(function (name) {
    const week = round1(state.weekly.filter(function (w) { return w.solvent === name; }).reduce(function (a, w) { return a + Number(w.weekQty); }, 0));
    return { name: name, qty: state.inventories[name].qty, week: week, level: state.inventories[name].level, low: state.inventories[name].level < 30 };
  });
  return {
    role: state.role,
    toast: state.toast,
    canEdit: canEdit(state),
    total: weekSum(state),
    batchTotal: batchSum(state),
    diff: round1(weekSum(state) - batchSum(state)),
    running: running,
    late: late,
    weeks: weeks,
    progress: progress,
    stocks: stocks,
  };
}

function hourlyView(state, solvent) {
  const names = ["DMF", "ACN", "IPAc", "甲醇"];
  const name = names.indexOf(solvent) >= 0 ? solvent : "甲醇";
  const plan = planOf(state, name);
  const pills = names.map(function (item) {
    const current = planOf(state, item);
    return {
      name: item,
      mark: current.urgent ? "赶不上" : current.suggestQty > 0 ? "要补" : "够用",
      on: item === name,
    };
  });
  const rawDays = [];
  let maxDay = 0;
  for (let d = 0; d < 7; d++) {
    let qty = 0;
    for (let h = 0; h < 24; h++) qty += plan.demand[d * 24 + h] || 0;
    qty = round1(qty);
    rawDays.push(qty);
    if (qty > maxDay) maxDay = qty;
  }
  const days = rawDays.map(function (qty, d) {
    return {
      label: "第" + (d + 1) + "天",
      qty: qty,
      width: maxDay ? Math.round(qty / maxDay * 100) : 0,
      end: plan.projected[d * 24 + 23],
    };
  });
  const sampled = [];
  for (let h = 0; h < plan.projected.length; h += 6) sampled.push({ h: h, v: plan.projected[h] });
  const min = Math.min.apply(null, sampled.map(function (item) { return item.v; }).concat([plan.floor, 0]));
  const max = Math.max.apply(null, sampled.map(function (item) { return item.v; }).concat([plan.floor]));
  const span = Math.max(0.1, max - min);
  const samples = sampled.map(function (item) {
    return {
      h: item.h,
      height: Math.max(4, Math.round(((item.v - min) / span) * 120)),
      below: item.v < plan.floor,
    };
  });
  return {
    role: state.role,
    toast: state.toast,
    canEdit: canEdit(state),
    solvent: name,
    pills: pills,
    suggestQty: plan.suggestQty,
    legacyQty: plan.legacyQty,
    leadHours: plan.leadHours,
    totalDemand: plan.totalDemand,
    startOnHand: plan.startOnHand,
    urgent: plan.urgent,
    stockoutHour: plan.stockoutHour,
    delays: plan.delays,
    changeText: plan.arrivalChange ? plan.arrivalChange.text : "",
    floor: plan.floor,
    days: days,
    samples: samples,
  };
}

module.exports = {
  create: create,
  weekSum: weekSum,
  batchSum: batchSum,
  setWeekQty: setWeekQty,
  setBatchField: setBatchField,
  setDuration: setDuration,
  applyDuration: applyDuration,
  planOf: planOf,
  freeze: freeze,
  demandView: demandView,
  batchView: batchView,
  durationView: durationView,
  boardView: boardView,
  hourlyView: hourlyView,
};
