const orders = require("../../utils/orders.js");

Page({
  data: { draftMaterial: "甲醇", draftQty: "10", draftTime: "16:00" },
  onShow() { this.refresh(); },
  refresh() {
    const view = orders.queueView(getApp().globalData);
    this.setData(Object.assign({ draftMaterial: this.data.draftMaterial, draftQty: this.data.draftQty, draftTime: this.data.draftTime }, view));
  },
  onFilter(e) {
    getApp().globalData.filter = e.currentTarget.dataset.filter;
    this.refresh();
  },
  onOpen(e) {
    wx.navigateTo({ url: "/pages/order/index?id=" + e.currentTarget.dataset.id });
  },
  onMaterial(e) { this.setData({ draftMaterial: e.currentTarget.dataset.material }); },
  onQty(e) { this.setData({ draftQty: e.detail.value }); },
  onTime(e) { this.setData({ draftTime: e.detail.value }); },
  onCreate() {
    orders.createOrder(getApp().globalData, {
      material: this.data.draftMaterial,
      qty: this.data.draftQty,
      planTime: this.data.draftTime,
    });
    this.refresh();
  },
});
