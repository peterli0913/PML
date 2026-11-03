const store = require("../../utils/store.js");

Page({
  data: { role: "", toast: "", rows: [], canEdit: true },
  onShow() { this.refresh(); },
  refresh() { this.setData(store.durationView(getApp().globalData)); },
  onRole() { this.refresh(); },
  onHours(e) {
    store.setDuration(getApp().globalData, e.currentTarget.dataset.id, e.detail.value);
  },
  onApply(e) {
    store.applyDuration(getApp().globalData, e.currentTarget.dataset.id);
    this.refresh();
  },
});
