function round1(n) {
  return Math.round((Number(n) + Number.EPSILON) * 10) / 10;
}

function fail(message) {
  return { ok: false, message: message };
}

function ok(message) {
  return { ok: true, message: message };
}

function requireStatus(order, list) {
  if (list.indexOf(order.status) < 0) return "当前是「" + order.status + "」，不能做这一步";
  return "";
}

function placeByDistance(order) {
  const km = Number(order.distanceKm);
  if (km < 5) {
    order.status = "待门卫核查";
    return "距厂 " + km + " 公里，请到门卫核验";
  }
  if (km <= 15) {
    order.status = "到场预告";
    return "距厂 " + km + " 公里，已通知门卫和综合办";
  }
  order.status = "在途";
  return "距厂 " + km + " 公里，还在途中";
}

function onBay(order) {
  return ["待收货递检", "待取样", "原地等待放行", "卸车中", "装车中"].indexOf(order.status) >= 0;
}

function apply(order, action, payload, ctx) {
  const p = payload || {};
  const tank = ctx.tank;
  const inbound = order.kind === "in";

  if (action === "set_distance") {
    const bad = requireStatus(order, ["在途", "到场预告"]);
    if (bad) return fail(bad);
    order.distanceKm = Number(p.km);
    return ok(placeByDistance(order));
  }

  if (action === "gate_pass") {
    const bad = requireStatus(order, ["待门卫核查"]);
    if (bad) return fail(bad);
    if (!order.plate) return fail("没有车牌，不能进厂");
    if (inbound && !order.coa) return fail("溶剂车没有 COA，门卫不能放行");
    order.status = inbound ? "待罐区入厂指令" : "待入厂装车";
    return ok("门卫已核验，等罐区安排车位");
  }

  if (action === "tank_wait_out") {
    const bad = requireStatus(order, ["待罐区入厂指令"]);
    if (bad) return fail(bad);
    if (!p.place) return fail("厂外等待要指定位置");
    order.waitPlace = p.place;
    order.status = "厂外等待";
    return ok("改到" + p.place + "等候");
  }

  if (action === "tank_in") {
    const allowed = inbound ? ["待罐区入厂指令", "厂外等待"] : ["待入厂装车"];
    const bad = requireStatus(order, allowed);
    if (bad) return fail(bad);
    if (!tank) return fail("没有对应储罐");
    if (tank.online === false) return fail(tank.code + " 液位中断，不能安排车位");
    if (p.bayId && p.bayId !== order.bayId) return fail("车位和这车的物料不一致");
    const free = round1(Number(tank.cap) - Number(tank.qty));
    if (inbound && free < Number(order.qty)) {
      return fail(tank.code + " 可用 " + free + " 吨，这车 " + order.qty + " 吨，不能进位");
    }
    if (!inbound && Number(tank.qty) < Number(order.qty)) {
      return fail(tank.code + " 现存 " + tank.qty + " 吨，不够装 " + order.qty + " 吨");
    }
    order.status = inbound ? "待收货递检" : "装车中";
    return ok(inbound ? "进入" + ctx.bayName + "，等库房收货" : "进入" + ctx.bayName + "，开始装车");
  }

  if (action === "receive") {
    const bad = requireStatus(order, ["待收货递检"]);
    if (bad) return fail(bad);
    order.rcvNo = order.rcvNo || ("RCV-" + String(order.code).slice(-3));
    order.status = "待取样";
    return ok("已记下收货。ERP 不回写。等取样");
  }

  if (action === "sample_done") {
    const bad = requireStatus(order, ["待取样"]);
    if (bad) return fail(bad);
    const hours = Number(order.releaseHours);
    order.batch = order.batch || ("BN-" + order.material + "-" + String(order.code).slice(-3));
    order.sampled = true;
    if (hours < 2) {
      order.waitMode = "原地等待";
      order.status = "原地等待放行";
      return ok("取样完成。放行约 " + hours + " 小时，留在车位等");
    }
    if (!p.place) return fail("放行要 " + hours + " 小时，出厂等待要指定位置");
    order.waitMode = "出厂等待";
    order.waitPlace = p.place;
    order.status = "出厂等待放行";
    return ok("取样完成。到" + p.place + "等放行");
  }

  if (action === "mark_release") {
    const bad = requireStatus(order, ["原地等待放行", "出厂等待放行"]);
    if (bad) return fail(bad);
    order.erpReleased = true;
    order.reportResult = "合格";
    return ok("已记下 ERP 放行结果。不回写 ERP");
  }

  if (action === "pull_release") {
    const bad = requireStatus(order, ["原地等待放行", "出厂等待放行"]);
    if (bad) return fail(bad);
    if (!order.erpReleased) return fail("ERP 里还没有放行，不能卸车");
    if (order.status === "原地等待放行") {
      order.status = "待置换卸车";
      return ok("放行已完成，可以在车位卸车");
    }
    order.status = "待重新入厂";
    return ok("放行已完成。车在厂外，等罐区叫号进厂");
  }

  if (action === "reenter") {
    const bad = requireStatus(order, ["待重新入厂"]);
    if (bad) return fail(bad);
    order.status = "待置换卸车";
    return ok("叫车进" + ctx.bayName);
  }

  if (action === "start_unload") {
    const bad = requireStatus(order, ["待置换卸车"]);
    if (bad) return fail(bad);
    if (!order.erpReleased) return fail("没有放行结果，不能卸车");
    order.status = "卸车中";
    return ok("开始卸入" + (tank ? tank.code : "储罐"));
  }

  if (action === "disconnect") {
    const bad = requireStatus(order, ["卸车中"]);
    if (bad) return fail(bad);
    if (!tank) return fail("没有对应储罐");
    const before = Number(tank.qty);
    if (before > 0) tank.batch = order.batch + "-M-" + tank.code;
    else tank.batch = order.batch;
    tank.qty = round1(before + Number(order.qty));
    order.mixBatch = tank.batch;
    order.status = "已断管离场";
    order.closed = true;
    return ok("卸完离场。罐内批号 " + tank.batch + "，现存 " + tank.qty + " 吨");
  }

  if (action === "weigh") {
    const bad = requireStatus(order, ["装车中"]);
    if (bad) return fail(bad);
    order.weight = Number(p.weight || order.qty);
    order.status = "待检斤联单";
    return ok("过磅 " + order.weight + " 吨，等联单确认");
  }

  if (action === "manifest") {
    const bad = requireStatus(order, ["待检斤联单"]);
    if (bad) return fail(bad);
    if (!ctx.receiver || !ctx.receiver.ready) return fail("接收商手续未齐，不能提交联单");
    const weight = Number(order.weight || order.qty);
    if (Number(ctx.receiver.quota) < weight) return fail("联单余量不足");
    if (!tank) return fail("没有对应储罐");
    ctx.receiver.quota = round1(Number(ctx.receiver.quota) - weight);
    tank.qty = round1(Number(tank.qty) - weight);
    order.manifestNo = "LD-" + String(order.code).slice(-3);
    order.status = "已离场";
    order.closed = true;
    return ok("联单 " + order.manifestNo + " 已确认，可以出厂");
  }

  if (action === "report_exception") {
    const bad = requireStatus(order, ["在途", "到场预告", "待确认发车"]);
    if (bad) return fail(bad);
    order.exception = p.text || "司机上报异常";
    order.statusBeforeException = order.status;
    order.status = "异常暂停";
    return ok("已暂停。等罐区处理后再走");
  }

  if (action === "resolve_exception") {
    const bad = requireStatus(order, ["异常暂停"]);
    if (bad) return fail(bad);
    order.exception = "";
    if (order.distanceKm == null) order.status = "待确认发车";
    else placeByDistance(order);
    return ok("异常已解除");
  }

  return fail("没有这个动作");
}

function instruction(order, bayName, tankCode) {
  const bay = bayName || "车位";
  const tank = tankCode || "储罐";
  const place = order.waitPlace || "厂外等候点";
  const map = {
    待供应商上报: "等待承运信息。确认后才能发车。",
    待确认发车: "车辆已登记。接到发车通知再出发。",
    在途: "按导航来厂。到厂前会通知你进哪一个车位。",
    到场预告: "即将到厂。在门外等候，不要自己进卸料位。",
    待门卫核查: "到门卫核验车牌。通过后再等罐区叫号。",
    待罐区入厂指令: "在门口等候叫号。",
    厂外等待: "到" + place + "等候。叫号前不要进卸料位。",
    待收货递检: "停在" + bay + "。等库房收货，先别卸。",
    待取样: "停在" + bay + "。等取样，先别卸。",
    原地等待放行: "留在" + bay + "。放行前不要卸车。",
    出厂等待放行: "到" + place + "等放行。放行前不要进卸料位。",
    待重新入厂: "化验已放行。在门口等罐区叫你进" + bay + "。",
    待置换卸车: "到" + bay + "，对接" + tank + "。",
    卸车中: "正在卸入" + tank + "。听现场指挥。",
    已断管离场: "可以出厂。这趟流程结束。",
    待入厂装车: "到" + bay + "装车。",
    装车中: "正在" + bay + "装车。装完去地磅。",
    待检斤联单: "去地磅过磅。联单确认后出厂。",
    已离场: "可以出厂。这趟流程结束。",
    异常暂停: "先停车。等罐区通知后再走。",
  };
  return map[order.status] || "等罐区通知。";
}

function goNow(order) {
  return ["待收货递检", "待取样", "原地等待放行", "待置换卸车", "卸车中", "装车中", "待入厂装车"].indexOf(order.status) >= 0;
}

function milestones(order) {
  const inbound = order.kind === "in";
  const names = inbound
    ? ["车辆", "在途", "门卫", "取样", "放行", "卸车", "离场"]
    : ["车辆", "在途", "门卫", "装车", "过磅", "离场"];
  const at = {
    待供应商上报: 0, 待确认发车: 0,
    在途: 1, 到场预告: 1, 异常暂停: 1,
    待门卫核查: 2,
    待罐区入厂指令: 3, 厂外等待: 3, 待收货递检: 3, 待取样: 3, 待入厂装车: 3,
    原地等待放行: 4, 出厂等待放行: 4, 待重新入厂: 4, 装车中: 3,
    待置换卸车: 5, 卸车中: 5, 待检斤联单: 4,
    已断管离场: 6, 已离场: inbound ? 6 : 5,
  };
  let index = at[order.status];
  if (index == null) index = 0;
  if (!inbound && order.status === "装车中") index = 3;
  if (!inbound && order.status === "待检斤联单") index = 4;
  if (!inbound && order.status === "已离场") index = 5;
  if (order.closed) index = names.length;
  return names.map(function (name, i) {
    return { name: name, state: i < index ? "done" : i === index ? "now" : "todo" };
  });
}

function mixPreview(order, tank) {
  if (!order || order.kind !== "in" || !tank || order.closed) return "";
  if (!order.batch) return "取样之后才会生成批号。罐里若还有料，卸完会写成新批号-M-储罐。";
  if (Number(tank.qty) <= 0) return "罐是空的，卸完批号用 " + order.batch + "。";
  const next = round1(Number(tank.qty) + Number(order.qty));
  return "罐内还有 " + tank.qty + " 吨。卸完先出库底料，再按 " + order.batch + "-M-" + tank.code + " 入库 " + next + " 吨。底料不重检。";
}

module.exports = {
  round1: round1,
  apply: apply,
  onBay: onBay,
  instruction: instruction,
  goNow: goNow,
  milestones: milestones,
  mixPreview: mixPreview,
};
