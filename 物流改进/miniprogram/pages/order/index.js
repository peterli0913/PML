const orders = require("../../utils/orders.js");

Page({
  data: { missing: true, plateDraft: "" },
  onLoad(query) { this.orderId = query.id; },
  onShow() { this.refresh(); },
  refresh() { this.setData(Object.assign({ plateDraft: this.data.plateDraft }, orders.orderView(getApp().globalData, this.orderId))); },
  onAllow() {
    orders.allow(getApp().globalData, this.orderId);
    this.refresh();
  },
  onLeave() {
    orders.leave(getApp().globalData, this.orderId);
    this.refresh();
  },
  onPull() {
    orders.pullPortal(getApp().globalData, this.orderId);
    this.refresh();
  },
  onPlate(e) { this.setData({ plateDraft: e.detail.value }); },
  onSavePlate() {
    orders.setPlate(getApp().globalData, this.orderId, this.data.plateDraft);
    this.refresh();
  },
});
