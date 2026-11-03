const PAGES = [
  { id: "demand", title: "更新溶剂需求", url: "/pages/demand/index" },
  { id: "batches", title: "更新批次清单", url: "/pages/batches/index" },
  { id: "duration", title: "更新单操作时长", url: "/pages/duration/index" },
  { id: "board", title: "看板抓取当前进度及周计划", url: "/pages/board/index" },
  { id: "hourly", title: "未来一周小时需求", url: "/pages/hourly/index" },
];

Component({
  properties: {
    current: String,
    title: String,
    toast: String,
    role: String,
  },
  data: { pages: PAGES },
  methods: {
    go(e) {
      const url = e.currentTarget.dataset.url;
      if (!url || url.indexOf("/" + this.data.current + "/") >= 0) return;
      wx.redirectTo({ url: url });
    },
    toggleRole() {
      const app = getApp();
      const next = app.globalData.role === "生产经理" ? "物流计划员" : "生产经理";
      app.globalData.role = next;
      app.globalData.toast = next === "生产经理"
        ? "生产经理可以改周计划、批次和操作时长。看板与小时需求跟着变。"
        : "物流计划员查看进度和小时需求。周计划、批次和时长为只读。";
      this.triggerEvent("rolechange");
    },
  },
});
