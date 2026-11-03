const store = require("../../utils/store.js");

Page({
  data: { role: "", toast: "", rows: [], total: 0 },
  onShow() { this.refresh(); },
  refresh() {
    const s = getApp().globalData;
    this.setData({
      role: s.role,
      toast: s.toast,
      total: store.weekSum(s),
      rows: s.weekly.map(function (w) {
        const sum = s.batches.filter(function (b) { return b.weekId === w.id; }).reduce(function (a, b) { return a + Number(b.qty); }, 0);
        return Object.assign({}, w, { batchQty: Math.round(sum * 10) / 10 });
      }),
    });
  },
  onRole() { this.refresh(); },
  onQty(e) {
    store.setWeekQty(getApp().globalData, e.currentTarget.dataset.id, e.detail.value);
    this.refresh();
  },
});
