const store = require("../../utils/store.js");

Page({
  data: { role: "", toast: "", rows: [] },
  onShow() { this.refresh(); },
  refresh() {
    const s = getApp().globalData;
    this.setData({
      role: s.role,
      toast: s.toast,
      rows: s.operations.map(function (op) {
        return Object.assign({}, op, {
          count: s.batches.filter(function (b) { return b.opId === op.id && b.status !== "完成"; }).length,
        });
      }),
    });
  },
  onRole() { this.refresh(); },
  onHours(e) {
    const op = getApp().globalData.operations.find(function (item) { return item.id === e.currentTarget.dataset.id; });
    op.durationHours = Number(e.detail.value);
  },
  onApply(e) {
    store.applyDuration(getApp().globalData, e.currentTarget.dataset.id);
    this.refresh();
  },
});
