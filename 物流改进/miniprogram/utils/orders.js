function create() {
  const bays = [
    { id: "B-MEOH", name: "甲醇鹤位", material: "甲醇", tank: "甲醇罐" },
    { id: "B-DMF", name: "DMF鹤位", material: "DMF", tank: "DMF罐" },
    { id: "B-ACN", name: "乙腈鹤位", material: "乙腈", tank: "乙腈罐" },
    { id: "B-WASTE", name: "废液鹤位", material: "废液", tank: "废液罐" },
  ];
  const portal = [
    { shipmentNo: "FH-2401", plate: "津A·D102", driver: "张师傅", coa: "已附", qualification: "槽车资质有效" },
    { shipmentNo: "FH-2402", plate: "津A·F018", driver: "王师傅", coa: "已附", qualification: "槽车资质有效" },
  ];
  const orders = [
    row({ id: "WO-01", kind: "in", material: "甲醇", qty: 16, planTime: "09:40", bayId: "B-MEOH", plate: "津A·D102", driver: "张师傅", shipmentNo: "FH-2401", status: "等候", coa: "已附", qualification: "槽车资质有效" }),
    row({ id: "WO-02", kind: "in", material: "DMF", qty: 18, planTime: "07:30", bayId: "B-DMF", plate: "津A·F018", driver: "王师傅", shipmentNo: "FH-2402", status: "可进入", coa: "已附", qualification: "槽车资质有效" }),
    row({ id: "WO-03", kind: "out", material: "废DMF", qty: 8, planTime: "08:30", bayId: "B-WASTE", plate: "津A·W033", driver: "孙师傅", shipmentNo: "", status: "已离开", coa: "出库不附", qualification: "随车" }),
    row({ id: "WO-04", kind: "out", material: "废IPAc", qty: 6, planTime: "15:00", bayId: "B-WASTE", plate: "津A·W033", driver: "孙师傅", shipmentNo: "", status: "待确认", coa: "出库不附", qualification: "随车" }),
  ];
  return {
    role: "厂内",
    focusId: "WO-01",
    filter: "全部",
    nextNo: 5,
    toast: "今天的工单。供应链补车牌，罐区点允许进入和已离开。",
    bays: bays,
    portal: portal,
    orders: orders,
    log: [],
  };
}

function row(seed) {
  return Object.assign({ driver: "", shipmentNo: "", coa: "", qualification: "", plate: "" }, seed);
}

function find(list, id) {
  return list.find(function (item) { return item.id === id; });
}

function bayOf(state, id) { return find(state.bays, id); }
function orderOf(state, id) { return find(state.orders, id); }

function bayFor(state, material) {
  if (String(material).indexOf("废") === 0) return find(state.bays, "B-WASTE");
  return state.bays.find(function (bay) { return bay.material === material; });
}

function occupied(state, bayId, exceptId) {
  return state.orders.find(function (item) {
    return item.bayId === bayId && item.status === "可进入" && item.id !== exceptId;
  });
}

function note(state, who, item, from, to) {
  state.log.push({ who: who, orderId: item.id, from: from, to: to });
}

function createOrder(state, spec) {
  const bay = bayFor(state, spec.material);
  if (!bay) {
    state.toast = "没有这个物料的鹤位";
    return false;
  }
  const qty = Number(spec.qty);
  if (!qty || qty <= 0) {
    state.toast = "吨数要大于 0";
    return false;
  }
  const id = "WO-0" + state.nextNo;
  state.nextNo += 1;
  state.orders.push(row({
    id: id,
    kind: String(spec.material).indexOf("废") === 0 ? "out" : "in",
    material: spec.material,
    qty: qty,
    planTime: spec.planTime || "待定",
    bayId: bay.id,
    plate: "",
    shipmentNo: spec.shipmentNo || "",
    status: "待确认",
  }));
  state.toast = "已建工单 " + id + "，状态待确认";
  return id;
}

function pullPortal(state, id) {
  const item = orderOf(state, id);
  if (!item) return false;
  const hit = state.portal.find(function (row) { return row.shipmentNo && row.shipmentNo === item.shipmentNo; });
  if (!hit) {
    state.toast = "门户对不上这张单，请手补车牌";
    return false;
  }
  item.plate = hit.plate;
  item.driver = hit.driver;
  item.coa = hit.coa;
  item.qualification = hit.qualification;
  state.toast = "已从门户带出 " + hit.plate;
  return true;
}

function setPlate(state, id, plate) {
  const item = orderOf(state, id);
  if (!item || item.status === "已离开") {
    state.toast = "这张工单不能再改车牌";
    return false;
  }
  if (!plate) {
    state.toast = "车牌不能空";
    return false;
  }
  item.plate = plate;
  state.toast = "工单 " + item.id + " 车牌改为 " + plate;
  return true;
}

function confirm(state, id) {
  const item = orderOf(state, id);
  if (!item || item.status !== "待确认") {
    state.toast = "这张工单不用再确认";
    return false;
  }
  if (!item.plate) {
    state.toast = "还没有车牌，不能确认";
    return false;
  }
  const from = item.status;
  item.status = "等候";
  note(state, "司机", item, from, item.status);
  state.toast = "已确认。请等待鹤位";
  return true;
}

function allow(state, id) {
  const item = orderOf(state, id);
  if (!item || item.status !== "等候") {
    state.toast = "只有等候中的工单可以放行进入";
    return false;
  }
  const busy = occupied(state, item.bayId, item.id);
  if (busy) {
    state.toast = bayOf(state, item.bayId).name + " 正在作业 " + busy.plate + "，不能进入";
    return false;
  }
  const from = item.status;
  item.status = "可进入";
  note(state, "罐区", item, from, item.status);
  state.toast = item.plate + " 可以进入 " + bayOf(state, item.bayId).name;
  return true;
}

function leave(state, id) {
  const item = orderOf(state, id);
  if (!item || item.status !== "可进入") {
    state.toast = "还没进入鹤位，不能点已离开";
    return false;
  }
  const from = item.status;
  item.status = "已离开";
  note(state, "罐区", item, from, item.status);
  state.toast = item.id + " 已离开，鹤位空出";
  return true;
}

function kindName(kind) { return kind === "out" ? "出厂" : "进厂"; }

function instruction(item) {
  if (item.status === "待确认") return "请确认这辆车。确认后等待通知。";
  if (item.status === "等候") return "请等待。鹤位空出后会通知你进入。";
  if (item.status === "可进入") return "请进场，按下面的鹤位和罐作业。";
  return "这趟已结束。";
}

function brief(state, item) {
  const bay = bayOf(state, item.bayId);
  return {
    id: item.id,
    kind: kindName(item.kind),
    material: item.material,
    qty: item.qty,
    planTime: item.planTime,
    plate: item.plate || "待补车牌",
    status: item.status,
    bay: bay.name,
    tank: bay.tank,
    tag: item.status === "可进入" ? "work" : item.status === "已离开" ? "done" : item.status === "等候" ? "wait" : "",
  };
}

function queueView(state) {
  const filter = state.filter || "全部";
  const rows = state.orders.filter(function (item) {
    if (filter === "进厂") return item.kind === "in";
    if (filter === "出厂") return item.kind === "out";
    return true;
  }).slice().sort(function (a, b) {
    if (a.status === "已离开" && b.status !== "已离开") return 1;
    if (b.status === "已离开" && a.status !== "已离开") return -1;
    return a.planTime < b.planTime ? -1 : 1;
  }).map(function (item) { return brief(state, item); });
  return { role: state.role, toast: state.toast, filter: filter, rows: rows };
}

function bayView(state) {
  return {
    role: state.role,
    toast: state.toast,
    rows: state.bays.map(function (bay) {
      const busy = occupied(state, bay.id);
      return {
        id: bay.id,
        name: bay.name,
        material: bay.material,
        tank: bay.tank,
        occupant: busy ? busy.plate : "",
        orderId: busy ? busy.id : "",
      };
    }),
  };
}

function orderView(state, id) {
  const item = orderOf(state, id);
  if (!item) return { missing: true, role: state.role, toast: state.toast };
  const bay = bayOf(state, item.bayId);
  const last = state.log.filter(function (line) { return line.orderId === item.id; }).slice(-1)[0];
  return {
    missing: false,
    role: state.role,
    toast: state.toast,
    id: item.id,
    kind: kindName(item.kind),
    material: item.material,
    qty: item.qty,
    planTime: item.planTime,
    plate: item.plate || "待补",
    driver: item.driver || "待门户",
    status: item.status,
    bay: bay.name,
    tank: bay.tank,
    shipmentNo: item.shipmentNo || "无",
    coa: item.coa || "门户未带出",
    qualification: item.qualification || "门户未带出",
    canAllow: item.status === "等候",
    canLeave: item.status === "可进入",
    canPull: !item.plate && !!item.shipmentNo,
    audit: last ? last.who + " 把 " + item.id + " 从 " + last.from + " 改为 " + last.to : "还没有办理记录",
  };
}

function driverView(state) {
  const cards = state.orders.map(function (item) {
    const bay = bayOf(state, item.bayId);
    const open = item.status === "可进入";
    return {
      id: item.id,
      plate: item.plate || "未确认",
      material: item.material,
      qty: item.qty,
      status: item.status,
      instruction: instruction(item),
      showWhere: open,
      bay: open ? bay.name : "等候通知",
      tank: open ? bay.tank : "等候通知",
      canConfirm: item.status === "待确认" && !!item.plate,
    };
  });
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

module.exports = {
  create: create,
  createOrder: createOrder,
  pullPortal: pullPortal,
  setPlate: setPlate,
  confirm: confirm,
  allow: allow,
  leave: leave,
  queueView: queueView,
  bayView: bayView,
  orderView: orderView,
  driverView: driverView,
};
