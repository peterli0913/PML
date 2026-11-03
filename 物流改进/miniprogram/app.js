const store = require("./utils/store.js");

App({
  globalData: null,
  onLaunch() {
    const data = store.create();
    store.freeze(data);
    data.toast = "看板已抓取当前进度和周计划。改周计划后，这一页和小时需求一起变。";
    this.globalData = data;
  },
});
