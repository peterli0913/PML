const fleet = require("../../utils/fleet.js");

Page({
  data: { missing: true },
  onLoad(query) { this.orderId = query.id; },
  onShow() { this.refresh(); },
  refresh() {
    this.setData(fleet.orderView(getApp().globalData, this.orderId));
  },
  onAct(e) {
    const action = e.currentTarget.dataset.action;
    const payload = {};
    if (e.currentTarget.dataset.km) payload.km = Number(e.currentTarget.dataset.km);
    if (e.currentTarget.dataset.place) payload.place = e.currentTarget.dataset.place;
    fleet.act(getApp().globalData, this.orderId, action, payload);
    this.refresh();
  },
  onMove(e) {
    fleet.move(getApp().globalData, this.orderId, e.currentTarget.dataset.how);
    this.refresh();
  },
});
