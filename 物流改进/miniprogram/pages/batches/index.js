const store = require("../../utils/store.js");

Page({
  data: { role: "", toast: "", rows: [] },
  onShow() { this.refresh(); },
  refresh() {
    const s = getApp().globalData;
    this.setData({ role: s.role, toast: s.toast, rows: s.batches });
  },
  onRole() { this.refresh(); },
  onField(e) {
    store.setBatchField(getApp().globalData, e.currentTarget.dataset.id, e.currentTarget.dataset.field, e.detail.value);
    this.refresh();
  },
});
