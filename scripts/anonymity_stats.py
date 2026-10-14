"""Who retires carbon credits? Measure how often the beneficiary is identifiable in OffsetsDB.

    python scripts/anonymity_stats.py

Writes docs/anonymity_stats.md (method, tables, caveats) and docs/figures/anonymity_trend.png.
Needs the local OffsetsDB snapshot in data/raw/offsetsdb/ (see README).
"""

import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from core.config import PROJECT_ROOT  # noqa: E402
from core.data import anonymity as an  # noqa: E402
from core.data import offsetsdb  # noqa: E402

DOCS = PROJECT_ROOT / "docs"
FIRST_YEAR, LAST_FULL_YEAR = 2016, 2025

# Chart tokens (dataviz reference palette, light mode): accent + de-emphasis gray, text in ink tokens.
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
ACCENT = "#2a78d6"

LABELS = {
    "named": "Named beneficiary",
    "named_in_note": "Named only in free-text note",
    "intermediary_only": "Only an intermediary named (\"... clients\")",
    "explicitly_undisclosed": "Explicitly undisclosed (\"not disclosed\", \"anonymous\", \"private offset\")",
    "generic_note": "Free-text note without a beneficiary",
    "no_information": "No beneficiary information at all",
}


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def table(df: pd.DataFrame, index_name: str) -> str:
    cols = an.CLASSES
    head = f"| {index_name} | " + " | ".join(LABELS[c].split(" (")[0] for c in cols) + " | Not identifiable | Retired (Mt) |"
    sep = "|" + "---|" * (len(cols) + 3)
    rows = []
    for idx, r in df.iterrows():
        not_id = sum(r[c] for c in an.NOT_IDENTIFIABLE)
        rows.append(f"| {idx} | " + " | ".join(pct(r[c]) for c in cols) + f" | **{pct(not_id)}** | {r['total'] / 1e6:,.1f} |")
    return "\n".join([head, sep, *rows])


def chart(by_year: pd.DataFrame, path) -> None:
    years = by_year.index.astype(int)
    not_id = by_year[an.NOT_IDENTIFIABLE].sum(axis=1) * 100
    undisclosed = by_year["explicitly_undisclosed"] * 100

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.plot(years, not_id, color=MUTED, lw=2, marker="o", ms=5, mec=SURFACE, mew=2, zorder=3)
    ax.plot(years, undisclosed, color=ACCENT, lw=2.4, marker="o", ms=6, mec=SURFACE, mew=2, zorder=4)

    # Direct labels at the line ends (identity never by color alone)
    ax.annotate(f"No identifiable beneficiary  {not_id.iloc[-1]:.0f}%", (years[-1], not_id.iloc[-1]),
                xytext=(10, 0), textcoords="offset points", va="center", color=INK_2, fontsize=11)
    ax.annotate(f"Explicitly undisclosed  {undisclosed.iloc[-1]:.0f}%", (years[-1], undisclosed.iloc[-1]),
                xytext=(10, 0), textcoords="offset points", va="center", color=INK, fontsize=11, fontweight="bold")

    ax.set_ylim(0, 100)
    ax.set_xlim(years[0] - 0.4, years[-1] + 0.4)
    ax.set_xticks(years)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter())
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    ax.set_title(f"Retirements explicitly marked \"undisclosed\" rose from 0% to {undisclosed.iloc[-1]:.0f}%",
                 loc="left", color=INK, fontsize=15, fontweight="bold", pad=26)
    ax.text(0, 1.03, "Share of retired tonnes per year, all registries in OffsetsDB. "
            "More than half still name no identifiable beneficiary.", transform=ax.transAxes, color=INK_2, fontsize=11)
    fig.text(0.01, 0.01, f"Source: CarbonPlan OffsetsDB snapshot {offsetsdb.snapshot_date()}; "
             "classification: OnceSealed (core/data/anonymity.py).", color=MUTED, fontsize=8.5)
    fig.subplots_adjust(left=0.07, right=0.64, top=0.84, bottom=0.12)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    r = an.retirements_with_class(offsetsdb.credits())
    r["period"] = pd.cut(r["year"], [0, 2018, 2022, 2026], labels=["≤2018", "2019–2022", "2023–2026*"])
    overall = an.shares(r)
    overall["total"] = r["quantity"].sum()
    overall.index = ["All years"]
    rows = an.shares(r, weight=None).iloc[0]
    by_period = an.shares(r, "period")
    by_year = an.shares(r[(r["year"] >= FIRST_YEAR) & (r["year"] <= LAST_FULL_YEAR)], "year")
    by_year.index = by_year.index.astype(int)
    by_registry = an.shares(r[r["year"] >= 2023], "registry")
    by_registry.index = [f"{offsetsdb.REGISTRY_NAMES.get(i, i)} ({i})" for i in by_registry.index]

    recent = by_period.loc["2023–2026*"]
    early = by_period.loc["≤2018"]
    not_id_recent = sum(recent[c] for c in an.NOT_IDENTIFIABLE)
    not_id_recent_low = not_id_recent - recent["generic_note"]

    fig_path = DOCS / "figures" / "anonymity_trend.png"
    chart(by_year, fig_path)

    md = f"""# Who retires carbon credits? (OffsetsDB analysis)

Generated by `scripts/anonymity_stats.py` from the CarbonPlan OffsetsDB snapshot of **{offsetsdb.snapshot_date()}**
({len(r):,} retirement records, {r['quantity'].sum() / 1e9:.2f} billion tonnes, 7 registries).

## Headline numbers

- **Explicitly undisclosed retirements are rising:** {pct(early['explicitly_undisclosed'])} of retired tonnes up to 2018,
  **{pct(recent['explicitly_undisclosed'])}** in 2023–2026*. These records say outright "not disclosed", "not public",
  "anonymous" or "private offset" - a conservative lower bound for deliberate anonymity.
- **No identifiable beneficiary:** in 2023–2026*, **{pct(not_id_recent_low)}–{pct(not_id_recent)}** of retired tonnes
  name no identifiable beneficiary (the range depends on whether free-text notes without a recognised naming pattern
  hide a name; spot checks found a few that do).

![Trend]({fig_path.relative_to(DOCS).as_posix()})

## Method

Each retirement record is placed in exactly one class, in this order of precedence
(definitions in [`core/data/anonymity.py`](../core/data/anonymity.py)):

| Class | Rule |
|---|---|
| Explicitly undisclosed | beneficiary or note is exactly a marker such as "not disclosed", "not public", "anonymous", "private offset", or contains "for anonymous" / "retire anonymously" |
| Only an intermediary | beneficiary (or note, if no beneficiary) names clients/customers/end users of a reseller, e.g. "4air client" |
| Named beneficiary | the beneficiary field or CarbonPlan's harmonized beneficiary is filled |
| Named only in note | no beneficiary field, but the note names one ("retired on behalf of X", "order ... for X") |
| Note without beneficiary | free text only, e.g. "environmental benefit", order numbers |
| No information | beneficiary, harmonized beneficiary and note are all empty |

*Identifiable* = named beneficiary or named only in note. Shares are weighted by **tonnes** unless stated.
`retirement_account` is ignored because it names the account holder (often a broker), not the beneficiary.
Markers are matched exactly or as whole phrases, so company names like "XYZ Private Limited" are not counted as anonymous.

## Results

### By period (tonnes)

{table(by_period, "Period")}

\\* 2026 covers January to the snapshot date.

### By registry, 2023–2026* (tonnes)

{table(by_registry, "Registry")}

### By year (tonnes)

{table(by_year, "Year")}

### All years

By tonnes:

{table(overall, "Scope")}

By record count: named {pct(rows['named'])}, named in note {pct(rows['named_in_note'])}, intermediary only
{pct(rows['intermediary_only'])}, explicitly undisclosed {pct(rows['explicitly_undisclosed'])}, note without beneficiary
{pct(rows['generic_note'])}, no information {pct(rows['no_information'])}.

## Caveats

- **Registry practice, not only buyer choice.** "No information" partly reflects what each registry records and
  publishes; the share differs a lot between registries and over time.
- **Heuristic classification.** Free-text notes are classified with patterns; some notes without a recognised pattern
  still contain a name, hence the range in the headline.
- **Snapshot.** OffsetsDB updates were paused at the time of download; numbers describe the {offsetsdb.snapshot_date()}
  snapshot. CarbonPlan's own figure (0.67 of 1.34 billion retired credits with beneficiary information) used an
  earlier snapshot and a broader definition of "information".
- Data: CarbonPlan OffsetsDB, used under its Terms of Data Access; the underlying records belong to the registries.
"""
    (DOCS / "anonymity_stats.md").write_text(md, encoding="utf-8")
    print(f"explicitly undisclosed: <=2018 {pct(early['explicitly_undisclosed'])} -> 2023-26 {pct(recent['explicitly_undisclosed'])}")
    print(f"no identifiable beneficiary 2023-26: {pct(not_id_recent_low)} - {pct(not_id_recent)}")
    print(f"wrote docs/anonymity_stats.md and {fig_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
