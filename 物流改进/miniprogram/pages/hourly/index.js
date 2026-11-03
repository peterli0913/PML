const store = require("../../utils/store.js");

Page({
  data: { solvent: "甲醇" },
  onShow() { this.refresh(); },
  refresh(solvent) {
    const name = solvent || this.data.solvent;
    this.setData(store.hourlyView(getApp().globalData, name));
  },
  onRole() { this.refresh(); },
  onSolvent(e) { this.refresh(e.currentTarget.dataset.name); },
  onFreeze() {
    store.freeze(getApp().globalData);
    this.refresh();
  },
});
