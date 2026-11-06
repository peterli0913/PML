Component({
  properties: { current: String, role: String },
  data: {
    tabs: [
      { id: "queue", title: "工单", url: "/pages/queue/index" },
      { id: "bays", title: "车位", url: "/pages/bays/index" },
    ],
  },
  methods: {
    toggle() {
      const app = getApp();
      const next = app.globalData.role === "厂内" ? "司机" : "厂内";
      app.globalData.role = next;
      app.globalData.toast = next === "司机"
        ? "司机只确认自己的车，并查看能不能进入。"
        : "厂内维护当天工单，罐区点允许进入和已离开。";
      wx.redirectTo({ url: next === "司机" ? "/pages/driver/index" : "/pages/queue/index" });
    },
    go(e) {
      const url = e.currentTarget.dataset.url;
      if (!url || url.indexOf("/" + this.data.current + "/") >= 0) return;
      wx.redirectTo({ url: url });
    },
  },
});
