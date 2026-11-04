const fleet = require("./utils/fleet.js");

App({
  onLaunch() {
    this.globalData = fleet.create();
  },
});
