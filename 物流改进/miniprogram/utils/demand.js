function round1(n) {
  return Math.round((Number(n) + Number.EPSILON) * 10) / 10;
}

function overlap(a0, a1, b0, b1) {
  return Math.max(0, Math.min(a1, b1) - Math.max(a0, b0));
}

function timing(batch) {
  if (batch.status === "完成") return null;
  if (batch.status === "进行中") {
    const left = Math.max(0, 1 - Number(batch.progress || 0));
    return {
      start: 0,
      hours: Math.max(0.1, Number(batch.durationHours) * left),
      qty: Number(batch.qty) * left,
      slip: 0,
    };
  }
  const planned = Number(batch.plannedStartHour);
  const slip = planned < 0 ? -planned : 0;
  return {
    start: planned + slip,
    hours: Math.max(0.1, Number(batch.durationHours) || 0.1),
    qty: Number(batch.qty),
    slip: slip,
  };
}

function hourlyDemand(batches, hours) {
  const demand = [];
  const parts = [];
  for (let h = 0; h < hours; h++) {
    demand.push(0);
    parts.push([]);
  }
  batches.forEach(function (batch) {
    const when = timing(batch);
    if (!when || when.qty <= 0) return;
    if (batch.mode === "单次") {
      const h = Math.floor(when.start);
      if (h >= 0 && h < hours) {
        demand[h] += when.qty;
        parts[h].push({ id: batch.id, qty: when.qty, project: batch.project });
      }
      return;
    }
    const rate = when.qty / when.hours;
    for (let h = 0; h < hours; h++) {
      const piece = overlap(h, h + 1, when.start, when.start + when.hours);
      if (piece <= 0) continue;
      const qty = rate * piece;
      demand[h] += qty;
      parts[h].push({ id: batch.id, qty: qty, project: batch.project });
    }
  });
  return { demand: demand, parts: parts };
}

function projectInventory(demand, arrivals, startOnHand) {
  const projected = [];
  let onHand = startOnHand;
  for (let h = 0; h < demand.length; h++) {
    onHand = onHand - demand[h] + (arrivals[h] || 0);
    projected.push(onHand);
  }
  return projected;
}

function leadHours(cycles) {
  return Number(cycles.arrival) + Number(cycles.inspect) + Number(cycles.release) + Number(cycles.unload);
}

function suggest(projected, floor, lead) {
  let stockoutHour = null;
  let maxGap = 0;
  let gapHour = null;
  for (let h = 0; h < projected.length; h++) {
    if (projected[h] < floor && stockoutHour == null) stockoutHour = h;
    if (h >= lead) {
      const gap = floor - projected[h];
      if (gap > maxGap) {
        maxGap = gap;
        gapHour = h;
      }
    }
  }
  return {
    qty: round1(Math.max(0, maxGap)),
    stockoutHour: stockoutHour,
    gapHour: gapHour,
    arrivalHour: lead,
    urgent: stockoutHour != null && stockoutHour < lead,
  };
}

function legacyQty(totalDemand, onHand, inbound, low) {
  return round1(Math.max(0, totalDemand - onHand - inbound, low - onHand, 0));
}

function delayAlerts(batches) {
  return batches.filter(function (batch) {
    return batch.status === "未开始" && Number(batch.plannedStartHour) <= -4;
  }).map(function (batch) {
    return {
      id: batch.id,
      text: batch.project + " " + batch.opNo + " 已过计划开工 " + (-Number(batch.plannedStartHour)) + " 小时，需求平移到当前",
    };
  });
}

function arrivalChange(previous, next) {
  if (!previous) return null;
  const qtyShift = Math.abs(Number(previous.qty) - Number(next.qty));
  const hourShift = Math.abs(Number(previous.arrivalHour) - Number(next.arrivalHour));
  if (qtyShift < 1 && hourShift < 12) return null;
  return {
    text: "到货建议由 " + previous.qty + " 吨、第 " + previous.arrivalHour + " 小时，改为 " + next.qty + " 吨、第 " + next.arrivalHour + " 小时",
  };
}

function planSolvent(spec) {
  const hours = spec.hours || 168;
  const batches = spec.batches;
  const built = hourlyDemand(batches, hours);
  const arrivals = [];
  for (let h = 0; h < hours; h++) arrivals.push(0);
  (spec.inbound || []).forEach(function (item) {
    const h = Math.max(0, Math.min(hours - 1, Math.floor(item.hour)));
    arrivals[h] += Number(item.qty);
  });
  const startOnHand = Number(spec.inventory.qty) + Number(spec.releasedNotUnloaded || 0);
  const projected = projectInventory(built.demand, arrivals, startOnHand);
  const floor = Number(spec.inventory.low) + Number(spec.cycles.buffer);
  const lead = leadHours(spec.cycles);
  const advice = suggest(projected, floor, lead);
  const totalDemand = built.demand.reduce(function (a, b) { return a + b; }, 0);
  const inboundQty = (spec.inbound || []).reduce(function (a, b) { return a + Number(b.qty); }, 0);
  const focus = advice.gapHour == null ? advice.stockoutHour : advice.gapHour;
  return {
    solvent: spec.solvent,
    projected: projected.map(round1),
    floor: floor,
    leadHours: lead,
    startOnHand: round1(startOnHand),
    totalDemand: round1(totalDemand),
    suggestQty: advice.qty,
    suggestArrivalHour: advice.arrivalHour,
    stockoutHour: advice.stockoutHour,
    urgent: advice.urgent,
    legacyQty: legacyQty(totalDemand, startOnHand, inboundQty, Number(spec.inventory.low)),
    delays: delayAlerts(batches),
    arrivalChange: arrivalChange(spec.previous, { qty: advice.qty, arrivalHour: advice.arrivalHour }),
  };
}

module.exports = { round1: round1, planSolvent: planSolvent };
