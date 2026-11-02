(function () {
  const D = window.Dispatch;
  let orders = window.DispatchData.generate();
  let selected = "TJ4-DEMO-A";
  let filter = "全部";
  let q = "";
  let trace = [];
  let form = {};

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function current() {
    return orders.find(function (o) { return o.code === selected; }) || orders[0];
  }

  function stageOf(status) {
    if (status === "已断管离场" || status === "已离场") return "已结束";
    if (status === "异常暂停") return "异常";
    const early = ["待供应链下达", "待采购转发", "待供应商上报", "待确认发车", "在途", "到场预告", "待门卫核查"];
    return early.indexOf(status) >= 0 ? "阶段一" : "阶段二";
  }

  function visible() {
    return orders.filter(function (o) {
      if (filter === "溶剂到货" || filter === "废液装车") return o.kind === filter;
      if (filter !== "全部" && stageOf(o.status) !== filter) return false;
      if (!q) return true;
      const blob = (o.code + o.material + o.plate + o.supplier + o.status).toLowerCase();
      return blob.indexOf(q.toLowerCase()) >= 0;
    });
  }

  function replace(order) {
    orders = orders.map(function (o) { return o.code === order.code ? order : o; });
    selected = order.code;
  }

  function apply(action, payload) {
    const result = D.act(current(), action, payload);
    trace.push(result);
    if (result.ok) replace(result.order);
    render();
  }

  function play(kind) {
    const code = kind === "long" ? "TJ4-DEMO-B" : "TJ4-DEMO-A";
    const fresh = window.DispatchData.generate().find(function (o) { return o.code === code; });
    const steps = kind === "long" ? D.longScript(fresh) : D.shortScript(fresh);
    const result = D.runScript(fresh, steps);
    replace(result.order);
    trace = result.trace.slice();
    render();
  }

  function field(id, label, value) {
    return "<label>" + label + "</label><input id='" + id + "' value='" + esc(value || "") + "'>";
  }

  function actionForm(order) {
    const actions = D.nextActions(order);
    if (!actions.length) return "<p class='muted'>这条单已经结束，没有下一步。</p>";
    return actions.map(function (action) {
      let extra = "";
      if (action === "supplier_report") {
        extra = field("f-plate", "车牌", "津A演示88" + order.code.slice(-2)) +
          field("f-driver", "司机", "张师傅") + field("f-phone", "电话", "13800001888") +
          "<label><input id='f-coa' type='checkbox' checked style='width:auto'> 已附 COA</label>";
      }
      if (action === "confirm_depart") extra = field("f-hours", "路途时间（小时）", "4");
      if (action === "set_distance") extra = field("f-km", "当前距离（km）", order.distanceKm > 15 ? "12" : "3");
      if (action === "adjust_buffer") extra = field("f-buffer", "调节小时", "1");
      if (action === "report_exception") extra = field("f-ex", "异常说明", "服务区检修，晚到 1 小时");
      if (action === "tank_wait_out") extra = field("f-place", "厂外等待位置", "厂外停车场 1 号");
      if (action === "tank_in") {
        const right = D.bayFor(order.material);
        extra = "<label>鹤管</label><select id='f-bay'><option>" + esc(right) + "</option><option>鹤管A</option><option>鹤管B</option></select>";
      }
      if (action === "sample_done") extra = field("f-hours2", "标准放行时间（小时）", order.releaseHours);
      if (action === "weigh") extra = field("f-weight", "检斤重量（吨）", order.qty);
      return "<div class='math' style='margin-top:8px'><button class='act' data-action='" + action + "'>" + esc(D.ACTION_LABEL[action]) + "</button>" + extra + "</div>";
    }).join("");
  }

  function payloadFor(action) {
    const v = function (id) { const el = document.getElementById(id); return el ? el.value : ""; };
    const coa = document.getElementById("f-coa");
    if (action === "supplier_report") return { plate: v("f-plate"), driver: v("f-driver"), phone: v("f-phone"), coa: coa ? coa.checked : false };
    if (action === "confirm_depart") return { travelHours: v("f-hours") };
    if (action === "set_distance") return { km: v("f-km") };
    if (action === "adjust_buffer") return { hours: v("f-buffer"), note: "前段使用计划变动" };
    if (action === "report_exception") return { text: v("f-ex") };
    if (action === "tank_wait_out") return { waitPlace: v("f-place") };
    if (action === "tank_in") return { bay: v("f-bay") };
    if (action === "sample_done") {
      const hours = Number(v("f-hours2"));
      return { releaseHours: hours, yardPlace: hours >= 2 ? "厂外停车场 2 号" : "" };
    }
    if (action === "weigh") return { weight: v("f-weight") };
    return {};
  }

  function render() {
    const rows = visible();
    const counts = { 全部: orders.length };
    orders.forEach(function (o) {
      const s = stageOf(o.status);
      counts[s] = (counts[s] || 0) + 1;
      counts[o.kind] = (counts[o.kind] || 0) + 1;
    });
    const chips = ["全部", "阶段一", "阶段二", "异常", "已结束", "溶剂到货", "废液装车"].map(function (name) {
      return "<button class='chip" + (filter === name ? " on" : "") + "' data-filter='" + name + "'>" + name + " " + (counts[name] || 0) + "</button>";
    }).join("");
    const head = "<div class='filters'>" + chips + "<input id='q' placeholder='搜编号、物料、车牌' value='" + esc(q) + "' style='max-width:220px'><button class='ghost' id='run-short'>演完一单：放行小于 2 小时</button><button class='ghost' id='run-long'>演完一单：放行达到 2 小时</button></div>";
    const table = "<div class='scroll'><table><thead><tr><th>唯一编号</th><th>类型</th><th>物料</th><th>吨</th><th>状态</th><th>车牌</th><th>距离</th></tr></thead><tbody>" +
      rows.map(function (o) {
        const bad = o.status === "异常暂停" || o.closed;
        return "<tr data-code='" + esc(o.code) + "' class='" + (o.code === selected ? "sel" : "") + "'><td>" + esc(o.code) + "</td><td>" + esc(o.kind) + "</td><td>" + esc(o.material) + "</td><td>" + esc(o.qty) + "</td><td><span class='tag" + (o.status.indexOf("异常") >= 0 ? " bad" : o.closed ? " ok" : "") + "'>" + esc(o.status) + "</span></td><td>" + esc(o.plate || "—") + "</td><td>" + (o.distanceKm == null ? "—" : esc(o.distanceKm + " km")) + "</td></tr>";
      }).join("") + "</tbody></table></div>";
    const order = current();
    const log = (trace.filter(function (t) { return t.order && t.order.code === order.code; }).slice(-18).map(function (t) {
      return "<li><b>" + esc(t.ok ? t.role : "未通过") + "</b> " + esc(t.message) + (t.input ? "<div class='muted'>输入：" + esc(t.input) + "</div><div class='muted'>输出：" + esc(t.output) + "</div>" : "") + "</li>";
    }).join("")) || "<li class='muted'>还没有操作。可以逐步点下一步，或演完 DEMO 两单。</li>";
    const detail = "<div class='panel detail'><h2 style='margin:0 0 6px'>" + esc(order.code) + "</h2><p class='muted'>" + esc(order.kind) + " · " + esc(order.material) + " " + esc(order.qty) + " 吨 · " + esc(order.supplier) + (order.kind === "废液装车" ? " / " + order.receiver : "") + "</p><p>状态 <span class='tag'>" + esc(order.status) + "</span></p><p class='math'>标准放行 " + esc(order.releaseHours) + " 小时。距离 " + (order.distanceKm == null ? "未发车" : order.distanceKm + " km") + "。" + esc(order.etaNote || "") + (order.exception ? " 异常：" + order.exception : "") + (order.bay ? " 鹤管 " + order.bay : "") + (order.rcvNo ? " " + order.rcvNo : "") + (order.batch ? " " + order.batch : "") + (order.waitPlace ? " 等待位置 " + order.waitPlace : "") + "</p><h3>这一步可以做的事</h3>" + actionForm(order) + "<h3>过程</h3><ol class='log'>" + log + "</ol></div>";
    document.getElementById("app").innerHTML = "<div class='layout'><div class='panel'>" + head + table + "<p class='muted'>显示 " + rows.length + " / " + orders.length + " 条</p></div>" + detail + "</div>";
    const box = document.getElementById("q");
    if (box) box.addEventListener("input", function () { q = box.value; render(); });
  }

  document.addEventListener("click", function (event) {
    const filterBtn = event.target.closest("[data-filter]");
    if (filterBtn) { filter = filterBtn.getAttribute("data-filter"); render(); return; }
    const row = event.target.closest("tr[data-code]");
    if (row) { selected = row.getAttribute("data-code"); trace = []; render(); return; }
    const actionBtn = event.target.closest("[data-action]");
    if (actionBtn) { apply(actionBtn.getAttribute("data-action"), payloadFor(actionBtn.getAttribute("data-action"))); return; }
    if (event.target.id === "run-short") play("short");
    if (event.target.id === "run-long") play("long");
  });

  render();
})();
