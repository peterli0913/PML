(function () {
  const D = window.Demand;
  const pages = [
    ["demand", "更新溶剂需求"],
    ["batches", "更新批次清单"],
    ["duration", "更新单操作时长"],
    ["board", "进度与周计划"],
    ["hourly", "一周小时需求"],
  ];
  const cycles = { arrival: 24, inspect: 6, release: 18, unload: 4, buffer: 5 };
  const inventories = {
    DMF: { qty: 36, low: 12, level: 62 },
    ACN: { qty: 28, low: 10, level: 48 },
    IPAc: { qty: 14, low: 6, level: 22 },
    甲醇: { qty: 20, low: 8, level: 35 },
  };
  const inbound = {
    DMF: [{ hour: 30, qty: 16 }],
    ACN: [{ hour: 18, qty: 8 }],
    IPAc: [],
    甲醇: [],
  };
  let weekly = [
    { id: "W1", project: "PRJ-2408", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", manager: "王经理", weekQty: 24 },
    { id: "W2", project: "PRJ-2411", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", manager: "王经理", weekQty: 18 },
    { id: "W3", project: "PRJ-2412", workshop: "2号厂房", solvent: "ACN", materialCode: "SOL-ACN", manager: "赵经理", weekQty: 22 },
    { id: "W4", project: "PRJ-2418", workshop: "1号厂房", solvent: "IPAc", materialCode: "SOL-IPAc", manager: "陈经理", weekQty: 16 },
    { id: "W5", project: "PRJ-2404", workshop: "3号厂房", solvent: "甲醇", materialCode: "SOL-MEOH", manager: "周经理", weekQty: 18 },
  ];
  let operations = [
    { id: "OP-12", step: "投料", mode: "持续", durationHours: 36 },
    { id: "OP-03", step: "补料", mode: "持续", durationHours: 30 },
    { id: "OP-07", step: "滴加", mode: "持续", durationHours: 48 },
    { id: "OP-02", step: "投料", mode: "持续", durationHours: 16 },
    { id: "OP-01", step: "一次投入", mode: "单次", durationHours: 1 },
  ];
  let batches = [
    { id: "B01", weekId: "W1", opId: "OP-12", step: "投料", opNo: "OP-12", manager: "王经理", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", project: "PRJ-2408", qty: 24, mode: "持续", plannedStartHour: -8, durationHours: 36, progress: 0.4, status: "进行中" },
    { id: "B02", weekId: "W2", opId: "OP-03", step: "补料", opNo: "OP-03", manager: "王经理", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", project: "PRJ-2411", qty: 18, mode: "持续", plannedStartHour: 20, durationHours: 30, progress: 0, status: "未开始" },
    { id: "B04", weekId: "W3", opId: "OP-07", step: "滴加", opNo: "OP-07", manager: "赵经理", workshop: "2号厂房", solvent: "ACN", materialCode: "SOL-ACN", project: "PRJ-2412", qty: 22, mode: "持续", plannedStartHour: 8, durationHours: 48, progress: 0, status: "未开始" },
    { id: "B06", weekId: "W4", opId: "OP-02", step: "投料", opNo: "OP-02", manager: "陈经理", workshop: "1号厂房", solvent: "IPAc", materialCode: "SOL-IPAc", project: "PRJ-2418", qty: 16, mode: "持续", plannedStartHour: -10, durationHours: 16, progress: 0, status: "未开始" },
    { id: "B08", weekId: "W5", opId: "OP-01", step: "一次投入", opNo: "OP-01", manager: "周经理", workshop: "3号厂房", solvent: "甲醇", materialCode: "SOL-MEOH", project: "PRJ-2404", qty: 18, mode: "单次", plannedStartHour: 1, durationHours: 1, progress: 0, status: "未开始" },
  ];
  let page = "board";
  let role = "生产经理";
  let solvent = "甲醇";
  let toast = "看板已抓取当前进度和周计划。直接改周计划数量，这一页和小时需求会一起变。";
  let official = {};

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function round1(n) { return D.round1(n); }
  function weekOf(id) { return weekly.find(function (w) { return w.id === id; }); }
  function batchesOf(weekId) { return batches.filter(function (b) { return b.weekId === weekId; }); }
  function solvents() { return ["DMF", "ACN", "IPAc", "甲醇"]; }

  function scaleWeek(row) {
    const list = batchesOf(row.id).filter(function (b) { return b.status !== "完成"; });
    const sum = list.reduce(function (a, b) { return a + Number(b.qty); }, 0);
    if (!list.length) return;
    if (sum <= 0) { list[0].qty = Number(row.weekQty); return; }
    const factor = Number(row.weekQty) / sum;
    list.forEach(function (b) { b.qty = round1(b.qty * factor); });
  }

  function planOf(name) {
    return D.planSolvent({
      solvent: name,
      hours: 168,
      batches: batches.filter(function (b) { return b.solvent === name; }),
      inventory: inventories[name],
      inbound: inbound[name],
      cycles: cycles,
      previous: official[name] || null,
    });
  }

  function freeze() {
    solvents().forEach(function (name) {
      const plan = planOf(name);
      official[name] = { qty: plan.suggestQty, arrivalHour: plan.suggestArrivalHour };
    });
  }
  freeze();

  function weekSum() { return round1(weekly.reduce(function (a, w) { return a + Number(w.weekQty); }, 0)); }
  function batchSum(name) {
    return round1(batches.filter(function (b) { return !name || b.solvent === name; }).reduce(function (a, b) { return a + Number(b.qty); }, 0));
  }
  function delays() {
    return batches.filter(function (b) { return b.status === "未开始" && Number(b.plannedStartHour) <= -4; });
  }
  function progressOf(row) {
    const list = batchesOf(row.id);
    if (!list.length) return 0;
    const qty = list.reduce(function (a, b) { return a + Number(b.qty); }, 0) || 1;
    return list.reduce(function (a, b) { return a + Number(b.qty) * Number(b.progress || 0); }, 0) / qty;
  }

  function setWeekQty(id, qty) {
    const row = weekOf(id);
    row.weekQty = qty;
    scaleWeek(row);
    toast = row.project + " " + row.solvent + " 周计划改为 " + qty + " 吨，已分摊到未完成批次，看板和小时需求已更新。";
  }

  function shell(title, body) {
    const nav = pages.map(function (item) {
      return "<button class='item" + (page === item[0] ? " on" : "") + "' data-page='" + item[0] + "'>" + item[1] + "</button>";
    }).join("");
    return "<div class='app'><aside class='side'><div class='logo'>溶剂物流系统</div><div class='role'>当前身份<br><b>" + esc(role) + "</b></div><div class='nav-group'>溶剂需求计划</div>" + nav + "</aside><div class='main'><div class='bar'><div class='crumb'>首页 / <b>" + esc(title) + "</b></div><div><button class='btn' id='role'>" + (role === "生产经理" ? "切换为物流计划员" : "切换为生产经理") + "</button> <a href='demand.html'>算法单页</a></div></div><div class='content'>" + (toast ? "<div class='toast'>" + esc(toast) + "</div>" : "") + body + "</div></div></div>";
  }

  function bar(pct, low) {
    const width = Math.max(0, Math.min(100, pct));
    return "<div class='bar-track'><div class='bar-fill" + (low ? " low" : "") + "' style='width:" + width + "%'></div></div>";
  }

  function pageDemand() {
    const rows = weekly.map(function (w) {
      const got = round1(batchesOf(w.id).reduce(function (a, b) { return a + Number(b.qty); }, 0));
      return "<tr><td>" + esc(w.project) + "</td><td>" + esc(w.workshop) + "</td><td>" + esc(w.solvent) + "</td><td>" + esc(w.materialCode) + "</td><td>" + esc(w.manager) + "</td><td><input class='num' data-week='" + w.id + "' value='" + w.weekQty + "'></td><td>" + got + "</td></tr>";
    }).join("");
    return shell("更新溶剂需求", "<div class='kpis'><div class='card'><div class='label'>周计划合计</div><div class='num'>" + weekSum() + " 吨</div><div class='delta'>改任意一行，看板使用同一个数</div></div></div><div class='card'><h2>本周溶剂需求</h2><p class='note'>生产经理在这里改周计划。保存的是项目上的溶剂需求，未完成批次按比例跟着变，进度看板立刻用新数。</p><table><thead><tr><th>项目号</th><th>厂房</th><th>溶剂</th><th>料号</th><th>生产经理</th><th>周计划（吨）</th><th>已分摊到批次</th></tr></thead><tbody>" + rows + "</tbody></table></div>");
  }

  function pageBatches() {
    const rows = batches.map(function (b) {
      return "<tr><td>" + esc(b.project) + "</td><td>" + esc(b.step) + "</td><td>" + esc(b.opNo) + "</td><td>" + esc(b.manager) + "</td><td>" + esc(b.workshop) + "</td><td>" + esc(b.solvent) + "</td><td>" + esc(b.materialCode) + "</td><td><input class='num' data-batch='" + b.id + "' data-field='qty' value='" + b.qty + "'></td><td><input class='num' data-batch='" + b.id + "' data-field='plannedStartHour' value='" + b.plannedStartHour + "'></td><td>" + esc(b.mode) + "</td><td><input class='num' data-batch='" + b.id + "' data-field='durationHours' value='" + b.durationHours + "'></td><td><input class='num' data-batch='" + b.id + "' data-field='progress' value='" + b.progress + "'></td><td>" + esc(b.status) + "</td></tr>";
    }).join("");
    return shell("更新批次清单", "<div class='card'><h2>单批次清单</h2><p class='note'>字段与拆分方案一致。改需求量会回写对应周计划，看板同步。负的「距开始」表示计划时点已过、批次还没开工。</p><div style='overflow:auto'><table><thead><tr><th>项目号</th><th>步骤</th><th>操作号</th><th>生产经理</th><th>厂房</th><th>溶剂</th><th>料号</th><th>需求量</th><th>距开始</th><th>模式</th><th>操作时长</th><th>进度</th><th>状态</th></tr></thead><tbody>" + rows + "</tbody></table></div></div>");
  }

  function pageDuration() {
    const rows = operations.map(function (op) {
      const n = batches.filter(function (b) { return b.opId === op.id && b.status !== "完成"; }).length;
      return "<tr><td>" + esc(op.step) + "</td><td>" + esc(op.id) + "</td><td>" + esc(op.mode) + "</td><td><input class='num' data-op='" + op.id + "' value='" + op.durationHours + "'></td><td>" + n + "</td><td><button class='btn primary' data-apply='" + op.id + "'>应用到未完成批次</button></td></tr>";
    }).join("");
    return shell("更新单操作时长", "<div class='card'><h2>操作时长</h2><p class='note'>持续：需求量 ÷ 时长，铺到每个小时。单次：需求量落在开工那一小时。应用到批次后，小时需求和看板进度一起变。</p><table><thead><tr><th>步骤</th><th>操作号</th><th>模式</th><th>标准时长（小时）</th><th>未完成批次</th><th></th></tr></thead><tbody>" + rows + "</tbody></table></div>");
  }

  function pageBoard() {
    const running = batches.filter(function (b) { return b.status === "进行中"; }).length;
    const late = delays().length;
    const diff = round1(weekSum() - batchSum());
    const planRows = weekly.map(function (w) {
      const pct = Math.round(progressOf(w) * 100);
      return "<tr><td>" + esc(w.project) + "</td><td>" + esc(w.solvent) + "</td><td>" + esc(w.workshop) + "</td><td><input class='num' data-week='" + w.id + "' value='" + w.weekQty + "'></td><td>" + bar(pct, pct < 30 && w.solvent === "IPAc") + "</td><td>" + pct + "%</td></tr>";
    }).join("");
    const progRows = batches.map(function (b) {
      const pct = Math.round(Number(b.progress) * 100);
      const slip = b.status === "未开始" && b.plannedStartHour < 0 ? "延误 " + (-b.plannedStartHour) + " 小时" : b.status;
      return "<tr><td>" + esc(b.project) + " " + esc(b.opNo) + "</td><td>" + esc(b.solvent) + "</td><td>" + esc(b.qty) + "</td><td>" + bar(pct, slip.indexOf("延误") === 0) + "</td><td>" + esc(slip) + "</td></tr>";
    }).join("");
    const stockRows = solvents().map(function (name, i) {
      const inv = inventories[name];
      const week = round1(weekly.filter(function (w) { return w.solvent === name; }).reduce(function (a, w) { return a + Number(w.weekQty); }, 0));
      return "<tr><td>" + (i + 1) + "</td><td>" + esc(name) + "</td><td>" + inv.qty + "</td><td>" + week + "</td><td>" + bar(inv.level, inv.level < 30) + " " + inv.level + "%</td></tr>";
    }).join("");
    return shell("进度与周计划", "<div class='kpis'>" +
      "<div class='card'><div class='label'>本周溶剂需求</div><div class='num'>" + weekSum() + " 吨</div><div class='delta'>来自周计划，批次合计 " + batchSum() + " 吨</div></div>" +
      "<div class='card'><div class='label'>进行中批次</div><div class='num'>" + running + "</div><div class='delta'>看板抓取的当前进度</div></div>" +
      "<div class='card'><div class='label'>延误批次</div><div class='num'>" + late + "</div><div class='delta down'>开工已过仍未开始</div></div>" +
      "<div class='card'><div class='label'>周计划与批次差</div><div class='num'>" + diff + "</div><div class='delta'>改周计划后应回到 0</div></div></div>" +
      "<div class='grid-3'><div class='card'><h2>周计划 · 可直接改</h2><p class='note'>这一列就是生产经理的溶剂需求。改完，上面的合计和右边的批次需求一起变。</p><table><thead><tr><th>项目</th><th>溶剂</th><th>厂房</th><th>周计划</th><th>进度</th><th></th></tr></thead><tbody>" + planRows + "</tbody></table></div>" +
      "<div class='card'><h2>当前批次进度</h2><table><thead><tr><th>批次</th><th>溶剂</th><th>需求量</th><th>进度</th><th>状态</th></tr></thead><tbody>" + progRows + "</tbody></table></div>" +
      "<div class='card'><h2>溶剂与库存</h2><p class='note'>余量来自 DCS 演示值，不随周计划改。</p><table><thead><tr><th></th><th>溶剂</th><th>余量</th><th>周需求</th><th>液位</th></tr></thead><tbody>" + stockRows + "</tbody></table></div></div>");
  }

  function chart(plan) {
    const w = 640;
    const h = 180;
    const pad = 28;
    const min = Math.min(plan.floor, 0, Math.min.apply(null, plan.projected));
    const max = Math.max(plan.floor, Math.max.apply(null, plan.projected)) + 2;
    const span = Math.max(0.1, max - min);
    const path = plan.projected.map(function (v, i) {
      const x = pad + (i / 167) * (w - pad * 2);
      const y = pad + (1 - (v - min) / span) * (h - pad * 2);
      return (i === 0 ? "M" : "L") + x.toFixed(1) + " " + y.toFixed(1);
    }).join(" ");
    const fy = pad + (1 - (plan.floor - min) / span) * (h - pad * 2);
    return "<svg viewBox='0 0 " + w + " " + h + "'><line x1='" + pad + "' y1='" + fy.toFixed(1) + "' x2='" + (w - pad) + "' y2='" + fy.toFixed(1) + "' stroke='#ef4444' stroke-dasharray='4 3'/><path d='" + path + "' fill='none' stroke='#1d4ed8' stroke-width='2'/><text x='" + pad + "' y='16' font-size='12' fill='#6b7280'>预计库存 · 红线为下限+缓冲 " + plan.floor + " 吨</text></svg>";
  }

  function pageHourly() {
    const plan = planOf(solvent);
    const pills = solvents().map(function (name) {
      const item = planOf(name);
      const mark = item.urgent ? "赶不上" : item.suggestQty > 0 ? "要补" : "够用";
      return "<button class='btn" + (name === solvent ? " on" : "") + "' data-solvent='" + name + "'>" + name + " · " + mark + "</button>";
    }).join("");
    const late = plan.delays.map(function (item) { return "<div class='alert'>" + esc(item.text) + "</div>"; }).join("") || "<p class='note'>没有超过 4 小时的开工延误。</p>";
    const change = plan.arrivalChange ? "<div class='alert bad'>" + esc(plan.arrivalChange.text) + "</div>" : "<p class='note'>和上一档 12 小时定稿比，没有超过 1 吨或 12 小时。</p>";
    const urgent = plan.urgent ? "<div class='alert bad'>第 " + plan.stockoutHour + " 小时破下限加缓冲。车要第 " + plan.leadHours + " 小时才到，需要加急或后移批次。</div>" : "<p class='note'>断料不早于提前期，或本周没有破地板。</p>";
    return shell("一周小时需求", "<div class='pills'>" + pills + "<button class='btn primary' id='freeze'>执行 12 小时重算</button></div><div class='grid-2'><div class='card'><h2>" + esc(solvent) + " · 未来 168 小时</h2>" + chart(plan) + "<p class='note'>每 12 小时把当前结果定稿。DCS 可以 15 分钟刷新库存，但不每次都改到货计划。</p></div><div class='card'><h2>计算结果</h2><div class='num' style='font-size:28px;font-weight:700'>" + plan.suggestQty + " 吨</div><p class='note'>只按总量减库存是 " + plan.legacyQty + " 吨。提前期 " + plan.leadHours + " 小时。一周需求 " + plan.totalDemand + " 吨，起始可用 " + plan.startOnHand + " 吨。</p>" + urgent + "<h2>到货更改</h2>" + change + "<h2>延误</h2>" + late + "</div></div>");
  }

  const views = { demand: pageDemand, batches: pageBatches, duration: pageDuration, board: pageBoard, hourly: pageHourly };

  function render() {
    document.getElementById("app").innerHTML = views[page]();
  }

  document.addEventListener("click", function (event) {
    const nav = event.target.closest("[data-page]");
    if (nav) { page = nav.getAttribute("data-page"); render(); return; }
    const solv = event.target.closest("[data-solvent]");
    if (solv) { solvent = solv.getAttribute("data-solvent"); render(); return; }
    const apply = event.target.closest("[data-apply]");
    if (apply) {
      const op = operations.find(function (item) { return item.id === apply.getAttribute("data-apply"); });
      let n = 0;
      batches.forEach(function (b) {
        if (b.opId === op.id && b.status !== "完成") {
          b.durationHours = Number(op.durationHours);
          b.mode = op.mode;
          n += 1;
        }
      });
      toast = op.id + " 标准时长 " + op.durationHours + " 小时，已应用到 " + n + " 个未完成批次。";
      render();
      return;
    }
    if (event.target.id === "role") {
      role = role === "生产经理" ? "物流计划员" : "生产经理";
      render();
      return;
    }
    if (event.target.id === "freeze") {
      freeze();
      toast = "12 小时计算已定稿。之后再改周计划或时长，会重新出现到货更改。";
      render();
    }
  });

  document.addEventListener("change", function (event) {
    const input = event.target;
    if (input.getAttribute("data-week")) {
      setWeekQty(input.getAttribute("data-week"), Number(input.value));
      setTimeout(render, 0);
      return;
    }
    if (input.getAttribute("data-op")) {
      const op = operations.find(function (item) { return item.id === input.getAttribute("data-op"); });
      op.durationHours = Number(input.value);
      return;
    }
    const id = input.getAttribute("data-batch");
    if (!id) return;
    const batch = batches.find(function (b) { return b.id === id; });
    batch[input.getAttribute("data-field")] = Number(input.value);
    if (input.getAttribute("data-field") === "qty") {
      const row = weekOf(batch.weekId);
      row.weekQty = round1(batchesOf(row.id).reduce(function (a, b) { return a + Number(b.qty); }, 0));
      toast = batch.project + " 批次需求已改，周计划同步为 " + row.weekQty + " 吨。";
    } else {
      toast = batch.project + " 的批次清单已更新，看板会按新进度抓取。";
    }
    setTimeout(render, 0);
  });

  render();
})();
