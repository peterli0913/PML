const orders = require("./utils/orders.js");

App({
  onLaunch() {
    this.globalData = orders.create();
  },
});
