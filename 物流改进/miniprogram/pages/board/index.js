const store = require("../../utils/store.js");

Page({
  data: {},
  onShow() { this.refresh(); },
  refresh() {
    const s = getApp().globalData;
    const running = s.batches.filter(function (b) { return b.status === "进行中"; }).length;
    const late = s.batches.filter(function (b) { return b.status === "未开始" && Number(b.plannedStartHour) <= -4; }).length;
    const weeks = s.weekly.map(function (w) {
      const list = s.batches.filter(function (b) { return b.weekId === w.id; });
      const qty = list.reduce(function (a, b) { return a + Number(b.qty); }, 0) || 1;
      const pct = Math.round(list.reduce(function (a, b) { return a + Number(b.qty) * Number(b.progress || 0); }, 0) / qty * 100);
      return Object.assign({}, w, { pct: pct, low: w.solvent === "IPAc" });
    });
    const progress = s.batches.map(function (b) {
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
    const stocks = ["DMF", "ACN", "IPAc", "甲醇"].map(function (name, i) {
      const week = s.weekly.filter(function (w) { return w.solvent === name; }).reduce(function (a, w) { return a + Number(w.weekQty); }, 0);
      return { name: name, index: i + 1, qty: s.inventories[name].qty, week: week, level: s.inventories[name].level, low: s.inventories[name].level < 30 };
    });
    this.setData({
      role: s.role,
      toast: s.toast,
      total: store.weekSum(s),
      batchTotal: store.batchSum(s),
      diff: Math.round((store.weekSum(s) - store.batchSum(s)) * 10) / 10,
      running: running,
      late: late,
      weeks: weeks,
      progress: progress,
      stocks: stocks,
    });
  },
  onRole() { this.refresh(); },
  onQty(e) {
    store.setWeekQty(getApp().globalData, e.currentTarget.dataset.id, e.detail.value);
    this.refresh();
  },
});
