const orders = require("../../utils/orders.js");

Page({
  data: {},
  onShow() { this.setData(orders.bayView(getApp().globalData)); },
});
