const store = require("../../utils/store.js");

Page({
  data: { role: "", toast: "", rows: [], total: 0, canEdit: true },
  onShow() { this.refresh(); },
  refresh() { this.setData(store.demandView(getApp().globalData)); },
  onRole() { this.refresh(); },
  onQty(e) {
    store.setWeekQty(getApp().globalData, e.currentTarget.dataset.id, e.detail.value);
    this.refresh();
  },
});
