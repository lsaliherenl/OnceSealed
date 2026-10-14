"""D2: chart and summary of the scale replay (docs/figures/scale_gas.png, data/derived/scale/summary.json).

    python scripts/scale_chart.py

Reads data/derived/scale/<project>-<vintage>-{linear,hinted}.csv written by scripts/scale_replay.py.
"""

import csv
import json
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from core.config import PROJECT_ROOT  # noqa: E402

SCALE = PROJECT_ROOT / "data" / "derived" / "scale"
BLOCK_GAS = 36_000_000
# dataviz reference palette (light): categorical slots 1-2, ink and chrome tokens
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
HINTED, LINEAR = "#2a78d6", "#eb6834"


def read(name: str) -> list[dict]:
    path = SCALE / f"{name}.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]


def summary(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["ok"] == 1]
    failed = next((int(r["n"]) for r in rows if r["ok"] == 0), None)
    return {"replayed": len(rows), "succeeded": len(ok), "first_failure": failed,
            "gas_first": int(ok[0]["gas_used"]) if ok else None, "gas_last": int(ok[-1]["gas_used"]) if ok else None,
            "gas_max": int(max(r["gas_used"] for r in ok)) if ok else None,
            "median_latency_ms": round(st.median(r["latency_ms"] for r in ok), 1) if ok else None}


def main() -> None:
    lin, hin = read("VCS766-2009-linear"), read("VCS766-2009-hinted")
    out = {"block_gas_limit": BLOCK_GAS, "real_history_retirements": 38_382,
           "VCS766-2009-linear": summary(lin), "VCS766-2009-hinted": summary(hin),
           "VCS1477-2020-linear": summary(read("VCS1477-2020-linear")),
           "VCS1477-2020-hinted": summary(read("VCS1477-2020-hinted"))}
    (SCALE / "summary.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axhline(BLOCK_GAS / 1e6, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(0, BLOCK_GAS / 1e6 + 0.6, "Block gas limit (36M)", color=INK_2, fontsize=10)
    if lin:
        ax.plot([r["n"] for r in lin if r["ok"]], [r["gas_used"] / 1e6 for r in lin if r["ok"]],
                color=LINEAR, lw=2, zorder=3)
        fail = out["VCS766-2009-linear"]["first_failure"]
        last = [r for r in lin if r["ok"]][-1]
        ax.annotate(f"Linear scan: fails at retirement {fail:,}" if fail else "Linear scan",
                    (last["n"], last["gas_used"] / 1e6), xytext=(10, -14), textcoords="offset points",
                    color=INK, fontsize=11, fontweight="bold")
    if hin:
        xs = [r["n"] for r in hin if r["ok"]]
        ax.plot(xs, [r["gas_used"] / 1e6 for r in hin if r["ok"]], color=HINTED, lw=2.4, zorder=4)
        g = out["VCS766-2009-hinted"]["gas_last"]
        ax.annotate(f"Hinted sorted list: {g / 1e3:,.0f}k gas, constant ({len(xs):,} retirements)",
                    (xs[0], g / 1e6), xytext=(6, 10), textcoords="offset points", ha="left",
                    color=INK, fontsize=11, fontweight="bold")
    ax.set_xlim(0, max(38_382, max((r["n"] for r in hin), default=0)))
    ax.set_ylim(0, 40)
    ax.set_xlabel("Retirements already recorded in the batch", color=INK_2)
    ax.set_ylabel("Gas per retirement (millions)", color=INK_2)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    ax.set_title("Real retirement history: the linear check breaks, the hinted list stays flat",
                 loc="left", color=INK, fontsize=14, fontweight="bold", pad=26)
    ax.text(0, 1.03, "VCS766, vintage 2009: 38,382 real retirements from OffsetsDB replayed on a local chain",
            transform=ax.transAxes, color=INK_2, fontsize=11)
    fig.text(0.01, 0.01, "Source: scripts/scale_replay.py on Anvil; CarbonPlan OffsetsDB snapshot 2026-06-01.",
             color=MUTED, fontsize=8.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.84, bottom=0.14)
    path = PROJECT_ROOT / "docs" / "figures" / "scale_gas.png"
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
