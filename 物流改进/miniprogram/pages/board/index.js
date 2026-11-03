const store = require("../../utils/store.js");

Page({
  data: {},
  onShow() { this.refresh(); },
  refresh() { this.setData(store.boardView(getApp().globalData)); },
  onRole() { this.refresh(); },
  onQty(e) {
    store.setWeekQty(getApp().globalData, e.currentTarget.dataset.id, e.detail.value);
    this.refresh();
  },
});
