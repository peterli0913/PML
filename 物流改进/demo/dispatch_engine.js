/* Vehicle-dispatch rules from the TJ4 split-execution deck, slides 5–6. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Dispatch = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const BAY = {
    DMF: "鹤管A", ACN: "鹤管B", MTBE: "鹤管C", IPAc: "鹤管D", THF: "鹤管E",
    DCM: "鹤管F", 甲醇: "鹤管G", 甲苯: "鹤管H", 正己烷: "鹤管I", 乙酸乙酯: "鹤管J",
  };

  function bayFor(material) {
    if (BAY[material]) return BAY[material];
    if (String(material).indexOf("废") === 0) return "废液鹤管1";
    return "";
  }

  function tail(code) {
    const matched = String(code).match(/DEMO-([AB])$/);
    if (matched) return matched[1];
    return String(code).slice(-3);
  }

  function clone(order) {
    return JSON.parse(JSON.stringify(order));
  }

  function fail(order, message) {
    return { ok: false, order: order, message: message, role: "", input: "", output: "" };
  }

  function ix(system, direction, content) {
    return { system: system, direction: direction, content: content };
  }

  function succeed(order, role, message, input, output, exchanges) {
    const items = exchanges || [];
    order.exchanges = (order.exchanges || []).concat(items);
    order.log.push({
      status: order.status,
      role: role,
      message: message,
      input: input,
      output: output,
      exchanges: items,
    });
    return { ok: true, order: order, message: message, role: role, input: input, output: output, exchanges: items };
  }

  function requireStatus(order, list) {
    if (list.indexOf(order.status) < 0) {
      return "当前是「" + order.status + "」，不能做这一步";
    }
    return "";
  }

  function placeByDistance(order) {
    const km = Number(order.distanceKm);
    if (km < 5) {
      order.status = "待门卫核查";
      return "距离 " + km + " km，小于 5 km，交给门卫核查";
    }
    if (km <= 15) {
      order.status = "到场预告";
      return "距离 " + km + " km，进入 15 km，提醒门卫和综合办";
    }
    order.status = "在途";
    return "距离 " + km + " km，仍在途";
  }

  function act(raw, action, payload) {
    const order = clone(raw);
    const p = payload || {};
    const inbound = order.kind === "溶剂到货";

    if (action === "issue_plan") {
      const bad = requireStatus(order, ["待供应链下达"]);
      if (bad) return fail(order, bad);
      order.status = "待采购转发";
      return succeed(order, "供应链", "下达到货或装车计划，生成唯一编号", "计划块已确认的数量、物料、罐、日期", "唯一编号 " + order.code + "，状态=待采购转发", [
        ix("计划采集系统", "读入", order.code + " 已确认计划 " + order.material + " " + order.qty + " 吨"),
        ix("钉钉", "写出", "待办给采购：转发 " + order.code),
        ix("看板", "写出", order.code + " 进入调度，状态=待采购转发"),
      ]);
    }

    if (action === "forward_purchase") {
      const bad = requireStatus(order, ["待采购转发"]);
      if (bad) return fail(order, bad);
      if (inbound && !order.supplierQualified) {
        return fail(order, order.supplier + " 尚未经过 QA 确认，采购不能下达送货计划");
      }
      if (!inbound && !order.receiverReady) {
        return fail(order, order.receiver + " 手续未齐，不能派车");
      }
      if (!inbound && Number(order.quotaLeft) < Number(order.qty)) {
        return fail(order, order.receiver + " 联单余量不足");
      }
      order.status = "待供应商上报";
      return succeed(order, "采购", "向供应商下达送货或派车计划", "已确认计划、合格供应商或接收商", "发货计划，等待车辆、司机电话" + (inbound ? "、COA" : ""), [
        ix("微信供应商门户", "写出", "待上报：" + order.code + " " + order.material + " " + order.qty + " 吨"),
        ix("邮件", "写出", "发货计划通知 " + (inbound ? order.supplier : order.receiver)),
        ix("钉钉", "写出", "待办给供应商：上报车辆"),
        ix("看板", "写出", order.code + " 状态=待供应商上报"),
      ]);
    }

    if (action === "supplier_report") {
      const bad = requireStatus(order, ["待供应商上报"]);
      if (bad) return fail(order, bad);
      if (!p.plate || !p.driver || !p.phone) return fail(order, "车牌、司机、电话必须同时上报");
      if (inbound && !p.coa) return fail(order, "溶剂到货必须上报 COA，否则不能进入发车确认");
      order.plate = p.plate;
      order.driver = p.driver;
      order.phone = p.phone;
      order.coa = !!p.coa;
      order.status = "待确认发车";
      return succeed(order, "供应商", "门户上报车辆信息", "车牌 " + p.plate + "，司机 " + p.driver + "，电话 " + p.phone + (inbound ? "，COA 已附" : ""), "待供应链按路途时间确认发车", [
        ix("微信供应商门户", "读入", "车牌 " + p.plate + "，电话 " + p.phone + (order.coa ? "，COA" : "")),
        ix("钉钉", "写出", "待办给供应链：确认 " + order.code + " 发车时间"),
        ix("看板", "写出", order.code + " 已上报车辆"),
      ]);
    }

    if (action === "confirm_depart") {
      const bad = requireStatus(order, ["待确认发车"]);
      if (bad) return fail(order, bad);
      const hours = Number(p.travelHours);
      if (!hours || hours <= 0) return fail(order, "要给出路途时间");
      order.travelHours = hours;
      order.distanceKm = Math.round(hours * 45);
      order.etaNote = "按路途 " + hours + " 小时确认发车";
      order.status = "在途";
      return succeed(order, "供应链", "确认发车时间，车辆在途", "路途 " + hours + " 小时", "距离约 " + order.distanceKm + " km，状态=在途", [
        ix("微信供应商门户", "写出", "允许发车 " + order.code + "，路途 " + hours + " 小时"),
        ix("定位", "写出", "开始跟踪 " + order.plate),
        ix("计划采集系统", "写出", order.code + " 在途，预计距离 " + order.distanceKm + " km"),
        ix("看板", "写出", order.code + " 状态=在途"),
      ]);
    }

    if (action === "set_distance") {
      const bad = requireStatus(order, ["在途", "到场预告"]);
      if (bad) return fail(order, bad);
      order.distanceKm = Number(p.km);
      const note = placeByDistance(order);
      const distanceX = [ix("定位", "读入", order.plate + " 距厂 " + order.distanceKm + " km"), ix("看板", "写出", order.code + " 状态=" + order.status)];
      if (order.status === "到场预告") distanceX.push(ix("钉钉", "写出", "到场预告给门卫、综合办：" + order.code));
      if (order.status === "待门卫核查") distanceX.push(ix("钉钉", "写出", "待核查给门卫：" + order.code));
      return succeed(order, "系统", note, "定位距离 " + p.km + " km", "状态=" + order.status, distanceX);
    }

    if (action === "adjust_buffer") {
      const bad = requireStatus(order, ["在途", "到场预告"]);
      if (bad) return fail(order, bad);
      order.bufferHours = Number(p.hours) || 0;
      order.etaNote = "供应链调节在途 " + order.bufferHours + " 小时" + (p.note ? "：" + p.note : "");
      return succeed(order, "供应链", "按使用计划变动调节在途时间", "调节 " + order.bufferHours + " 小时", order.etaNote + "。数量和车牌不变", [
        ix("计划采集系统", "写出", order.code + " 在途时间调整 " + order.bufferHours + " 小时，数量不变"),
        ix("微信供应商门户", "写出", "通知司机调整到达时间"),
        ix("看板", "写出", order.code + " 在途调节"),
      ]);
    }

    if (action === "report_exception") {
      const bad = requireStatus(order, ["在途", "到场预告", "待确认发车"]);
      if (bad) return fail(order, bad);
      if (!p.text) return fail(order, "异常说明不能空");
      order.exception = p.text;
      order.statusBeforeException = order.status;
      order.status = "异常暂停";
      return succeed(order, "供应商", "扫码上报在途异常", p.text, "状态=异常暂停，等待供应链处理", [
        ix("微信供应商门户", "读入", "异常：" + p.text),
        ix("钉钉", "写出", "异常给供应链：" + order.code),
        ix("看板", "写出", order.code + " 异常暂停"),
      ]);
    }

    if (action === "resolve_exception") {
      const bad = requireStatus(order, ["异常暂停"]);
      if (bad) return fail(order, bad);
      order.exception = "";
      if (order.distanceKm == null) order.status = "待确认发车";
      else placeByDistance(order);
      return succeed(order, "供应链", "异常已处理，车辆回到途中状态", "处理说明", "状态=" + order.status, [
        ix("微信供应商门户", "写出", order.code + " 异常已解除"),
        ix("看板", "写出", order.code + " 状态=" + order.status),
      ]);
    }

    if (action === "gate_pass") {
      const bad = requireStatus(order, ["待门卫核查"]);
      if (bad) return fail(order, bad);
      if (!order.plate) return fail(order, "没有车牌，综合办不能放行");
      if (inbound && !order.coa) return fail(order, "没有 COA，综合办不能放行");
      order.status = inbound ? "待罐区入厂指令" : "待入厂装车";
      return succeed(order, "门卫", "核查通过并点击放行", "车牌 " + order.plate, "流转到罐区", [
        ix("钉钉", "写出", "已放行，待办给罐区" + (inbound ? "和库房：" : "：") + order.code),
        ix("看板", "写出", order.code + " 门卫已放行"),
      ]);
    }

    if (action === "tank_wait_out") {
      const bad = requireStatus(order, inbound ? ["待罐区入厂指令"] : []);
      if (bad) return fail(order, bad || "废液车不在这一步厂外等待");
      if (!p.waitPlace) return fail(order, "厂外等待必须分配具体位置");
      order.waitPlace = p.waitPlace;
      order.status = "厂外等待";
      return succeed(order, "罐区", "指令为厂外等待", "等待位置 " + p.waitPlace, "状态=厂外等待", [
        ix("钉钉", "写出", "通知司机到 " + p.waitPlace),
        ix("看板", "写出", order.code + " 厂外等待"),
      ]);
    }

    if (action === "tank_in") {
      const allowed = inbound ? ["待罐区入厂指令", "厂外等待"] : ["待入厂装车"];
      const bad = requireStatus(order, allowed);
      if (bad) return fail(order, bad);
      const expect = bayFor(order.material);
      if (p.bay && p.bay !== expect) return fail(order, p.bay + " 与 " + order.material + " 不一致，不能确认。应使用 " + expect);
      if (order.tankOnline === false) return fail(order, "DCS 显示储罐液位中断，不能分配鹤管");
      if (inbound && order.tankFree != null && Number(order.tankFree) < Number(order.qty)) {
        return fail(order, "DCS 可用空间 " + order.tankFree + " 吨，小于本车 " + order.qty + " 吨");
      }
      order.bay = expect;
      order.status = inbound ? "待收货递检" : "装车中";
      return succeed(order, "罐区", inbound ? "确认入厂和车位，同步库房收货递检" : "确认废液鹤管，开始装车", "车位 " + order.bay, "状态=" + order.status, [
        ix("DCS", "读入", order.tank + " 在线，可用空间 " + (order.tankFree == null ? "未接" : order.tankFree + " 吨") + "，鹤管 " + order.bay),
        ix("钉钉", "写出", inbound ? "通知司机对接罐区，并提醒库房收货" : "通知司机到废液鹤管"),
        ix("看板", "写出", order.code + " 车位 " + order.bay),
      ]);
    }

    if (action === "receive") {
      const bad = requireStatus(order, ["待收货递检"]);
      if (bad) return fail(order, bad);
      order.rcvNo = p.rcvNo || ("RCV-" + tail(order.code));
      order.status = "待取样";
      return succeed(order, "库房", "同步收货递检", "车辆已由门卫放行", "RCV " + order.rcvNo + "，状态=待取样", [
        ix("U9", "读入", "收货递检单号 " + order.rcvNo + "。不回写 U9"),
        ix("钉钉", "写出", "提醒 QC 按计划准备取样：" + order.code),
        ix("看板", "写出", order.code + " 待取样"),
      ]);
    }

    if (action === "sample_done") {
      const bad = requireStatus(order, ["待取样"]);
      if (bad) return fail(order, bad);
      const hours = Number(p.releaseHours != null ? p.releaseHours : order.releaseHours);
      order.releaseHours = hours;
      order.batch = p.batch || ("BN-" + order.material + "-" + tail(order.code));
      if (hours < 2) {
        order.waitMode = "原地等待";
        order.status = "原地等待放行";
        return succeed(order, "罐区", "取样完成。标准放行时间 " + hours + " 小时，小于 2 小时，原位等待", "批号 " + order.batch, "状态=原地等待放行", [
        ix("U9", "读入", "批号 " + order.batch + "，取样完成"),
        ix("钉钉", "写出", "原位等待，提醒分析按 " + hours + " 小时放行"),
        ix("看板", "写出", order.code + " 原地等待放行"),
      ]);
      }
      if (!p.yardPlace) return fail(order, "放行时间达到 2 小时，出厂等待必须分配具体位置");
      order.waitMode = "出厂等待";
      order.waitPlace = p.yardPlace;
      order.status = "出厂等待放行";
      return succeed(order, "罐区", "取样完成。标准放行时间 " + hours + " 小时，出厂等待", "等待位置 " + p.yardPlace, "状态=出厂等待放行", [
        ix("U9", "读入", "批号 " + order.batch + "，取样完成"),
        ix("钉钉", "写出", "出厂等待：" + p.yardPlace),
        ix("看板", "写出", order.code + " 出厂等待放行"),
      ]);
    }

    if (action === "pull_release") {
      const bad = requireStatus(order, ["原地等待放行", "出厂等待放行"]);
      if (bad) return fail(order, bad);
      order.released = true;
      if (order.status === "原地等待放行") {
        order.status = "待置换卸车";
        return succeed(order, "系统", "从 ERP 抓到 QA 放行，车辆原位，直接置换", "放行结果=合格", "状态=待置换卸车", [
        ix("U9", "读入", order.batch + " QA 放行=合格。不回写 U9"),
        ix("钉钉", "写出", "放行完成，罐区就地置换：" + order.code),
        ix("看板", "写出", order.code + " 待置换卸车"),
      ]);
      }
      order.status = "待重新入厂";
      return succeed(order, "系统", "从 ERP 抓到 QA 放行，车辆在厂外，等待罐区确认入厂", "放行结果=合格", "状态=待重新入厂", [
        ix("U9", "读入", order.batch + " QA 放行=合格。不回写 U9"),
        ix("钉钉", "写出", "放行完成，请罐区确认重新入厂：" + order.code),
        ix("看板", "写出", order.code + " 待重新入厂"),
      ]);
    }

    if (action === "reenter") {
      const bad = requireStatus(order, ["待重新入厂"]);
      if (bad) return fail(order, bad);
      order.status = "待置换卸车";
      return succeed(order, "罐区", "确认车辆入厂，开始置换", "预定入厂", "状态=待置换卸车", [
        ix("钉钉", "写出", "车辆重新入厂：" + order.code),
        ix("看板", "写出", order.code + " 待置换卸车"),
      ]);
    }

    if (action === "start_unload") {
      const bad = requireStatus(order, ["待置换卸车"]);
      if (bad) return fail(order, bad);
      order.status = "卸车中";
      return succeed(order, "罐区", "置换后卸车", "车位 " + (order.bay || bayFor(order.material)), "状态=卸车中", [
        ix("看板", "写出", order.code + " 卸车中"),
      ]);
    }

    if (action === "disconnect") {
      const bad = requireStatus(order, ["卸车中"]);
      if (bad) return fail(order, bad);
      order.status = "已断管离场";
      order.closed = true;
      return succeed(order, "罐区", "卸车完毕，断管离场，流程终止", "卸车完成", "状态=已断管离场", [
        ix("计划采集系统", "写出", order.code + " 卸车完成，在途结束。库存变化以 DCS 为准"),
        ix("DCS", "读入", "卸后液位由采集程序读取，调度不写 DCS"),
        ix("看板", "写出", order.code + " 已断管离场"),
        ix("钉钉", "写出", "流程结束：" + order.code),
      ]);
    }

    if (action === "weigh") {
      const bad = requireStatus(order, ["装车中"]);
      if (bad) return fail(order, bad);
      order.weight = Number(p.weight || order.qty);
      order.status = "待检斤联单";
      return succeed(order, "库房", "出厂检斤", "重量 " + order.weight + " 吨", "状态=待检斤联单", [
        ix("地磅", "读入", order.plate + " " + order.weight + " 吨"),
        ix("看板", "写出", order.code + " 待检斤联单"),
      ]);
    }

    if (action === "manifest") {
      const bad = requireStatus(order, ["待检斤联单"]);
      if (bad) return fail(order, bad);
      if (!order.receiverReady) return fail(order, order.receiver + " 手续未齐，不能提交联单");
      if (Number(order.quotaLeft) < Number(order.weight || order.qty)) return fail(order, "联单余量不足");
      order.manifestNo = "LD-" + tail(order.code);
      order.quotaLeft = Math.round((Number(order.quotaLeft) - Number(order.weight || order.qty)) * 10) / 10;
      order.status = "已离场";
      order.closed = true;
      return succeed(order, "EHS", "确认联单后离场，流程终止", "重量 " + (order.weight || order.qty) + " 吨", "联单 " + order.manifestNo, [
        ix("联单系统", "写出", "RPA 填入 " + order.manifestNo + "，余量剩 " + order.quotaLeft + " 吨"),
        ix("计划采集系统", "写出", order.code + " 废液已离场"),
        ix("看板", "写出", order.code + " 已离场"),
        ix("钉钉", "写出", "联单已提交：" + order.code),
      ]);
    }

    return fail(order, "没有这个动作");
  }

  function nextActions(order) {
    const map = {
      待供应链下达: ["issue_plan"],
      待采购转发: ["forward_purchase"],
      待供应商上报: ["supplier_report"],
      待确认发车: ["confirm_depart", "report_exception"],
      在途: ["set_distance", "adjust_buffer", "report_exception"],
      到场预告: ["set_distance", "adjust_buffer", "report_exception"],
      待门卫核查: ["gate_pass"],
      待罐区入厂指令: ["tank_in", "tank_wait_out"],
      厂外等待: ["tank_in"],
      待收货递检: ["receive"],
      待取样: ["sample_done"],
      原地等待放行: ["pull_release"],
      出厂等待放行: ["pull_release"],
      待重新入厂: ["reenter"],
      待置换卸车: ["start_unload"],
      卸车中: ["disconnect"],
      待入厂装车: ["tank_in"],
      装车中: ["weigh"],
      待检斤联单: ["manifest"],
      异常暂停: ["resolve_exception"],
    };
    return map[order.status] || [];
  }

  const ACTION_LABEL = {
    issue_plan: "供应链下达",
    forward_purchase: "采购转发",
    supplier_report: "供应商上报",
    confirm_depart: "确认发车",
    set_distance: "更新距离",
    adjust_buffer: "调节在途",
    report_exception: "上报异常",
    resolve_exception: "异常解除",
    gate_pass: "门卫放行",
    tank_in: "罐区确认入厂",
    tank_wait_out: "罐区令厂外等待",
    receive: "库房收货递检",
    sample_done: "取样完成",
    pull_release: "抓取放行",
    reenter: "确认重新入厂",
    start_unload: "开始卸车",
    disconnect: "断管离场",
    weigh: "检斤",
    manifest: "提交联单",
  };

  function runScript(raw, steps) {
    let order = clone(raw);
    const trace = [];
    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      const result = act(order, step.action, step.payload);
      trace.push(result);
      if (!result.ok) return { ok: false, order: order, trace: trace };
      order = result.order;
    }
    return { ok: true, order: order, trace: trace };
  }

  function shortScript(order) {
    return [
      { action: "issue_plan" },
      { action: "forward_purchase" },
      { action: "supplier_report", payload: { plate: "津A演示1001", driver: "张师傅", phone: "13800001001", coa: true } },
      { action: "confirm_depart", payload: { travelHours: 4 } },
      { action: "adjust_buffer", payload: { hours: 1, note: "前段使用推迟" } },
      { action: "set_distance", payload: { km: 80 } },
      { action: "set_distance", payload: { km: 12 } },
      { action: "set_distance", payload: { km: 3 } },
      { action: "gate_pass" },
      { action: "tank_in", payload: { bay: bayFor(order.material) } },
      { action: "receive" },
      { action: "sample_done", payload: { releaseHours: 1.5 } },
      { action: "pull_release" },
      { action: "start_unload" },
      { action: "disconnect" },
    ];
  }

  function longScript(order) {
    return [
      { action: "issue_plan" },
      { action: "forward_purchase" },
      { action: "supplier_report", payload: { plate: "津A演示1002", driver: "李师傅", phone: "13800001002", coa: true } },
      { action: "confirm_depart", payload: { travelHours: 5 } },
      { action: "set_distance", payload: { km: 10 } },
      { action: "set_distance", payload: { km: 2 } },
      { action: "gate_pass" },
      { action: "tank_in", payload: { bay: bayFor(order.material) } },
      { action: "receive" },
      { action: "sample_done", payload: { releaseHours: 3.5, yardPlace: "厂外停车场 2 号" } },
      { action: "pull_release" },
      { action: "reenter" },
      { action: "start_unload" },
      { action: "disconnect" },
    ];
  }

  const SYSTEMS = [
    ["计划采集系统", "读已确认计划，回写在途调整和卸车完成"],
    ["微信供应商门户", "下发发货计划，收回车辆、COA、异常"],
    ["邮件", "把发货计划通知供应商"],
    ["定位", "读距离，驱动 15 公里和 5 公里"],
    ["钉钉", "把待办发给当前角色"],
    ["U9", "只读收货单号、批号和放行"],
    ["DCS", "只读液位是否在线和罐的可用空间"],
    ["地磅", "读废液出厂重量"],
    ["联单系统", "EHS 确认后由 RPA 写入"],
    ["看板", "只接收状态，不在看板上下令"],
  ];

  return {
    BAY: BAY,
    SYSTEMS: SYSTEMS,
    bayFor: bayFor,
    act: act,
    nextActions: nextActions,
    ACTION_LABEL: ACTION_LABEL,
    runScript: runScript,
    shortScript: shortScript,
    longScript: longScript,
    clone: clone,
  };
});
