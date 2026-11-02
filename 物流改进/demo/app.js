/* Demo shell. Numbers are illustrative, not plant actuals. Rules live in calc.js. */
(function () {
  const NOW = "2026-11-02T10:40:00";
  const NOW_LABEL = "2026-11-02 10:40";
  const NAV = [
    ["三块", [["plan", "计划"], ["dispatch", "车辆调度"], ["board", "看板整合"]]],
  ];

  function seed() {
    return {
      page: "home",
      tab: "ui",
      flash: null,
      tanks: [
        { id: "TIF01", solvent: "DMF", level: 62, cap: 100, qty: 62, high: 95, low: 20, workshops: "1号厂房", point: "LI-TIF01", bay: "鹤管A", at: "10:32:01", online: true },
        { id: "TIF02", solvent: "ACN", level: 45, cap: 80, qty: 36, high: 90, low: 15, workshops: "2号厂房", point: "LI-TIF02", bay: "鹤管B", at: "10:32:01", online: true },
        { id: "TIF03", solvent: "MTBE", level: 70, cap: 60, qty: 42, high: 90, low: 12, workshops: "3号厂房", point: "LI-TIF03", bay: "鹤管C", at: "10:32:08", online: true },
        { id: "TIF04", solvent: "IPAc", level: 18, cap: 50, qty: 9, high: 85, low: 15, workshops: "1号厂房", point: "LI-TIF04", bay: "鹤管D", at: "10:31:40", online: true },
      ],
      wasteTanks: [
        { id: "WF01", solvent: "废DMF", level: 78, cap: 40, qty: 31.2, high: 90, low: 0, workshops: "1号厂房", point: "LI-WF01", bay: "废液鹤管1", at: "10:32:01", online: true, project: "PRJ-2408" },
      ],
      unmapped: [{ id: "TIF99", solvent: "未定", point: "", note: "点位为空，不能进入计划" }],
      cycles: { DMF: 24, ACN: 24, MTBE: 24, IPAc: 36 },
      demands: [
        { id: "D-001", type: "溶剂需求", solvent: "IPAc", qty: 12, date: "2026-11-03", workshop: "1号厂房", project: "PRJ-2411", special: false, text: "", status: "确认", by: "生产经理-演示" },
        { id: "D-002", type: "废液产出", solvent: "废DMF", qty: 8, date: "2026-11-03", workshop: "1号厂房", project: "PRJ-2408", special: false, text: "", status: "确认", by: "生产经理-演示" },
      ],
      plans: [],
      vehicles: [
        { id: "V-00", planId: "", solvent: "DMF", qty: 20, plate: "苏A演示01", planPlate: "苏A演示01", status: "在途", depart: "11-02 06:10", arrive: "", exception: "" },
      ],
      nodes: [
        { id: "N-01", batch: "BN-ACN-1101", solvent: "ACN", qty: 16, plate: "苏A演示02", receipt: "2026-11-01T08:00:00", sample: "", result: "", release: "", status: "已到货未取样", bay: "" },
        { id: "N-02", batch: "BN-MTBE-1101", solvent: "MTBE", qty: 10, plate: "苏A演示03", receipt: "2026-11-01T07:00:00", sample: "2026-11-01T09:00:00", result: "合格", release: "2026-11-01T18:00:00", status: "已放行待卸车", bay: "" },
      ],
      suppliers: [
        { id: "S-A", name: "供应商甲", mfr: "生产商甲", project: "PRJ-2411", qualified: true, qaAt: "2026-10-12", docs: "营业执照、危化许可（演示资料）" },
        { id: "S-B", name: "供应商乙", mfr: "生产商乙", project: "PRJ-2411", qualified: false, qaAt: "", docs: "仅营业执照（演示资料）" },
      ],
      receivers: [
        { id: "R-1", name: "接收商甲", quota: 40, used: 12, ready: true, procedure: "已办结" },
        { id: "R-2", name: "接收商乙", quota: 20, used: 0, ready: false, procedure: "新公司手续未齐" },
      ],
      notices: [],
      audits: [{ at: NOW_LABEL, who: "罐区", what: "导入 TIF01–TIF04、WF01，并与点位对照" }],
      manifests: [],
      actuals: [
        { solvent: "DMF", planQty: 80, actualQty: 76, planCycle: 36, actualCycle: 41 },
        { solvent: "ACN", planQty: 40, actualQty: 44, planCycle: 48, actualCycle: 46 },
      ],
      mail: null,
      seq: 10,
      form: {},
    };
  }

  let state = seed();
  if (location.hash && window.SPEC[location.hash.slice(1)]) state.page = location.hash.slice(1);

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function $(id) { return document.getElementById(id); }
  function val(id) { const el = $(id); return el ? el.value : ""; }

  function remember() {
    state.form = state.form || {};
    ["p6-plan", "p6-party", "p6-plate", "p6-seal", "p7-vehicle", "p7-plate", "p8-node", "p8-bay", "p10-plan", "p10-receiver", "p10-weight", "p11-plan", "p3-low", "p4-text", "p4-solvent", "p4-qty", "p4-date", "p4-workshop", "p4-type", "p4-reason"].forEach(function (id) {
      const el = $(id);
      if (el) state.form[id] = el.value;
    });
  }

  function chosen(id, fallback) {
    const value = state.form && state.form[id];
    return value == null || value === "" ? fallback : value;
  }

  function flash(program, what, dest) {
    state.flash = { program: program, what: what, dest: dest };
  }

  function allTanks() {
    return state.tanks.concat(state.wasteTanks);
  }

  function tag(text, kind) {
    return '<span class="tag ' + (kind || "") + '">' + esc(text) + "</span>";
  }

  function table(headers, rows) {
    return "<table><thead><tr>" + headers.map(function (h) { return "<th>" + esc(h) + "</th>"; }).join("") +
      "</tr></thead><tbody>" + rows.map(function (r) {
        return "<tr>" + r.map(function (c) { return "<td>" + c + "</td>"; }).join("") + "</tr>";
      }).join("") + "</tbody></table>";
  }

  function confirmedDemand(type, solvent) {
    return Calc.sum(state.demands, function (d) {
      return d.status === "确认" && d.type === type && d.solvent === solvent;
    }, function (d) { return d.qty; });
  }

  function inTransitQty(solvent) {
    return Calc.sum(state.vehicles, function (v) {
      return v.solvent === solvent && (v.status === "在途" || v.status === "已发车");
    }, function (v) { return v.qty; });
  }

  function releasedQty(solvent) {
    return Calc.sum(state.nodes, function (n) {
      return n.solvent === solvent && n.status === "已放行待卸车";
    }, function (n) { return n.qty; });
  }

  function solventRows() {
    return state.tanks.map(function (tank) {
      const demand = confirmedDemand("溶剂需求", tank.solvent);
      const result = Calc.solventSuggestion(tank, demand, inTransitQty(tank.solvent), releasedQty(tank.solvent));
      return { tank: tank, demand: demand, result: result };
    });
  }

  function wasteRows() {
    return state.wasteTanks.map(function (tank) {
      const output = confirmedDemand("废液产出", tank.solvent);
      return { tank: tank, output: output, result: Calc.wasteSuggestion(tank, output) };
    });
  }

  function buildFreshDrafts() {
    const drafts = [];
    solventRows().forEach(function (row) {
      if (row.result.blocked || row.result.suggest <= 0) return;
      const demandRow = state.demands.find(function (d) {
        return d.status === "确认" && d.type === "溶剂需求" && d.solvent === row.tank.solvent;
      });
      drafts.push({
        id: "PL-" + row.tank.id,
        type: "到货",
        solvent: row.tank.solvent,
        tank: row.tank.id,
        qty: row.result.suggest,
        date: demandRow ? demandRow.date : "2026-11-03",
        priority: row.result.priority,
        level: row.tank.level,
        math: row.result.math,
        reason: row.tank.workshops + " 的 " + row.tank.solvent + " 需求 " + row.demand + " 吨，当前余量 " + row.tank.qty + " 吨。建议补充 " + row.result.suggest + " 吨。数量来自规则。",
        status: "草案",
        party: "",
        plate: "",
        seal: "",
        bay: row.tank.bay,
        project: demandRow ? demandRow.project : "",
      });
    });
    wasteRows().forEach(function (row) {
      if (row.result.blocked || row.result.suggest <= 0) return;
      drafts.push({
        id: "PL-" + row.tank.id,
        type: "装车",
        solvent: row.tank.solvent,
        tank: row.tank.id,
        qty: row.result.suggest,
        date: "2026-11-03",
        priority: null,
        level: row.tank.level,
        math: row.result.math,
        reason: "废液罐 " + row.tank.id + " 当前 " + row.tank.qty + " 吨，已确认产出 " + row.output + " 吨。按上限容积计算，至少装出 " + row.result.suggest + " 吨。数量来自规则。",
        status: "草案",
        party: "",
        plate: "",
        seal: "",
        bay: row.tank.bay,
        project: row.tank.project || "",
      });
    });
    drafts.sort(function (a, b) {
      if (a.type !== b.type) return a.type === "到货" ? -1 : 1;
      return a.priority - b.priority;
    });
    return drafts;
  }

  function skips() {
    return solventRows().filter(function (row) { return row.result.blocked; }).map(function (row) {
      return row.result.math;
    }).concat(wasteRows().filter(function (row) { return row.result.blocked; }).map(function (row) {
      return row.result.math;
    }));
  }

  function timeouts() {
    const list = [];
    state.nodes.forEach(function (node) {
      const cycle = state.cycles[node.solvent] || 24;
      if (node.receipt && !node.sample) {
        const hours = Calc.hoursBetween(node.receipt, NOW);
        if (hours > cycle) list.push({ role: "分析", batch: node.batch, solvent: node.solvent, hours: hours, rule: "收货后 " + hours + " 小时仍未取样，检测周期 " + cycle + " 小时" });
      } else if (node.sample && !node.release) {
        const hours = Calc.hoursBetween(node.sample, NOW);
        if (hours > cycle) list.push({ role: "QA", batch: node.batch, solvent: node.solvent, hours: hours, rule: "取样后 " + hours + " 小时仍未放行，检测周期 " + cycle + " 小时" });
      } else if (node.release && node.status === "已放行待卸车") {
        const hours = Calc.hoursBetween(node.release, NOW);
        if (hours > 12) list.push({ role: "罐区、综合办", batch: node.batch, solvent: node.solvent, hours: hours, rule: "放行后 " + hours + " 小时仍未卸，卸车等待时限 12 小时（演示值）" });
      }
    });
    return list;
  }

  function parseSpecial(text) {
    const solvents = ["废DMF", "IPAc", "DMF", "ACN", "MTBE"];
    const found = solvents.find(function (name) { return text.toUpperCase().indexOf(name.toUpperCase()) >= 0; }) || "";
    const qtyMatch = text.match(/(\d+(?:\.\d+)?)\s*吨/);
    const shopMatch = text.match(/(\d+号厂房)/);
    let date = "2026-11-03";
    if (text.indexOf("后天") >= 0) date = "2026-11-04";
    return {
      solvent: found,
      qty: qtyMatch ? qtyMatch[1] : "",
      workshop: shopMatch ? shopMatch[1] : "",
      date: date,
      special: /加急|急需/.test(text),
      note: found && qtyMatch ? "已抽出字段。确认入单之前不写入需求对象。演示用规则抽取，不是外网模型。" : "没有抽出溶剂或吨数，不能入单。",
    };
  }

  function renderSpec(spec, key) {
    if (key === "in") {
      if (!spec.inputs.length) return "<p class='muted'>本页没有业务输入。</p>";
      return table(["输入", "含义", "输入来源", "何时读取"], spec.inputs.map(function (r) {
        return r.map(esc);
      }));
    }
    if (key === "out") {
      if (!spec.outputs.length) return "<p class='muted'>本页没有业务输出。</p>";
      return "<p class='sub'>输出去向就是输出来源的接收端：写入哪个对象，接下来哪个程序或哪个人读取。</p>" +
        table(["输出", "含义", "输出去向", "何时写出"], spec.outputs.map(function (r) { return r.map(esc); }));
    }
    if (key === "dev") {
      return "<h2>功能</h2><ul class='list'>" + spec.functions.map(function (f) { return "<li>" + esc(f) + "</li>"; }).join("") + "</ul>" +
        "<h2>开发思路</h2><ol class='steps'>" + spec.dev.map(function (f) { return "<li>" + esc(f) + "</li>"; }).join("") + "</ol>" +
        "<h2>这版不做</h2><ul class='list'>" + spec.notnow.map(function (f) { return "<li>" + esc(f) + "</li>"; }).join("") + "</ul>";
    }
    return "<ol class='steps'>" + spec.demo.map(function (f) { return "<li>" + esc(f) + "</li>"; }).join("") + "</ol>";
  }

  function shell(spec, body) {
    const tabs = state.page === "home" ? "" : (
      "<div class='tabs'>" +
      [["ui", "操作界面"], ["in", "输入与来源"], ["out", "输出与去向"], ["dev", "功能与开发思路"], ["demo", "本页演示"]].map(function (t) {
        return "<button data-tab='" + t[0] + "' class='" + (state.tab === t[0] ? "active" : "") + "'>" + t[1] + "</button>";
      }).join("") + "</div>"
    );
    const inner = state.page !== "home" && state.tab !== "ui" ? renderSpec(spec, state.tab) : body;
    const flashHtml = state.flash ? (
      "<div class='flash'><b>" + esc(state.flash.program) + " 刚刚写出</b><div>" + esc(state.flash.what) +
      "</div><div class='muted'>去向：" + esc(state.flash.dest) + "</div></div>"
    ) : "";
    return "<div class='kicker'>" + esc(spec.code) + " · " + esc(spec.host) + " · 演示时间 " + NOW_LABEL + "</div>" +
      "<h1>" + esc(spec.name) + "</h1>" +
      "<p class='sub'>" + esc(spec.purpose) + "</p>" +
      "<p class='sub'>角色：" + esc(spec.role) + "</p>" +
      tabs + flashHtml + inner;
  }

  function viewHome() {
    const spec = window.SPEC.home;
    const cards = NAV.map(function (group) {
      return "<div class='panel'><h2>" + esc(group[0]) + "</h2><div class='row'>" + group[1].map(function (item) {
        return "<button class='btn' data-nav='" + item[0] + "'>" + esc(item[1]) + "</button>";
      }).join("") + "</div></div>";
    }).join("");
    return shell(spec, "<div class='panel'><h2>三块只交接这些结果</h2><ul class='list'><li>计划写出「已确认计划」：溶剂、数量、罐、日期。没有车牌。</li><li>车辆调度从已确认计划派车，写出车辆、鹤管和联单。</li><li>看板只读两边，另外写出超时和加急通知。</li></ul><h2>建议按这个顺序点</h2><ol class='steps'>" +
      spec.demo.map(function (step) { return "<li>" + esc(step) + "</li>"; }).join("") +
      "</ol><p><a href='dispatch.html'>打开车辆调度完整功能（100 条假数据）</a></p></div>" + cards);
  }

  function tankTable(withButtons, list) {
    return table(["罐", "溶剂", "点位", "液位", "余量(吨)", "下限", "状态", withButtons ? "采集" : ""], (list || allTanks()).map(function (tank) {
      const status = !tank.online ? tag("数据中断", "bad") : (tank.qty < tank.low ? tag("低于下限", "bad") : tag("在线", "ok"));
      const btn = !withButtons ? "" : (tank.online
        ? "<button class='btn bad' data-act='offline' data-id='" + tank.id + "'>模拟中断</button>"
        : "<button class='btn' data-act='online' data-id='" + tank.id + "'>恢复采集</button>");
      return [esc(tank.id), esc(tank.solvent), esc(tank.point), tank.online ? esc(tank.level + "%") : "—", tank.online ? esc(String(tank.qty)) : "—", esc(tank.low), status, btn];
    }));
  }

  function viewPlan() {
    const demandRows = state.demands.map(function (d) {
      const actions = d.status === "提报"
        ? "<button class='btn primary' data-act='confirm-demand' data-id='" + d.id + "'>确认入单</button> <button class='btn bad' data-act='reject-demand' data-id='" + d.id + "'>驳回</button>"
        : "";
      const kind = d.status === "确认" ? "ok" : d.status === "驳回" ? "bad" : "warn";
      return [esc(d.id), esc(d.type), esc(d.solvent), esc(d.qty), esc(d.date), tag(d.status, kind), esc(d.text || ""), actions];
    });
    const planRows = state.plans.map(function (p) {
      const btn = p.status === "草案" ? "<button class='btn primary' data-act='confirm-plan' data-id='" + p.id + "'>确认计划</button>" : "";
      const kind = p.status === "草案" ? "warn" : "ok";
      return [esc(p.id), tag(p.status, kind), esc(p.type), esc(p.solvent), esc(p.tank), esc(p.qty), esc(p.priority == null ? "—" : p.priority), esc(p.math), btn];
    });
    const skip = skips();
    const actualRows = state.actuals.map(function (a) {
      return [esc(a.solvent), esc(a.planQty), esc(a.actualQty), esc(a.actualQty) + " <span class='muted'>并列</span>"];
    });
    return shell(window.SPEC.plan,
      "<div class='panel'><h2>库存与参数</h2><p class='math'>余量 = 液位% × 罐容。中断的罐不进草案。本块不填车牌。</p>" + tankTable(true) +
      "<p class='muted'>未对照：" + esc(state.unmapped.map(function (t) { return t.id + " " + t.note; }).join("；")) + "</p>" +
      "<div class='row'><div class='field'><label>TIF04 下限（吨）</label><input id='p3-low' value='" + esc(chosen("p3-low", state.tanks[3].low)) + "'></div><button class='btn' data-act='save-low'>保存下限</button></div></div>" +
      "<div class='panel' style='margin-top:12px'><h2>需求</h2><label>特殊需求原文</label><textarea id='p4-text'>" + esc(chosen("p4-text", "明天2号厂房 ACN 要 40 吨，客户加急")) + "</textarea><div class='row' style='margin-top:8px'><button class='btn' data-act='parse'>整理原文</button><button class='btn primary' data-act='submit-demand'>提交提报</button></div><p id='p4-note' class='muted'></p><div class='row'><div class='field'><label>类型</label><select id='p4-type'><option" + (chosen("p4-type", "溶剂需求") === "废液产出" ? "" : " selected") + ">溶剂需求</option><option" + (chosen("p4-type", "") === "废液产出" ? " selected" : "") + ">废液产出</option></select></div><div class='field'><label>溶剂</label><input id='p4-solvent' value='" + esc(chosen("p4-solvent", "")) + "'></div><div class='field'><label>数量</label><input id='p4-qty' value='" + esc(chosen("p4-qty", "")) + "'></div><div class='field'><label>日期</label><input id='p4-date' value='" + esc(chosen("p4-date", "")) + "'></div><div class='field'><label>厂房</label><input id='p4-workshop' value='" + esc(chosen("p4-workshop", "")) + "'></div><div class='field'><label>驳回原因</label><input id='p4-reason' value='" + esc(chosen("p4-reason", "数量和当天产能不符")) + "'></div></div>" +
      table(["单号", "类型", "溶剂", "数量", "日期", "状态", "原文", "操作"], demandRows) + "</div>" +
      "<div class='panel' style='margin-top:12px'><h2>草案</h2><p class='math'>溶剂建议量 = max(需求 − 余量 − 在途 − 已放行待卸, 下限 − 余量, 0)。废液建议量 = max(当前容积 + 已确认产出 − 上限容积, 0)。</p><button class='btn primary' data-act='draft'>生成草案</button>" +
      (planRows.length ? table(["单号", "状态", "类型", "溶剂", "罐", "建议量", "优先分值", "计算过程", "操作"], planRows) : "<p class='muted'>还没有草案。</p>") +
      (skip.length ? "<ul class='list'>" + skip.map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("") + "</ul>" : "") + "</div>" +
      "<div class='panel' style='margin-top:12px'><h2>预测只并列</h2>" + table(["溶剂", "上月计划", "上月实际", "下月参考"], actualRows) +
      "<div class='row' style='margin-top:8px'><button class='btn bad' data-act='forecast-write'>尝试写入草案</button></div></div>");
  }

  function viewDispatch() {
    const ready = state.plans.filter(function (p) { return p.status === "已确认"; });
    const planOptions = ready.map(function (p) {
      const selected = p.id === chosen("p6-plan", ready[0] ? ready[0].id : "") ? " selected" : "";
      return "<option value='" + esc(p.id) + "'" + selected + ">" + esc(p.id + " " + p.type + " " + p.solvent + " " + p.qty + "吨") + "</option>";
    }).join("");
    const parties = "<optgroup label='供应商'>" + state.suppliers.map(function (s) {
      const selected = s.id === chosen("p6-party", "") ? " selected" : "";
      return "<option value='" + s.id + "'" + selected + ">" + esc(s.name + (s.qualified ? " · 已确认" : " · 未确认")) + "</option>";
    }).join("") + "</optgroup><optgroup label='接收商'>" + state.receivers.map(function (r) {
      const selected = r.id === chosen("p6-party", "") ? " selected" : "";
      return "<option value='" + r.id + "'" + selected + ">" + esc(r.name + " · " + r.procedure) + "</option>";
    }).join("") + "</optgroup>";
    const issued = state.plans.filter(function (p) { return p.status === "已下达"; }).map(function (p) {
      return [esc(p.id), esc(p.solvent), esc(p.qty), esc(p.party || "—"), esc(p.plate || "—")];
    });
    const suppliers = state.suppliers.map(function (s) {
      const btn = s.qualified ? tag("已确认 " + s.qaAt, "ok") : "<button class='btn primary' data-act='qa' data-id='" + s.id + "'>QA 确认</button>";
      return [esc(s.name), esc(s.project), esc(s.docs), btn];
    });
    const waiting = state.vehicles.filter(function (v) { return v.status === "待发车" || v.status === "在途" || v.status === "到厂"; });
    const actionable = waiting.filter(function (v) { return v.status === "待发车" || v.status === "在途"; });
    const preferred = (actionable.filter(function (v) { return v.status === "待发车"; })[0] || actionable[0] || {}).id || "";
    const currentVehicle = chosen("p7-vehicle", preferred);
    const choices = actionable.map(function (v) {
      const selected = v.id === currentVehicle ? " selected" : "";
      return "<option value='" + v.id + "'" + selected + ">" + esc(v.id + " " + v.solvent + " " + v.status) + "</option>";
    }).join("");
    const vehicleRows = waiting.map(function (v) {
      return [esc(v.id), esc(v.solvent), esc(v.qty), esc(v.planPlate || "—"), esc(v.plate), tag(v.status, v.exception ? "bad" : "ok"), esc(v.exception || "—")];
    });
    const pending = state.nodes.filter(function (n) { return n.status === "已放行待卸车"; });
    const nodeOptions = pending.map(function (n) {
      const selected = n.id === chosen("p8-node", pending[0].id) ? " selected" : "";
      return "<option value='" + n.id + "'" + selected + ">" + esc(n.batch + " " + n.solvent) + "</option>";
    }).join("");
    const suggestedBay = (pending[0] && allTanks().find(function (t) { return t.solvent === pending[0].solvent && t.online; }) || {}).id || "";
    const bayCurrent = chosen("p8-bay", suggestedBay);
    const bays = allTanks().map(function (t) {
      const selected = t.id === bayCurrent ? " selected" : "";
      return "<option value='" + t.id + "'" + selected + ">" + esc(t.bay + " · " + t.solvent) + "</option>";
    }).join("");
    const nodeRows = state.nodes.map(function (node) {
      const sampleBtn = node.sample ? "" : "<button class='btn' data-act='sample' data-id='" + node.id + "'>写入取样</button>";
      const releaseBtn = node.sample && !node.release ? "<button class='btn' data-act='release' data-id='" + node.id + "'>写入放行</button>" : "";
      return [esc(node.batch), esc(node.solvent), esc(node.sample || "—"), esc(node.release || "—"), tag(node.status, "warn"), esc(node.bay || "未确认"), sampleBtn + releaseBtn];
    });
    const loadPlans = state.plans.filter(function (p) { return p.type === "装车" && p.status === "已下达"; });
    const loadOptions = loadPlans.map(function (p) {
      const selected = p.id === chosen("p10-plan", loadPlans[0].id) ? " selected" : "";
      return "<option value='" + p.id + "'" + selected + ">" + esc(p.id + " " + p.qty + "吨 " + p.party) + "</option>";
    }).join("");
    const receivers = state.receivers.map(function (r) {
      const selected = r.id === chosen("p10-receiver", "") ? " selected" : "";
      return "<option value='" + r.id + "'" + selected + ">" + esc(r.name + " " + r.procedure) + "</option>";
    }).join("");
    const ledger = state.receivers.map(function (r) {
      return [esc(r.name), esc(r.quota), esc(r.used), esc(Calc.round1(r.quota - r.used)), tag(r.procedure, r.ready ? "ok" : "bad")];
    });
    const mans = state.manifests.map(function (m) { return [esc(m.id), esc(m.party), esc(m.weight), esc(m.plate)]; });
    return shell(window.SPEC.dispatch,
      "<div class='panel'><h2>派已确认的计划</h2>" + (ready.length ? "<label>已确认计划</label><select id='p6-plan'>" + planOptions + "</select><label>供应商或接收商</label><select id='p6-party'>" + parties + "</select><div class='row'><div class='field'><label>车牌</label><input id='p6-plate' value='" + esc(chosen("p6-plate", "苏A演示11")) + "'></div><div class='field'><label>锁封号</label><input id='p6-seal' value='" + esc(chosen("p6-seal", "")) + "'></div></div><button class='btn primary' data-act='issue'>确认派车</button>" : "<p>还没有已确认计划。先到计划块生成并确认。</p>") +
      (issued.length ? table(["单号", "溶剂", "数量", "对方", "车牌"], issued) : "") +
      (state.mail ? "<p class='math'>" + esc(state.mail) + "</p>" : "") + "</div>" +
      "<div class='panel' style='margin-top:12px'><h2>供应商资格</h2>" + table(["供应商", "项目", "已有资料", "QA"], suppliers) + "</div>" +
      "<div class='split' style='margin-top:12px'><div class='panel'><h2>车辆</h2>" + table(["车", "溶剂", "数量", "计划车牌", "实际车牌", "状态", "异常"], vehicleRows) + "</div><div class='phone'><h2>供应商门户</h2><p class='muted'>不能改计划数量。</p>" + (choices ? "<label>车辆</label><select id='p7-vehicle'>" + choices + "</select><label>实际车牌</label><input id='p7-plate' value='" + esc(chosen("p7-plate", "苏B演示99")) + "'><div class='row' style='margin-top:8px'><button class='btn primary' data-act='depart'>发车</button><button class='btn' data-act='arrive'>登记到达</button></div>" : "<p class='muted'>派车后出现待发车。</p>") + "</div></div>" +
      "<div class='panel' style='margin-top:12px'><h2>到厂与鹤管</h2>" + (nodeOptions ? "<div class='row'><div class='field'><label>已放行待卸</label><select id='p8-node'>" + nodeOptions + "</select></div><div class='field'><label>鹤管</label><select id='p8-bay'>" + bays + "</select></div><button class='btn primary' data-act='bay'>确认鹤管</button></div>" : "<p class='muted'>没有已放行待卸。</p>") +
      (waiting.some(function (v) { return v.status === "在途"; }) ? "<button class='btn' data-act='gate'>把第一辆在途车登记到厂</button>" : "") + "</div>" +
      "<div class='panel' style='margin-top:12px'><h2>厂内节点（只读 U9，演示按钮代替点击）</h2>" + table(["批号", "溶剂", "取样", "放行", "状态", "鹤管", "演示"], nodeRows) + "</div>" +
      "<div class='grid' style='margin-top:12px'><div class='panel'><h2>接收商</h2>" + table(["接收商", "额度", "已用", "剩余", "手续"], ledger) + "</div><div class='panel'><h2>联单</h2>" + (loadOptions ? "<label>已下达装车</label><select id='p10-plan'>" + loadOptions + "</select><label>接收商</label><select id='p10-receiver'>" + receivers + "</select><label>重量</label><input id='p10-weight' value='" + esc(chosen("p10-weight", loadPlans[0].qty)) + "'><button class='btn primary' data-act='manifest'>EHS 确认并提交</button>" : "<p>废液计划派车后才能预填联单。</p>") +
      (mans.length ? table(["单号", "接收商", "重量", "车牌"], mans) : "") + "</div></div>");
  }

  function viewBoard() {
    const solventOnline = Calc.round1(state.tanks.filter(function (t) { return t.online; }).reduce(function (a, t) { return a + t.qty; }, 0));
    const transit = state.vehicles.filter(function (v) { return v.status === "在途"; }).length;
    const openNodes = state.nodes.filter(function (n) { return n.status !== "已卸车"; }).length;
    const wasteSuggest = Calc.round1(wasteRows().reduce(function (a, row) { return a + (row.result.suggest || 0); }, 0));
    const exceptions = [];
    state.tanks.forEach(function (t) {
      if (!t.online) exceptions.push(["采集", t.id + " 数据中断"]);
      else if (t.qty < t.low) exceptions.push(["库存", t.id + " " + t.solvent + " 余量 " + t.qty + " 低于下限 " + t.low]);
    });
    timeouts().forEach(function (item) { exceptions.push(["时效", item.batch + " → " + item.role]); });
    state.vehicles.forEach(function (v) { if (v.exception) exceptions.push(["在途", v.plate + " " + v.exception]); });
    const planOptions = state.plans.map(function (p) { return "<option value='" + p.id + "'>" + esc(p.id + " " + p.status + " " + p.solvent) + "</option>"; }).join("");
    const sla = timeouts().map(function (item) { return [esc(item.role), esc(item.batch), esc(item.hours), esc(item.rule)]; });
    return shell(window.SPEC.board,
      "<div class='cards'><div class='card'><div class='lbl'>在线溶剂库存（吨）</div><div class='num'>" + solventOnline + "</div></div>" +
      "<div class='card'><div class='lbl'>在途车辆</div><div class='num'>" + transit + "</div></div>" +
      "<div class='card'><div class='lbl'>未关闭厂内节点</div><div class='num'>" + openNodes + "</div></div>" +
      "<div class='card" + (wasteSuggest > 0 ? " warn" : "") + "'><div class='lbl'>废液规则待装（吨）</div><div class='num'>" + wasteSuggest + "</div></div></div>" +
      "<div class='panel'><h2>溶剂罐</h2>" + tankTable(false, state.tanks) + "</div>" +
      "<div class='grid' style='margin-top:12px'><div class='panel'><h2>异常</h2>" + (exceptions.length ? table(["类", "内容"], exceptions.map(function (e) { return e.map(esc); })) : "<p>没有异常。</p>") + "</div>" +
      "<div class='panel'><h2>计划</h2>" + (state.plans.length ? table(["单号", "状态", "溶剂", "数量"], state.plans.map(function (p) { return [esc(p.id), esc(p.status), esc(p.solvent), esc(p.qty)]; })) : "<p class='muted'>计划块还没有草案。</p>") +
      "<h2>车辆</h2>" + table(["车", "状态", "溶剂", "车牌"], state.vehicles.map(function (v) { return [esc(v.id), esc(v.status), esc(v.solvent), esc(v.plate)]; })) + "</div></div>" +
      "<div class='panel' style='margin-top:12px'><h2>超时</h2>" + (sla.length ? table(["通知谁", "批号", "已等待小时", "规则"], sla) : "<p>当前没有超时。</p>") +
      "<button class='btn primary' data-act='send-sla'>发送超时通知</button></div>" +
      "<div class='panel' style='margin-top:12px'><h2>加急</h2>" + (planOptions ? "<select id='p11-plan'>" + planOptions + "</select><button class='btn' data-act='urgent'>发给全部节点</button>" : "<p class='muted'>还没有计划。</p>") + "</div>");
  }

  const VIEWS = { home: viewHome, plan: viewPlan, dispatch: viewDispatch, board: viewBoard };

  function render() {
    const nav = "<div class='brand'>TJ4 物流三块<small>演示数据，非厂区实绩</small></div><button class='nav" + (state.page === "home" ? " active" : "") + "' data-nav='home'>总览与演示顺序</button>" +
      NAV.map(function (group) {
        return "<div class='group'>" + esc(group[0]) + "</div>" + group[1].map(function (item) {
          return "<button class='nav" + (state.page === item[0] ? " active" : "") + "' data-nav='" + item[0] + "'>" + esc(item[1]) + "</button>";
        }).join("");
      }).join("") + "<button class='reset' data-act='reset'>重置演示数据</button>";
    $("app").innerHTML = "<div class='app'><aside class='side'>" + nav + "</aside><main class='main'>" + VIEWS[state.page]() + "</main></div>";
  }

  function findTank(id) {
    return allTanks().find(function (t) { return t.id === id; });
  }

  function onClick(event) {
    remember();
    const nav = event.target.closest("[data-nav]");
    if (nav) {
      state.page = nav.getAttribute("data-nav");
      state.tab = "ui";
      render();
      return;
    }
    const tab = event.target.closest("[data-tab]");
    if (tab) {
      state.tab = tab.getAttribute("data-tab");
      render();
      return;
    }
    const actEl = event.target.closest("[data-act]");
    if (!actEl) return;
    const act = actEl.getAttribute("data-act");
    const id = actEl.getAttribute("data-id");

    if (act === "reset") { state = seed(); render(); return; }
    if (act === "offline" || act === "online") {
      const tank = findTank(id);
      tank.online = act === "online";
      flash("P1", tank.id + (tank.online ? " 恢复采集" : " 标记为数据中断"), "P5 跳过该罐；P12 不把它计入库存；通知罐区");
    }
    if (act === "sample" || act === "release") {
      const node = state.nodes.find(function (n) { return n.id === id; });
      if (act === "sample") {
        node.sample = NOW;
        node.status = "未卸车待放行";
        flash("P2", node.batch + " 写入取样时间", "状态改为未卸车待放行；P9 不再通知分析");
      } else {
        node.release = NOW;
        node.result = "合格";
        node.status = "已放行待卸车";
        flash("P2", node.batch + " 写入放行时间", "状态改为已放行待卸车；P8 可以分配鹤管。演示不写 U9");
      }
    }
    if (act === "save-low") {
      const tank = state.tanks[3];
      const next = Number(val("p3-low"));
      if (!next && next !== 0) { flash("P3", "下限不是数字", "没有写入"); render(); return; }
      const prev = tank.low;
      tank.low = next;
      state.audits.unshift({ at: NOW_LABEL, who: "罐区", what: "把 " + tank.id + " 下限从 " + prev + " 改为 " + next + "，已通知原录入人" });
      flash("P3", tank.id + " 下限改为 " + next, "P5 下次生成草案时读取；通知原录入人");
    }
    if (act === "parse") {
      const parsed = parseSpecial(val("p4-text"));
      $("p4-solvent").value = parsed.solvent;
      $("p4-qty").value = parsed.qty;
      $("p4-date").value = parsed.date;
      $("p4-workshop").value = parsed.workshop;
      if (parsed.solvent === "废DMF") $("p4-type").value = "废液产出";
      $("p4-note").textContent = parsed.note;
      return;
    }
    if (act === "submit-demand") {
      const text = val("p4-text");
      const solvent = val("p4-solvent");
      const qty = Number(val("p4-qty"));
      if (!solvent || !qty) { flash("P4", "溶剂或数量还空着", "没有写入需求对象"); render(); return; }
      state.seq += 1;
      state.demands.unshift({
        id: "D-" + String(state.seq).padStart(3, "0"),
        type: val("p4-type"),
        solvent: solvent,
        qty: qty,
        date: val("p4-date") || "2026-11-03",
        workshop: val("p4-workshop") || "1号厂房",
        project: "PRJ-2411",
        special: /加急|急需/.test(text),
        text: text,
        status: "提报",
        by: "生产经理-演示",
      });
      flash("P4", "新需求状态=提报", "还不到 P5。需要再点确认入单");
    }
    if (act === "confirm-demand") {
      const demand = state.demands.find(function (d) { return d.id === id; });
      demand.status = "确认";
      flash("P4", demand.id + " 状态=确认", "P5 生成草案时读取；P12 显示");
    }
    if (act === "reject-demand") {
      const reason = val("p4-reason");
      if (!reason) { flash("P4", "驳回原因是空的", "状态未改"); render(); return; }
      const demand = state.demands.find(function (d) { return d.id === id; });
      demand.status = "驳回";
      state.notices.push({ kind: "驳回", role: "生产经理", text: demand.id + " 被驳回：" + reason });
      flash("P4", demand.id + " 状态=驳回", "通知生产经理；P5 不读取");
    }
    if (act === "draft") {
      const kept = state.plans.filter(function (p) { return p.status !== "草案"; });
      const taken = {};
      kept.forEach(function (p) { taken[p.type + "|" + p.tank] = true; });
      const fresh = buildFreshDrafts().filter(function (p) { return !taken[p.type + "|" + p.tank]; });
      state.plans = kept.concat(fresh);
      flash("计划", "写入 " + fresh.length + " 条草案", "仍在计划块。确认后才到车辆调度");
    }
    if (act === "confirm-plan") {
      const plan = state.plans.find(function (p) { return p.id === id; });
      if (!plan || plan.status !== "草案") return;
      plan.status = "已确认";
      flash("计划", plan.id + " 状态=已确认", "交给车辆调度。这里不分配车牌");
    }
    if (act === "issue") {
      const plan = state.plans.find(function (p) { return p.id === val("p6-plan"); });
      const partyId = val("p6-party");
      const plate = val("p6-plate") || "苏A演示11";
      if (!plan) return;
      if (plan.status !== "已确认") {
        flash("车辆调度", "只有已确认的计划可以派车", "数量仍留在计划块");
        render();
        return;
      }
      if (plan.type === "到货") {
        const supplier = state.suppliers.find(function (s) { return s.id === partyId; });
        const gate = Calc.canIssueSolvent(supplier);
        if (!gate.ok) { flash("车辆调度", gate.reason, "计划仍是已确认，没有车辆"); render(); return; }
        plan.party = supplier.name;
      } else {
        const receiver = state.receivers.find(function (r) { return r.id === partyId; });
        const gate = Calc.canIssueWaste(receiver, plan.qty);
        if (!gate.ok) { flash("车辆调度", gate.reason, "计划仍是已确认，没有车辆"); render(); return; }
        plan.party = receiver.name;
      }
      plan.status = "已下达";
      plan.plate = plate;
      plan.seal = val("p6-seal");
      state.seq += 1;
      state.vehicles.push({
        id: "V-" + state.seq,
        planId: plan.id,
        solvent: plan.solvent,
        qty: plan.qty,
        plate: plate,
        planPlate: plate,
        status: "待发车",
        depart: "",
        arrive: "",
        exception: "",
      });
      delete state.form["p7-vehicle"];
      state.mail = "收件人：" + plan.party + "\n" + plan.type + " " + plan.solvent + " " + plan.qty + " 吨，罐 " + plan.tank + "，车牌 " + plate + "。请按确认后的计划发车。演示不发出这封邮件。";
      flash("车辆调度", plan.id + " 状态=已下达", "供应商门户和看板。数量没有改");
    }
    if (act === "depart" || act === "arrive") {
      const vehicle = state.vehicles.find(function (v) { return v.id === val("p7-vehicle"); });
      if (!vehicle) return;
      if (act === "arrive") {
        vehicle.status = "到厂";
        vehicle.arrive = NOW_LABEL;
        flash("P7", vehicle.id + " 到达", "P8 可以登记；在途吨数不再计入 P5");
      } else {
        const plate = val("p7-plate") || vehicle.plate;
        vehicle.plate = plate;
        vehicle.status = "在途";
        vehicle.depart = NOW_LABEL;
        if (vehicle.planPlate && plate !== vehicle.planPlate) {
          vehicle.exception = "实际车牌 " + plate + " 与计划 " + vehicle.planPlate + " 不一致";
          state.notices.push({ kind: "异常", role: "供应链采购", text: vehicle.exception });
          flash("P7", "已发车，并写入在途异常", "通知供应链采购；P5 计入在途吨数；P12 显示异常");
        } else {
          vehicle.exception = val("p7-note");
          flash("P7", vehicle.id + " 已发车", "P5 计入在途吨数；P12 在途车辆加 1");
        }
      }
    }
    if (act === "bay") {
      const node = state.nodes.find(function (n) { return n.id === val("p8-node"); });
      const bayTank = findTank(val("p8-bay"));
      const gate = Calc.bayCompatible(bayTank, node.solvent);
      if (!gate.ok) { flash("P8", gate.reason, "鹤管没有写入"); render(); return; }
      node.bay = bayTank.bay;
      flash("P8", node.batch + " 确认 " + bayTank.bay, "只写入业务对象，不向阀门发指令");
    }
    if (act === "gate") {
      const vehicle = state.vehicles.find(function (v) { return v.status === "在途"; });
      if (!vehicle) return;
      vehicle.status = "到厂";
      vehicle.arrive = NOW_LABEL;
      flash("P8", vehicle.plate + " 已登记到厂", "P12 在途数减少。计划外车辆也只登记，不自动拒入");
    }
    if (act === "send-sla") {
      const list = timeouts();
      if (!list.length) { flash("P9", "当前没有超时", "没有新通知"); render(); return; }
      list.forEach(function (item) {
        state.notices.push({ kind: "超时", role: item.role, text: item.batch + " " + item.solvent + "，" + item.rule });
      });
      flash("看板整合", "写入 " + list.length + " 条超时通知", "对应角色。计划数量没有改");
    }
    if (act === "manifest") {
      const plan = state.plans.find(function (p) { return p.id === val("p10-plan"); });
      const receiver = state.receivers.find(function (r) { return r.id === val("p10-receiver"); });
      const weight = Number(val("p10-weight"));
      const gate = Calc.canIssueWaste(receiver, weight);
      if (!gate.ok) { flash("P10", gate.reason, "没有联单记录，余量未扣"); render(); return; }
      receiver.used = Calc.round1(receiver.used + weight);
      state.seq += 1;
      state.manifests.push({ id: "LD-" + state.seq, party: receiver.name, weight: weight, plate: plan.plate, at: NOW_LABEL });
      flash("P10", "联单 " + receiver.name + " " + weight + " 吨已确认", "余量已扣；演示记录代表 RPA 填入。不写 U9");
    }
    if (act === "qa") {
      const supplier = state.suppliers.find(function (s) { return s.id === id; });
      supplier.qualified = true;
      supplier.qaAt = "2026-11-02";
      flash("P11", supplier.name + " 已由 QA 确认", "P6 现在可以把它写入已下达计划。没有自动合格结论");
    }
    if (act === "urgent") {
      const plan = state.plans.find(function (p) { return p.id === val("p11-plan"); });
      ["生产经理", "采购", "供应商门户", "综合办", "罐区", "分析", "QA", "EHS"].forEach(function (role) {
        state.notices.push({ kind: "加急", role: role, text: plan.id + " " + plan.solvent + " 加急。建议量不变。" });
      });
      flash("P11", plan.id + " 生成 8 条加急任务", "钉钉全节点；P12 可见。数量没有改");
    }
    if (act === "forecast-write") {
      const before = state.plans.map(function (p) { return p.id + ":" + p.qty; }).join(",");
      flash("计划", "已拒绝。预测不写回计划对象", "草案保持 " + (before || "原样"));
    }
    render();
  }

  document.addEventListener("click", onClick);
  render();
})();
