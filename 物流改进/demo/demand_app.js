(function () {
  const D = window.Demand;
  const model = window.DemandData.create();
  const solvents = ["甲醇", "DMF", "ACN", "IPAc"];
  let solvent = "甲醇";
  let official = {};

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function specFor(name, previous) {
    return {
      solvent: name,
      hours: model.hours,
      batches: model.batches.filter(function (b) { return b.solvent === name; }),
      inventory: model.inventories[name],
      inbound: model.inbound[name] || [],
      cycles: model.cycles,
      previous: previous || null,
    };
  }

  function compute(name) {
    return D.planSolvent(specFor(name, official[name] || null));
  }

  function freeze() {
    solvents.forEach(function (name) {
      const plan = D.planSolvent(specFor(name, null));
      official[name] = { qty: plan.suggestQty, arrivalHour: plan.suggestArrivalHour };
    });
  }
  freeze();

  function linePath(values, min, max, w, h, pad) {
    const span = Math.max(0.1, max - min);
    return values.map(function (v, i) {
      const x = pad + (i / (values.length - 1)) * (w - pad * 2);
      const y = pad + (1 - (v - min) / span) * (h - pad * 2);
      return (i === 0 ? "M" : "L") + x.toFixed(1) + " " + y.toFixed(1);
    }).join(" ");
  }

  function yOf(v, min, max, h, pad) {
    const span = Math.max(0.1, max - min);
    return pad + (1 - (v - min) / span) * (h - pad * 2);
  }

  function chart(plan) {
    const w = 760;
    const h = 230;
    const pad = 36;
    const min = Math.min(plan.floor, 0, Math.min.apply(null, plan.projected));
    const max = Math.max(plan.floor, plan.startOnHand, Math.max.apply(null, plan.projected)) + 4;
    const path = linePath(plan.projected, min, max, w, h, pad);
    const floorY = yOf(plan.floor, min, max, h, pad);
    let marks = "";
    (model.inbound[plan.solvent] || []).forEach(function (item) {
      const x = pad + (item.hour / 167) * (w - pad * 2);
      marks += "<path d='M" + x.toFixed(1) + " " + (h - pad) + " l-5 -8 h10 z' fill='#1d6b3a'><title>在途 " + item.qty + " 吨，第 " + item.hour + " 小时到</title></path>";
    });
    const sx = pad + (Math.min(plan.suggestArrivalHour, 167) / 167) * (w - pad * 2);
    marks += "<path d='M" + sx.toFixed(1) + " " + pad + " l-5 8 h10 z' fill='#8a5a00'><title>若现在下单，最早第 " + plan.suggestArrivalHour + " 小时到厂</title></path>";
    let ticks = "";
    for (let d = 0; d < 7; d++) {
      const x = pad + (Math.min(d * 24, 167) / 167) * (w - pad * 2);
      ticks += "<line x1='" + x.toFixed(1) + "' y1='" + pad + "' x2='" + x.toFixed(1) + "' y2='" + (h - pad) + "' stroke='#e6ebf0'/>";
      ticks += "<text x='" + x.toFixed(1) + "' y='" + (h - 12) + "' font-size='11' fill='#5c6b7a'>" + (2 + d) + "日</text>";
    }
    const demandH = 78;
    const maxD = Math.max.apply(null, plan.demand.concat(1));
    const barW = Math.max(2.4, (w - pad * 2) / 168 - 0.6);
    let peak = 0;
    let peakHour = 0;
    let bars = "";
    plan.demand.forEach(function (qty, hour) {
      if (qty > peak) { peak = qty; peakHour = hour; }
      if (qty <= 0) return;
      const x = pad + (hour / 168) * (w - pad * 2);
      const bh = Math.max(2, (qty / maxD) * (demandH - 28));
      const names = plan.parts[hour].map(function (p) { return p.id + " " + D.round1(p.qty) + "吨"; }).join("，");
      bars += "<rect x='" + x.toFixed(1) + "' y='" + (demandH - 8 - bh).toFixed(1) + "' width='" + barW.toFixed(1) + "' height='" + bh.toFixed(1) + "' fill='#7ea4c4'><title>第 " + hour + " 小时需求 " + qty + " 吨。" + names + "</title></rect>";
    });
    if (peak > 0) {
      const px = pad + (peakHour / 168) * (w - pad * 2);
      bars += "<text x='" + Math.min(px, w - 120).toFixed(1) + "' y='14' font-size='11' fill='#1f4e79'>第 " + peakHour + " 小时 " + D.round1(peak) + " 吨</text>";
    }
    return "<svg viewBox='0 0 " + w + " " + (h + demandH + 18) + "' role='img' aria-label='" + plan.solvent + " 未来一周库存与小时需求'>" +
      "<text x='" + pad + "' y='16' font-size='12' fill='#1c2833'>预计库存（吨）</text>" +
      ticks +
      "<line x1='" + pad + "' y1='" + floorY.toFixed(1) + "' x2='" + (w - pad) + "' y2='" + floorY.toFixed(1) + "' stroke='#a33b3b' stroke-dasharray='4 3'/>" +
      "<text x='" + (w - pad - 92) + "' y='" + (floorY - 4).toFixed(1) + "' font-size='11' fill='#a33b3b'>下限+缓冲 " + plan.floor + "</text>" +
      "<path d='" + path + "' fill='none' stroke='#1f4e79' stroke-width='2'/>" +
      marks +
      "<text x='" + (w - 250) + "' y='" + (h + 16) + "' font-size='12' fill='#1c2833'>当小时需求（吨）</text>" +
      "<g transform='translate(0," + (h + 8) + ")'>" + bars + "</g></svg>";
  }

  function dayRows(plan) {
    const rows = [];
    for (let d = 0; d < 7; d++) {
      let sum = 0;
      let low = Infinity;
      for (let h = d * 24; h < (d + 1) * 24; h++) {
        sum += plan.rawDemand[h];
        low = Math.min(low, plan.projected[h]);
      }
      rows.push("<tr><td>11/" + (2 + d) + "</td><td>" + D.round1(sum) + "</td><td>" + low + "</td></tr>");
    }
    return rows.join("");
  }

  function advice(plan) {
    const late = plan.urgent
      ? "<div class='alert bad'>第 " + plan.stockoutHour + " 小时库存会低于下限加缓冲。现在下单的车要第 " + plan.leadHours + " 小时才到，赶在断料之前进不了罐。需要加急，或把批次后移。</div>"
      : (plan.stockoutHour == null
        ? "<div class='alert ok'>未来 168 小时，库存不低于下限加缓冲。</div>"
        : "<div class='alert'>第 " + plan.stockoutHour + " 小时触到下限加缓冲。车若在第 " + plan.leadHours + " 小时到，可以补上。</div>");
    const change = plan.arrivalChange ? "<div class='alert'>" + esc(plan.arrivalChange.text) + "</div>" : "<div class='muted'>和上一档 12 小时结果相比，到货建议没有超过 1 吨或 12 小时。</div>";
    const delays = plan.delays.length
      ? plan.delays.map(function (item) { return "<div class='alert'>" + esc(item.text) + "</div>"; }).join("")
      : "<div class='muted'>这个溶剂没有超过 4 小时的开工延误。</div>";
    const who = plan.drivers.length
      ? "缺口最大的小时主要由 " + plan.drivers.map(function (item) { return item.id + "（" + D.round1(item.qty) + " 吨）"; }).join("、") + " 拉动。"
      : "";
    return "<div class='kpi'><span>建议到货量</span><b>" + plan.suggestQty + " 吨</b></div>" +
      "<p class='formula'>提前期 " + plan.leadHours + " 小时 = 到货 " + model.cycles.arrival + " + 递检 " + model.cycles.inspect + " + 放行 " + model.cycles.release + " + 卸车 " + model.cycles.unload + "。缓冲 " + model.cycles.buffer + " 吨。起始可用 " + plan.startOnHand + " 吨，一周需求 " + plan.totalDemand + " 吨。</p>" +
      "<p class='formula'>若只按总量减库存，建议是 " + plan.legacyQty + " 吨。按小时滚动后，建议是 " + plan.suggestQty + " 吨。" + who + "</p>" +
      late + "<h2>到货更改</h2>" + change + "<h2>延误</h2>" + delays;
  }

  function render() {
    const plan = compute(solvent);
    const pills = solvents.map(function (name) {
      const item = compute(name);
      return "<button class='" + (name === solvent ? "on" : "") + "' data-solvent='" + name + "'>" + name + (item.urgent ? " · 赶不上" : item.suggestQty > 0 ? " · 要补" : " · 够用") + "</button>";
    }).join("");
    const rows = model.batches.filter(function (b) { return b.solvent === solvent; }).map(function (b) {
      return "<tr><td>" + esc(b.project) + "</td><td>" + esc(b.step) + " " + esc(b.opNo) + "</td><td>" + esc(b.manager) + "</td><td>" + esc(b.workshop) + "</td><td>" + esc(b.mode) + "</td><td>" + esc(b.status) + "</td>" +
        "<td><input class='num' data-id='" + b.id + "' data-field='qty' value='" + b.qty + "'></td>" +
        "<td><input class='num' data-id='" + b.id + "' data-field='plannedStartHour' value='" + b.plannedStartHour + "'></td>" +
        "<td><input class='num' data-id='" + b.id + "' data-field='durationHours' value='" + b.durationHours + "'></td>" +
        "<td><input class='num' data-id='" + b.id + "' data-field='progress' value='" + b.progress + "'></td></tr>";
    }).join("");
    document.getElementById("app").innerHTML =
      "<div class='kpis'><div class='kpi'><span>计算时点</span><b>" + esc(model.clock) + "</b></div>" +
      "<div class='kpi'><span>下次 12 小时定稿</span><b>11-02 20:00</b></div>" +
      "<div class='kpi'><span>本溶剂建议</span><b>" + plan.suggestQty + " 吨</b></div>" +
      "<div class='kpi'><span>提前期后最早到厂</span><b>第 " + plan.leadHours + " 小时</b></div></div>" +
      "<div class='pills'>" + pills + "<button class='btn primary' id='freeze'>执行 12 小时重算</button></div>" +
      "<div class='grid'><div class='panel'><h2>" + esc(solvent) + " · 库存怎么走，需求落在哪一小时</h2>" + chart(plan) +
      "<div class='chart-note'><span><i class='swatch' style='background:#1f4e79'></i>预计库存</span><span><i class='swatch' style='background:#a33b3b'></i>下限+缓冲</span><span><i class='swatch' style='background:#1d6b3a'></i>已在途到货</span><span><i class='swatch' style='background:#8a5a00'></i>现在下单的最早到厂</span><span><i class='swatch' style='background:#7ea4c4'></i>当小时需求</span></div>" +
      "<table class='days'><thead><tr><th>日期</th><th>当日需求（吨）</th><th>当日最低库存（吨）</th></tr></thead><tbody>" + dayRows(plan) + "</tbody></table></div>" +
      "<div class='panel'>" + advice(plan) +
      "<h2>周期，改完立即重算预览</h2>" +
      "<div class='kpis'><label>到货<input class='num' id='c-arrival' value='" + model.cycles.arrival + "'></label>" +
      "<label>递检<input class='num' id='c-inspect' value='" + model.cycles.inspect + "'></label>" +
      "<label>放行<input class='num' id='c-release' value='" + model.cycles.release + "'></label>" +
      "<label>卸车<input class='num' id='c-unload' value='" + model.cycles.unload + "'></label>" +
      "<label>缓冲吨<input class='num' id='c-buffer' value='" + model.cycles.buffer + "'></label></div></div></div>" +
      "<div class='panel' style='margin-top:12px'><h2>单批次清单 · " + esc(solvent) + "</h2><p class='muted'>需求量、距批次开始的小时、操作时长、进度由生产经理和看板更新。负的开工小时表示计划时点已过、批次还没开始。</p>" +
      "<table><thead><tr><th>项目号</th><th>步骤</th><th>生产经理</th><th>厂房</th><th>模式</th><th>状态</th><th>需求量</th><th>距开始</th><th>操作时长</th><th>进度</th></tr></thead><tbody>" + rows + "</tbody></table></div>";
  }

  document.addEventListener("click", function (event) {
    const pill = event.target.closest("[data-solvent]");
    if (pill) { solvent = pill.getAttribute("data-solvent"); render(); return; }
    if (event.target.id === "freeze") { freeze(); render(); }
  });
  document.addEventListener("change", function (event) {
    const input = event.target;
    if (input.id && input.id.indexOf("c-") === 0) {
      const key = input.id.slice(2);
      model.cycles[key] = Number(input.value);
      render();
      return;
    }
    const id = input.getAttribute("data-id");
    if (!id) return;
    const batch = model.batches.find(function (b) { return b.id === id; });
    batch[input.getAttribute("data-field")] = Number(input.value);
    render();
  });
  render();
})();
