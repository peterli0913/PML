const fleet = require("../../utils/fleet.js");

Page({
  data: {
    role: "司机",
    cars: [],
    current: { steps: [], instruction: "", bay: "", tank: "", plate: "", material: "", qty: "", queueText: "", whereLabel: "", canException: false },
  },
  onShow() { this.refresh(); },
  refresh() { this.setData(fleet.driverView(getApp().globalData)); },
  onCar(e) {
    fleet.setFocus(getApp().globalData, e.currentTarget.dataset.id);
    this.refresh();
  },
  onException() {
    fleet.act(getApp().globalData, this.data.current.id, "report_exception", { text: "路上异常，先停车" });
    this.refresh();
  },
});
