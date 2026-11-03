const store = require("../../utils/store.js");

Page({
  data: { role: "", toast: "", rows: [], canEdit: true },
  onShow() { this.refresh(); },
  refresh() { this.setData(store.batchView(getApp().globalData)); },
  onRole() { this.refresh(); },
  onField(e) {
    store.setBatchField(getApp().globalData, e.currentTarget.dataset.id, e.currentTarget.dataset.field, e.detail.value);
    this.refresh();
  },
});
