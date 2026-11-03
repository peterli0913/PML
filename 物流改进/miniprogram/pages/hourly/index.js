const store = require("../../utils/store.js");

Page({
  data: { solvents: ["DMF", "ACN", "IPAc", "甲醇"], solvent: "甲醇" },
  onShow() { this.refresh(); },
  refresh() {
    const s = getApp().globalData;
    const plan = store.planOf(s, this.data.solvent);
    const pills = this.data.solvents.map(function (name) {
      const item = store.planOf(s, name);
      return { name: name, mark: item.urgent ? "赶不上" : item.suggestQty > 0 ? "要补" : "够用", on: name === this.data.solvent };
    }, this);
    this.setData({
      role: s.role,
      toast: s.toast,
      solvent: this.data.solvent,
      pills: pills,
      suggestQty: plan.suggestQty,
      legacyQty: plan.legacyQty,
      leadHours: plan.leadHours,
      totalDemand: plan.totalDemand,
      startOnHand: plan.startOnHand,
      urgent: plan.urgent,
      stockoutHour: plan.stockoutHour,
      delays: plan.delays,
      changeText: plan.arrivalChange ? plan.arrivalChange.text : "",
      projected: plan.projected,
      floor: plan.floor,
    });
    this.draw(plan);
  },
  onRole() { this.refresh(); },
  onSolvent(e) {
    this.setData({ solvent: e.currentTarget.dataset.name });
    this.refresh();
  },
  onFreeze() {
    store.freeze(getApp().globalData);
    this.refresh();
  },
  draw(plan) {
    const query = this.createSelectorQuery();
    query.select("#chart").fields({ node: true, size: true }).exec(function (res) {
      if (!res[0] || !res[0].node) return;
      const canvas = res[0].node;
      const ctx = canvas.getContext("2d");
      const dpr = wx.getWindowInfo().pixelRatio || 2;
      const w = res[0].width;
      const h = res[0].height;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, w, h);
      const values = plan.projected;
      const min = Math.min(plan.floor, 0, Math.min.apply(null, values));
      const max = Math.max(plan.floor, Math.max.apply(null, values)) + 2;
      const span = Math.max(0.1, max - min);
      const pad = 16;
      const y = function (v) { return pad + (1 - (v - min) / span) * (h - pad * 2); };
      const fy = y(plan.floor);
      ctx.strokeStyle = "#ef4444";
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(pad, fy);
      ctx.lineTo(w - pad, fy);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.strokeStyle = "#1d4ed8";
      ctx.lineWidth = 2;
      ctx.beginPath();
      values.forEach(function (v, i) {
        const x = pad + (i / (values.length - 1)) * (w - pad * 2);
        if (i === 0) ctx.moveTo(x, y(v));
        else ctx.lineTo(x, y(v));
      });
      ctx.stroke();
    });
  },
});
