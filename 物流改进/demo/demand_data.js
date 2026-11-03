/* Illustrative week of batches. Not plant data. Clock is 2026-11-02 08:00. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.DemandData = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function create() {
    return {
      clock: "2026-11-02 08:00",
      hours: 168,
      cycles: { arrival: 24, inspect: 6, release: 18, unload: 4, buffer: 5 },
      inventories: {
        DMF: { qty: 36, low: 12 },
        ACN: { qty: 28, low: 10 },
        IPAc: { qty: 14, low: 6 },
        甲醇: { qty: 20, low: 8 },
      },
      inbound: {
        DMF: [{ hour: 30, qty: 16, code: "TJ4-在途-DMF" }],
        ACN: [{ hour: 18, qty: 8, code: "TJ4-在途-ACN" }],
        IPAc: [],
        甲醇: [],
      },
      batches: [
        { id: "B01", project: "PRJ-2408", step: "投料", opNo: "OP-12", manager: "王经理", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", qty: 24, mode: "持续", plannedStartHour: -8, durationHours: 36, progress: 0.4, status: "进行中" },
        { id: "B02", project: "PRJ-2411", step: "补料", opNo: "OP-03", manager: "王经理", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", qty: 18, mode: "持续", plannedStartHour: 20, durationHours: 30, progress: 0, status: "未开始" },
        { id: "B03", project: "PRJ-2416", step: "一次投入", opNo: "OP-01", manager: "李经理", workshop: "2号厂房", solvent: "DMF", materialCode: "SOL-DMF", qty: 10, mode: "单次", plannedStartHour: 70, durationHours: 1, progress: 0, status: "未开始" },
        { id: "B04", project: "PRJ-2412", step: "滴加", opNo: "OP-07", manager: "赵经理", workshop: "2号厂房", solvent: "ACN", materialCode: "SOL-ACN", qty: 22, mode: "持续", plannedStartHour: 8, durationHours: 48, progress: 0, status: "未开始" },
        { id: "B05", project: "PRJ-2409", step: "洗涤", opNo: "OP-04", manager: "赵经理", workshop: "2号厂房", solvent: "ACN", materialCode: "SOL-ACN", qty: 6, mode: "单次", plannedStartHour: 56, durationHours: 1, progress: 0, status: "未开始" },
        { id: "B06", project: "PRJ-2418", step: "投料", opNo: "OP-02", manager: "陈经理", workshop: "1号厂房", solvent: "IPAc", materialCode: "SOL-IPAc", qty: 16, mode: "持续", plannedStartHour: -10, durationHours: 16, progress: 0, status: "未开始" },
        { id: "B07", project: "PRJ-2420", step: "精制", opNo: "OP-09", manager: "陈经理", workshop: "3号厂房", solvent: "IPAc", materialCode: "SOL-IPAc", qty: 12, mode: "持续", plannedStartHour: 40, durationHours: 24, progress: 0, status: "未开始" },
        { id: "B08", project: "PRJ-2404", step: "一次投入", opNo: "OP-01", manager: "周经理", workshop: "3号厂房", solvent: "甲醇", materialCode: "SOL-MEOH", qty: 18, mode: "单次", plannedStartHour: 1, durationHours: 1, progress: 0, status: "未开始" },
        { id: "B09", project: "PRJ-2422", step: "保温补加", opNo: "OP-06", manager: "周经理", workshop: "3号厂房", solvent: "甲醇", materialCode: "SOL-MEOH", qty: 8, mode: "持续", plannedStartHour: 80, durationHours: 20, progress: 0, status: "未开始" },
        { id: "B10", project: "PRJ-2401", step: "投料", opNo: "OP-02", manager: "王经理", workshop: "1号厂房", solvent: "DMF", materialCode: "SOL-DMF", qty: 9, mode: "持续", plannedStartHour: 100, durationHours: 18, progress: 0, status: "未开始" },
      ],
    };
  }
  return { create: create };
});
