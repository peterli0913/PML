const fleet = require("../../utils/fleet.js");

Page({
  data: {},
  onShow() { this.setData(fleet.bayView(getApp().globalData)); },
});
