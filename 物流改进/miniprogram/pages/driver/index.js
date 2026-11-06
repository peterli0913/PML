const orders = require("../../utils/orders.js");

Page({
  data: {
    role: "司机",
    cars: [],
    current: { instruction: "", bay: "", tank: "", plate: "", material: "", qty: "", showWhere: false, canConfirm: false, id: "" },
  },
  onShow() { this.refresh(); },
  refresh() { this.setData(orders.driverView(getApp().globalData)); },
  onCar(e) {
    getApp().globalData.focusId = e.currentTarget.dataset.id;
    this.refresh();
  },
  onConfirm() {
    orders.confirm(getApp().globalData, this.data.current.id);
    this.refresh();
  },
});
