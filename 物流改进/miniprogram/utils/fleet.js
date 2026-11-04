const flow = require("./flow.js");

function create() {
  const tanks = [
    { id: "PS01", code: "PS01", material: "甲醇", cap: 60, qty: 22, online: true, batch: "L126010171-M-PS01" },
    { id: "PS02", code: "PS02", material: "乙腈", cap: 50, qty: 8, online: true, batch: "BN-ACN-M-PS02" },
    { id: "PS03", code: "PS03", material: "DMF", cap: 80, qty: 36, online: true, batch: "L126010088-M-PS03" },
    { id: "PS04", code: "PS04", material: "IPAc", cap: 40, qty: 32, online: true, batch: "BN-IPAc-M-PS04" },
    { id: "WF01", code: "WF01", material: "废DMF", cap: 40, qty: 31, online: true, batch: "WF-DMF-M-WF01" },
  ];
  const bays = [
    { id: "B-MEOH", name: "甲醇位", material: "甲醇", tankId: "PS01" },
    { id: "B-ACN", name: "乙腈位", material: "乙腈", tankId: "PS02" },
    { id: "B-DMF", name: "DMF位", material: "DMF", tankId: "PS03" },
    { id: "B-IPAC", name: "IPAc位", material: "IPAc", tankId: "PS04" },
    { id: "B-WASTE", name: "废液位", material: "废DMF", tankId: "WF01" },
  ];
  const orders = [
    order({
      id: "D102", code: "TJ4-IN-018", kind: "in", material: "甲醇", qty: 16, plate: "津A·D102",
      driver: "张师傅", phone: "13800001018", status: "在途", rank: 20, bayId: "B-MEOH", tankId: "PS01",
      distanceKm: 40, coa: true, releaseHours: 1.5, planTime: "09:40", reportItems: "外观、水分",
    }),
    order({
      id: "A221", code: "TJ4-IN-021", kind: "in", material: "乙腈", qty: 12, plate: "津A·A221",
      driver: "李师傅", phone: "13800001021", status: "出厂等待放行", rank: 10, bayId: "B-ACN", tankId: "PS02",
      distanceKm: 2, coa: true, releaseHours: 6, waitPlace: "厂外停车场 2 号", waitMode: "出厂等待",
      batch: "BN-ACN-1121", sampled: true, reportResult: "合格", erpReleased: false, planTime: "08:10",
      reportItems: "外观、纯度、甲醛",
    }),
    order({
      id: "F018", code: "TJ4-IN-014", kind: "in", material: "DMF", qty: 18, plate: "津A·F018",
      driver: "王师傅", phone: "13800001014", status: "待置换卸车", rank: 5, bayId: "B-DMF", tankId: "PS03",
      distanceKm: 0, coa: true, releaseHours: 1, batch: "BN-DMF-1114", sampled: true, reportResult: "合格",
      erpReleased: true, planTime: "07:30", reportItems: "外观、水分",
    }),
    order({
      id: "I006", code: "TJ4-IN-009", kind: "in", material: "IPAc", qty: 16, plate: "津A·I006",
      driver: "赵师傅", phone: "13800001009", status: "待罐区入厂指令", rank: 30, bayId: "B-IPAC", tankId: "PS04",
      distanceKm: 1, coa: true, releaseHours: 4, planTime: "10:20", reportItems: "外观、水分",
    }),
    order({
      id: "W033", code: "TJ4-OUT-007", kind: "out", material: "废DMF", qty: 8, plate: "津A·W033",
      driver: "孙师傅", phone: "13800002007", status: "待入厂装车", rank: 40, bayId: "B-WASTE", tankId: "WF01",
      distanceKm: 1, coa: false, planTime: "11:00", receiver: "甲",
    }),
  ];
  return {
    role: "罐区",
    focusId: "D102",
    filter: "全部",
    toast: "按到货时间排队。点一辆车安排车位、卸车或出库。",
    yardPlace: "厂外停车场 2 号",
    tanks: tanks,
    bays: bays,
    orders: orders,
    receivers: { 甲: { ready: true, quota: 20 } },
  };
}

function order(seed) {
  return Object.assign({
    sampled: false, reportResult: "", erpReleased: false, batch: "", rcvNo: "",
    weight: 0, manifestNo: "", closed: false, exception: "", receiver: "",
    waitPlace: "", waitMode: "",
  }, seed);
}

function find(list, id) {
  return list.find(function (item) { return item.id === id; });
}

function bayOf(state, id) { return find(state.bays, id); }
function tankOf(state, id) { return find(state.tanks, id); }
function orderOf(state, id) { return find(state.orders, id); }

function waiting(state, bayId) {
  return state.orders.filter(function (item) {
    return item.bayId === bayId && !item.closed && !flow.onBay(item);
  }).sort(function (a, b) { return a.rank - b.rank; });
}

function queueNo(state, item) {
  if (item.closed) return { n: 0, ahead: 0, text: "这趟已结束" };
  if (flow.onBay(item)) return { n: 0, ahead: 0, text: "正在这个车位作业" };
  const list = waiting(state, item.bayId);
  const index = list.findIndex(function (row) { return row.id === item.id; });
  const n = index + 1;
  const ahead = Math.max(0, n - 1);
  const bayName = bayOf(state, item.bayId).name;
  const text = ahead === 0 ? bayName + " 第 1 位，前面没有车" : bayName + " 第 " + n + " 位，前面 " + ahead + " 辆";
  return { n: n, ahead: ahead, text: text };
}

function act(state, id, action, payload) {
  const item = orderOf(state, id);
  if (!item) {
    state.toast = "没有这辆车";
    return false;
  }
  const tank = tankOf(state, item.tankId);
  const bay = bayOf(state, item.bayId);
  const result = flow.apply(item, action, payload, {
    tank: tank,
    bayName: bay ? bay.name : "",
    receiver: state.receivers[item.receiver],
  });
  state.toast = result.message;
  return result.ok;
}

function move(state, id, how) {
  const item = orderOf(state, id);
  if (!item || item.closed || flow.onBay(item)) {
    state.toast = "这辆车不在等候队列里";
    return false;
  }
  const list = waiting(state, item.bayId);
  const index = list.findIndex(function (row) { return row.id === id; });
  if (how === "top") {
    if (index <= 0) {
      state.toast = "已经在最前";
      return false;
    }
    item.rank = list[0].rank - 1;
    state.toast = item.plate + " 已提到最前";
    return true;
  }
  if (index <= 0) {
    state.toast = "前面没有车";
    return false;
  }
  const prev = list[index - 1];
  const rank = item.rank;
  item.rank = prev.rank;
  prev.rank = rank;
  state.toast = item.plate + " 前移一位";
  return true;
}

function setRole(state, role) {
  state.role = role;
  state.toast = role === "司机" ? "司机只看自己的去向和当前指令。" : "罐区可以安排车位、储罐和装卸。";
}

function setFocus(state, id) {
  if (!orderOf(state, id)) return;
  state.focusId = id;
}

function driverCard(state, item) {
  const bay = bayOf(state, item.bayId);
  const tank = tankOf(state, item.tankId);
  const q = queueNo(state, item);
  return {
    id: item.id,
    plate: item.plate,
    material: item.material,
    qty: item.qty,
    kind: item.kind === "in" ? "入库" : "出库",
    status: item.status,
    bay: bay.name,
    tank: tank.code,
    goNow: flow.goNow(item),
    whereLabel: flow.goNow(item) ? "现在去" : "计划去向",
    instruction: flow.instruction(item, bay.name, tank.code),
    queueText: q.text,
    steps: flow.milestones(item),
    canException: ["在途", "到场预告", "待确认发车"].indexOf(item.status) >= 0,
  };
}

function driverView(state) {
  const cards = state.orders.map(function (item) { return driverCard(state, item); });
  const current = cards.find(function (item) { return item.id === state.focusId; }) || cards[0];
  return {
    role: state.role,
    toast: state.toast,
    current: current,
    cars: cards.map(function (item) {
      return { id: item.id, plate: item.plate, on: item.id === current.id };
    }),
  };
}

function tagOf(status) {
  if (status === "卸车中" || status === "装车中") return "work";
  if (status.indexOf("已") === 0) return "done";
  if (status.indexOf("待") === 0 || status.indexOf("等待") >= 0) return "wait";
  return "";
}

function orderBrief(state, item) {
  const bay = bayOf(state, item.bayId);
  const tank = tankOf(state, item.tankId);
  const q = queueNo(state, item);
  return {
    id: item.id,
    plate: item.plate,
    material: item.material,
    qty: item.qty,
    kind: item.kind === "in" ? "入库" : "出库",
    status: item.status,
    bay: bay.name,
    tank: tank.code,
    planTime: item.planTime,
    queueText: q.text,
    closed: !!item.closed,
    tag: tagOf(item.status),
  };
}

function queueView(state) {
  const filter = state.filter || "全部";
  const rows = state.orders.filter(function (item) {
    if (filter === "入库") return item.kind === "in";
    if (filter === "出库") return item.kind === "out";
    return true;
  }).slice().sort(function (a, b) {
    if (!!a.closed !== !!b.closed) return a.closed ? 1 : -1;
    return a.rank - b.rank;
  }).map(function (item) { return orderBrief(state, item); });
  return { role: state.role, toast: state.toast, filter: filter, rows: rows };
}

function bayView(state) {
  return {
    role: state.role,
    toast: state.toast,
    rows: state.bays.map(function (bay) {
      const tank = tankOf(state, bay.tankId);
      const occupant = state.orders.find(function (item) { return item.bayId === bay.id && flow.onBay(item); });
      const wait = waiting(state, bay.id).length;
      return {
        id: bay.id,
        name: bay.name,
        material: bay.material,
        tank: tank.code,
        free: flow.round1(tank.cap - tank.qty),
        occupant: occupant ? occupant.plate : "",
        wait: wait,
      };
    }),
  };
}

function tankView(state) {
  return {
    role: state.role,
    toast: state.toast,
    rows: state.tanks.map(function (tank) {
      const bay = state.bays.find(function (item) { return item.tankId === tank.id; });
      return {
        id: tank.id,
        code: tank.code,
        material: tank.material,
        qty: tank.qty,
        cap: tank.cap,
        free: flow.round1(tank.cap - tank.qty),
        batch: tank.batch,
        level: Math.max(0, Math.min(100, Math.round(tank.qty / tank.cap * 100))),
        online: tank.online !== false,
        bay: bay ? bay.name : "",
      };
    }),
  };
}

function actionsFor(state, item) {
  const actions = [];
  function add(action, label, extra) {
    actions.push(Object.assign({ action: action, label: label, km: "", place: "" }, extra || {}));
  }
  if (item.status === "在途" || item.status === "到场预告") {
    add("set_distance", "距厂 12 公里", { km: "12" });
    add("set_distance", "距厂 3 公里", { km: "3" });
  }
  if (item.status === "待门卫核查") add("gate_pass", "记下门卫已核验");
  if (item.status === "待罐区入厂指令") {
    add("tank_in", "进入" + bayOf(state, item.bayId).name);
    add("tank_wait_out", "改到厂外等候", { place: state.yardPlace });
  }
  if (item.status === "厂外等待" || item.status === "待入厂装车") add("tank_in", "进入" + bayOf(state, item.bayId).name);
  if (item.status === "待收货递检") add("receive", "记下已收货");
  if (item.status === "待取样") add("sample_done", "记下取样完成", { place: state.yardPlace });
  if (item.status === "原地等待放行" || item.status === "出厂等待放行") {
    if (!item.erpReleased) add("mark_release", "记下 ERP 已放行");
    add("pull_release", "按放行结果往下走");
  }
  if (item.status === "待重新入厂") add("reenter", "叫车进厂");
  if (item.status === "待置换卸车") add("start_unload", "开始卸车");
  if (item.status === "卸车中") add("disconnect", "断管离场");
  if (item.status === "装车中") add("weigh", "记下过磅");
  if (item.status === "待检斤联单") add("manifest", "确认联单并离场");
  if (item.status === "异常暂停") add("resolve_exception", "解除异常");
  return actions;
}

function orderView(state, id) {
  const item = orderOf(state, id);
  if (!item) return { missing: true, toast: state.toast, role: state.role };
  const bay = bayOf(state, item.bayId);
  const tank = tankOf(state, item.tankId);
  const q = queueNo(state, item);
  return {
    missing: false,
    role: state.role,
    toast: state.toast,
    id: item.id,
    plate: item.plate,
    driver: item.driver,
    phone: item.phone,
    material: item.material,
    qty: item.qty,
    kind: item.kind === "in" ? "入库" : "出库",
    status: item.status,
    bay: bay.name,
    tank: tank.code,
    free: flow.round1(tank.cap - tank.qty),
    batch: item.batch || "取样后生成",
    tankBatch: tank.batch,
    coa: item.kind === "in" ? (item.coa ? "已附" : "没有") : "出库不需要",
    sample: item.sampled ? "已取样" : "未取样",
    result: item.reportResult || "待出",
    release: item.erpReleased ? "ERP 已放行" : "ERP 未放行",
    items: item.kind === "in" ? item.reportItems : "出库看联单，不看溶剂报告",
    mix: flow.mixPreview(item, tank),
    queueText: q.text,
    canMove: !item.closed && !flow.onBay(item),
    steps: flow.milestones(item),
    actions: actionsFor(state, item),
    closed: !!item.closed,
  };
}

module.exports = {
  create: create,
  act: act,
  move: move,
  setRole: setRole,
  setFocus: setFocus,
  queueView: queueView,
  bayView: bayView,
  tankView: tankView,
  orderView: orderView,
  driverView: driverView,
};
