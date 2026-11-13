/* Shared rules for the 13 logistics programs. Demo and unit tests both use this file. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Calc = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function round1(n) {
    return Math.round((Number(n) + Number.EPSILON) * 10) / 10;
  }

  function sum(list, pred, pick) {
    return round1(
      list.reduce(function (acc, item) {
        return acc + (pred(item) ? Number(pick(item)) : 0);
      }, 0)
    );
  }

  /* 溶剂建议量 = max(需求 − 余量 − 在途 − 已放行待卸, 下限 − 余量, 0)
     优先分值 = 余量 − 需求。思维导图中的「液位」在这里按换算后的余量（吨）理解。 */
  function solventSuggestion(tank, demandQty, inTransit, released) {
    if (!tank.online) {
      return {
        blocked: true,
        suggest: 0,
        priority: null,
        math: tank.id + " 数据中断，不生成草案",
      };
    }
    if (!tank.point) {
      return {
        blocked: true,
        suggest: 0,
        priority: null,
        math: tank.id + " 没有 DCS 点位对照，不生成草案",
      };
    }
    const gapDemand = round1(demandQty - tank.qty - inTransit - released);
    const gapLow = round1(tank.low - tank.qty);
    const suggest = round1(Math.max(gapDemand, gapLow, 0));
    const priority = round1(tank.qty - demandQty);
    const math =
      "余量 " + tank.qty + " − 需求 " + demandQty +
      " − 在途 " + inTransit + " − 已放行待卸 " + released +
      "；需求缺口 " + gapDemand + " 吨，下限缺口 " + gapLow +
      " 吨；优先分值（余量−需求）" + priority;
    return { blocked: false, suggest: suggest, priority: priority, math: math, gapDemand: gapDemand, gapLow: gapLow };
  }

  /* 废液建议量 = max(当前容积 + 已确认产出 − 上限容积, 0) */
  function wasteSuggestion(tank, outputQty) {
    if (!tank.online) {
      return { blocked: true, suggest: 0, math: tank.id + " 数据中断，不生成草案" };
    }
    const ceiling = round1(tank.cap * tank.high / 100);
    const suggest = round1(Math.max(tank.qty + outputQty - ceiling, 0));
    const free = round1(ceiling - tank.qty);
    const math =
      "上限容积 " + ceiling + " 吨（罐容 " + tank.cap + " × 上限 " + tank.high +
      "%）；当前 " + tank.qty + " 吨，剩余空间 " + free +
      " 吨，已确认产出 " + outputQty + " 吨";
    return { blocked: false, suggest: suggest, math: math, ceiling: ceiling, free: free };
  }

  function hoursBetween(startIso, endIso) {
    const a = new Date(startIso).getTime();
    const b = new Date(endIso).getTime();
    if (!a || !b) return null;
    return round1((b - a) / 36e5);
  }

  function canIssueSolvent(supplier) {
    if (!supplier) return { ok: false, reason: "还没有选择供应商" };
    if (!supplier.qualified) return { ok: false, reason: supplier.name + " 尚未经过 QA 确认，不能写入已下达计划" };
    return { ok: true, reason: "" };
  }

  function canIssueWaste(receiver, qty) {
    if (!receiver) return { ok: false, reason: "还没有选择接收商" };
    if (!receiver.ready) return { ok: false, reason: receiver.name + " 手续未齐，不能下达装车" };
    const left = round1(receiver.quota - receiver.used);
    if (left + 1e-9 < qty) return { ok: false, reason: receiver.name + " 联单余量只剩 " + left + " 吨，不够 " + qty + " 吨" };
    return { ok: true, reason: "" };
  }

  function bayCompatible(bayTank, solvent) {
    if (!bayTank) return { ok: false, reason: "这个鹤管没有对应储罐" };
    if (bayTank.solvent !== solvent) {
      return { ok: false, reason: bayTank.bay + " 对应 " + bayTank.solvent + "，与本车 " + solvent + " 不一致，不能确认" };
    }
    if (!bayTank.online) return { ok: false, reason: bayTank.id + " 液位中断，不能分配卸车" };
    return { ok: true, reason: "种类一致，且液位采集正常" };
  }

  return {
    round1: round1,
    sum: sum,
    solventSuggestion: solventSuggestion,
    wasteSuggestion: wasteSuggestion,
    hoursBetween: hoursBetween,
    canIssueSolvent: canIssueSolvent,
    canIssueWaste: canIssueWaste,
    bayCompatible: bayCompatible,
  };
});
