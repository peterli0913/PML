const fleet = require("../../utils/fleet.js");

Page({
  data: {},
  onShow() { this.setData(fleet.tankView(getApp().globalData)); },
});
