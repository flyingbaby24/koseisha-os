import type { Metric } from "../types";
import { isCount } from "../ui";

export function Logo() {
  return (
    <>
      <span className="brand-mark" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </span>
      <span className="brand-name">
        こどもアトラス<span>KODOMO ATLAS</span>
      </span>
    </>
  );
}

/** Counts compare with the 1,896-unit simple mean; rates with national aggregates. */
export function BaselineLabel({ metric }: { metric: Metric }) {
  return <>{isCount(metric) ? "自治体平均（参考）" : "全国集計値"}</>;
}
