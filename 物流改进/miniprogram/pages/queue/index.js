const fleet = require("../../utils/fleet.js");

Page({
  data: {},
  onShow() { this.refresh(); },
  refresh() { this.setData(fleet.queueView(getApp().globalData)); },
  onFilter(e) {
    getApp().globalData.filter = e.currentTarget.dataset.filter;
    this.refresh();
  },
  onOpen(e) {
    wx.navigateTo({ url: "/pages/order/index?id=" + e.currentTarget.dataset.id });
  },
});
