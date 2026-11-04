Component({
  properties: { current: String, role: String },
  data: {
    tabs: [
      { id: "queue", title: "排队", url: "/pages/queue/index" },
      { id: "bays", title: "车位", url: "/pages/bays/index" },
      { id: "tanks", title: "储罐", url: "/pages/tanks/index" },
    ],
  },
  methods: {
    toggle() {
      const app = getApp();
      const next = app.globalData.role === "罐区" ? "司机" : "罐区";
      app.globalData.role = next;
      app.globalData.toast = next === "司机" ? "司机只看自己的去向和当前指令。" : "罐区可以安排车位、储罐和装卸。";
      wx.redirectTo({ url: next === "司机" ? "/pages/driver/index" : "/pages/queue/index" });
    },
    go(e) {
      const url = e.currentTarget.dataset.url;
      if (!url || url.indexOf("/" + this.data.current + "/") >= 0) return;
      wx.redirectTo({ url: url });
    },
  },
});
