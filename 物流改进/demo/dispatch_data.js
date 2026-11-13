/* One hundred deterministic dispatch records. Not plant data. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.DispatchData = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const MATERIALS = ["DMF", "ACN", "MTBE", "IPAc", "THF", "DCM", "甲醇", "甲苯", "正己烷", "乙酸乙酯"];
  const WASTES = ["废DMF", "废ACN", "废甲醇", "废甲苯"];
  const SUPPLIERS = [
    ["天津德凯溶剂", true],
    ["山东齐鲁溶剂", true],
    ["江苏华昌化工", true],
    ["上海京华储运", true],
    ["河北永盛", true],
    ["浙江卫星贸易", true],
    ["辽宁辽化配送", false],
    ["安徽中能", false],
  ];
  const RECEIVERS = [
    ["接收商甲", true, 80],
    ["接收商丙", true, 50],
    ["接收商丁", true, 36],
    ["接收商乙", false, 20],
  ];
  const DRIVERS = ["张师傅", "李师傅", "王师傅", "赵师傅", "刘师傅", "陈师傅"];
  const INBOUND_PLAN = [
    ["待供应链下达", 3],
    ["待采购转发", 3],
    ["待供应商上报", 4],
    ["待确认发车", 4],
    ["在途", 8],
    ["到场预告", 5],
    ["待门卫核查", 4],
    ["待罐区入厂指令", 4],
    ["厂外等待", 3],
    ["待收货递检", 4],
    ["待取样", 4],
    ["原地等待放行", 4],
    ["出厂等待放行", 3],
    ["待重新入厂", 3],
    ["待置换卸车", 4],
    ["卸车中", 3],
    ["已断管离场", 5],
    ["异常暂停", 2],
  ];
  const WASTE_PLAN = [
    ["待供应链下达", 3],
    ["待采购转发", 3],
    ["待供应商上报", 3],
    ["待确认发车", 3],
    ["在途", 5],
    ["到场预告", 3],
    ["待门卫核查", 3],
    ["待入厂装车", 3],
    ["装车中", 2],
    ["待检斤联单", 1],
    ["已离场", 1],
  ];

  function pad(n) { return String(n).padStart(3, "0"); }

  function base(i, kind, status) {
    const material = kind === "溶剂到货" ? MATERIALS[i % MATERIALS.length] : WASTES[i % WASTES.length];
    const supplier = SUPPLIERS[i % SUPPLIERS.length];
    const receiver = RECEIVERS[i % RECEIVERS.length];
    const passedPurchase = ["待供应链下达", "待采购转发"].indexOf(status) < 0;
    const useSupplier = passedPurchase && !supplier[1] ? SUPPLIERS[0] : supplier;
    const useReceiver = passedPurchase && !receiver[1] ? RECEIVERS[0] : receiver;
    const reported = ["待供应商上报", "待供应链下达", "待采购转发"].indexOf(status) < 0;
    const code = "TJ4-1102-" + pad(i + 1);
    const order = {
      code: code,
      kind: kind,
      status: status,
      material: material,
      qty: 8 + (i % 12) * 2,
      tank: kind === "溶剂到货" ? "T" + material : "W" + material,
      project: "PRJ-24" + pad((i % 20) + 1),
      needAt: "2026-11-0" + (2 + (i % 3)) + " 08:00",
      supplier: useSupplier[0],
      supplierQualified: useSupplier[1],
      receiver: useReceiver[0],
      receiverReady: useReceiver[1],
      quotaLeft: useReceiver[2],
      plate: reported ? "津" + "ABCDEFGH"[i % 8] + "演示" + pad(200 + i) : "",
      driver: reported ? DRIVERS[i % DRIVERS.length] : "",
      phone: reported ? "1380000" + pad(300 + i) : "",
      coa: kind === "废液装车" ? false : reported,
      distanceKm: null,
      bufferHours: 0,
      etaNote: "",
      exception: "",
      bay: "",
      rcvNo: "",
      batch: "",
      releaseHours: i % 5 === 0 ? 3.5 : 1.5,
      waitMode: "",
      waitPlace: "",
      weight: null,
      manifestNo: "",
      released: false,
      closed: status === "已断管离场" || status === "已离场",
      tankOnline: true,
      tankFree: 80,
      exchanges: [],
      log: [],
    };
    if (status === "待罐区入厂指令" && i % 9 === 0) order.tankFree = 1;
    if (status === "在途") order.distanceKm = 40 + (i % 8) * 15;
    if (status === "到场预告") order.distanceKm = 6 + (i % 8);
    if (status === "待门卫核查" || ["待罐区入厂指令", "厂外等待", "待收货递检", "待取样", "原地等待放行", "出厂等待放行", "待重新入厂", "待置换卸车", "卸车中", "已断管离场", "待入厂装车", "装车中", "待检斤联单", "已离场"].indexOf(status) >= 0) {
      order.distanceKm = status === "待门卫核查" ? 2 + (i % 2) : 0;
    }
    if (["厂外等待", "出厂等待放行", "待重新入厂"].indexOf(status) >= 0) order.waitPlace = "厂外停车场 " + ((i % 3) + 1) + " 号";
    if (["待收货递检", "待取样", "原地等待放行", "出厂等待放行", "待重新入厂", "待置换卸车", "卸车中", "已断管离场", "装车中", "待检斤联单", "已离场"].indexOf(status) >= 0) {
      const api = typeof Dispatch !== "undefined" ? Dispatch : (typeof globalThis !== "undefined" ? globalThis.Dispatch : null);
      order.bay = api && api.bayFor ? api.bayFor(material) : "";
    }
    if (["待取样", "原地等待放行", "出厂等待放行", "待重新入厂", "待置换卸车", "卸车中", "已断管离场"].indexOf(status) >= 0) {
      order.rcvNo = "RCV-" + pad(i + 1);
    }
    if (["原地等待放行", "出厂等待放行", "待重新入厂", "待置换卸车", "卸车中", "已断管离场"].indexOf(status) >= 0) {
      order.batch = "BN-" + material + "-" + pad(i + 1);
      order.waitMode = status === "出厂等待放行" || status === "待重新入厂" ? "出厂等待" : "原地等待";
    }
    if (status === "待重新入厂" || status === "待置换卸车" || status === "卸车中" || status === "已断管离场") order.released = true;
    if (status === "待检斤联单" || status === "已离场") order.weight = order.qty;
    if (status === "已离场") order.manifestNo = "LD-" + pad(i + 1);
    if (status === "异常暂停") {
      order.exception = "高速临时管制，预计晚到 2 小时";
      order.distanceKm = 60;
      order.plate = order.plate || ("津A演示" + pad(200 + i));
      order.driver = order.driver || "王师傅";
      order.phone = order.phone || "13800006666";
      order.coa = kind === "溶剂到货";
    }
    if (status === "待采购转发" && kind === "溶剂到货" && i % 3 === 0) {
      order.supplier = "辽宁辽化配送";
      order.supplierQualified = false;
    }
    if (i === 0) {
      order.code = "TJ4-DEMO-A";
      order.material = "IPAc";
      order.tank = "T-IPAc";
      order.qty = 12;
      order.releaseHours = 1.5;
      order.supplier = "天津德凯溶剂";
      order.supplierQualified = true;
    }
    if (i === 1) {
      order.code = "TJ4-DEMO-B";
      order.material = "DMF";
      order.tank = "T-DMF";
      order.qty = 20;
      order.releaseHours = 3.5;
      order.supplier = "山东齐鲁溶剂";
      order.supplierQualified = true;
    }
    return order;
  }

  function expand(plan, kind, start) {
    const list = [];
    let n = start;
    plan.forEach(function (pair) {
      for (let c = 0; c < pair[1]; c++) {
        list.push(base(n, kind, pair[0]));
        n += 1;
      }
    });
    return list;
  }

  function generate() {
    const inbound = expand(INBOUND_PLAN, "溶剂到货", 0);
    const waste = expand(WASTE_PLAN, "废液装车", inbound.length);
    return inbound.concat(waste);
  }

  return { generate: generate, INBOUND_PLAN: INBOUND_PLAN, WASTE_PLAN: WASTE_PLAN };
});
