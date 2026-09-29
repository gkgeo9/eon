"""Snapshot the facts the figures need into figure-data/, so rendering needs no database.

Reads data/eon.db and data/archive/fintel.db read-only, the evaluation outputs,
and git metadata. Writes figure-data/evidence.json and figure-data/run.json.
Run from the eon root after evaluate_backtest.py:

  python docs/whitepaper/prepare_figure_data.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "figure-data"
DB = ROOT / "data/eon.db"
ARCHIVE = ROOT / "data/archive/fintel.db"
EVALUATION = HERE / "evaluation"
ORIGIN = Path("/Users/gkg/PycharmProjects/stock_stuff_06042025/10K_automator")
MARKET_BATCH = "all_comp_08022026"
OPTIONS_BATCH = "all_companies_options"
SPECIMEN = ("AAPL", 2025)
# Commits that date the three designs; dates are read from git, not typed in.
MILESTONES = {
    "first_commit": "eba182d",
    "workflow_builder_added": "deb71a4",
    "workflow_builder_removed": "694b11e",
    "market_batch_cli": "aee13b6",
    "rebrand_to_eon": "c87e25a",
    "backtester_added": "5d53983",
    "cspp_split_into_four_calls": "ff17ee3",
    "moonshot_excellence_single_call": "d5ed39c",
    "anchored_scores_in_code": "162185a",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)


def git_date(commit: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "log", "-1", "--format=%ad", "--date=short", commit],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def corpus(con: sqlite3.Connection) -> dict[str, Any]:
    rows = con.execute(
        "SELECT ticker, fiscal_year FROM analysis_results WHERE result_type = 'SimplifiedAnalysis'"
    ).fetchall()
    unique = set(rows)
    models: Counter[str] = Counter()
    for (config,) in con.execute(
        "SELECT config_json FROM analysis_runs WHERE analysis_type = 'multi' "
        "AND status = 'completed'"
    ):
        models[json.loads(config or "{}").get("model", "unknown")] += 1
    return {
        "stored_readings": len(rows),
        "unique_company_years": len(unique),
        "tickers": len({t for t, _ in unique}),
        "by_fiscal_year": dict(sorted(Counter(y for _, y in unique).items())),
        "completed_multi_runs_by_model": dict(models),
        "result_types": dict(
            con.execute(
                "SELECT result_type, COUNT(*) FROM analysis_results GROUP BY 1"
            ).fetchall()
        ),
    }


def specimen(con: sqlite3.Connection) -> dict[str, Any]:
    ticker, year = SPECIMEN
    row_id, payload = con.execute(
        "SELECT id, result_json FROM analysis_results WHERE result_type = 'SimplifiedAnalysis' "
        "AND ticker = ? AND fiscal_year = ? ORDER BY id LIMIT 1",
        (ticker, year),
    ).fetchone()
    data = json.loads(payload)
    filed = con.execute(
        "SELECT MIN(filing_date) FROM file_cache WHERE ticker = ? AND fiscal_year = ? "
        "AND filing_type = '10-K'",
        (ticker, year),
    ).fetchone()[0]

    def first_sentence(text: str) -> str:
        return re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]

    lenses = {}
    for lens, verdict_key in [
        ("buffett", "buffett_verdict"),
        ("taleb", "taleb_verdict"),
        ("contrarian", "contrarian_verdict"),
    ]:
        fields = data[lens]
        lenses[lens] = {
            "fields": len(fields),
            "field_names": list(fields),
            "verdict": first_sentence(str(fields[verdict_key])),
            "action_signal": fields.get("action_signal"),
        }
    return {
        "ticker": ticker,
        "fiscal_year": year,
        "row_id": row_id,
        "filing_date": filed,
        "top_level_fields": list(data),
        "total_fields": sum(v["fields"] for v in lenses.values()) + 2,
        "lenses": lenses,
        "final_verdict_opening": (
            re.match(r"^(.*?Conviction:\s*\w+)", str(data["final_verdict"]), re.S)
            or re.match(r"^(\S+)", str(data["final_verdict"]))
        )[1],
        "moat_rating": first_sentence(str(data["buffett"]["moat_rating"])),
        "antifragile_rating": first_sentence(str(data["taleb"]["antifragile_rating"])),
    }


def batch_rhythm(con: sqlite3.Connection, name: str, result_type: str) -> dict[str, Any]:
    batch_id, created, completed, total, done, failed = con.execute(
        "SELECT batch_id, created_at, completed_at, total_tickers, completed_tickers, "
        "failed_tickers FROM batch_jobs WHERE name = ? AND status = 'completed'",
        (name,),
    ).fetchone()
    stamps = [
        datetime.fromisoformat(s)
        for (s,) in con.execute(
            "SELECT ar.created_at FROM analysis_results ar JOIN batch_items bi "
            "ON ar.run_id = bi.run_id WHERE bi.batch_id = ? AND ar.result_type = ? "
            "ORDER BY ar.created_at",
            (batch_id, result_type),
        )
    ]
    hourly = Counter(s.replace(minute=0, second=0).isoformat() for s in stamps)
    # Gemini free-tier quotas reset at midnight Pacific: 08:00 UTC in February.
    quota_days = Counter((s - timedelta(hours=8)).date().isoformat() for s in stamps)
    errors: Counter[str] = Counter()
    for (message,) in con.execute(
        "SELECT error_message FROM batch_items WHERE batch_id = ? AND status = 'failed'",
        (batch_id,),
    ):
        text = (message or "").lower()
        if "no 10-k filings" in text or "could not be downloaded" in text:
            errors["no filing retrieved"] += 1
        elif "ai analysis failed" in text:
            errors["model call failed"] += 1
        elif "context" in text:
            errors["context length"] += 1
        else:
            errors["other"] += 1
    return {
        "name": name,
        "created_at": created,
        "completed_at": completed,
        "companies": total,
        "companies_completed": done,
        "companies_failed": failed,
        "readings": len(stamps),
        "first_reading": stamps[0].isoformat(),
        "last_reading": stamps[-1].isoformat(),
        "hourly_utc": dict(sorted(hourly.items())),
        "per_quota_day": dict(sorted(quota_days.items())),
        "failure_categories": dict(errors),
    }


def archive() -> dict[str, Any]:
    con = connect(ARCHIVE)
    result = {
        "saved_workflows": con.execute("SELECT COUNT(*) FROM workflows").fetchone()[0],
        "workflow_runs": con.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0],
        "workflow_step_logs": con.execute("SELECT COUNT(*) FROM workflow_step_logs").fetchone()[
            0
        ],
        "runs_by_type": dict(
            con.execute("SELECT analysis_type, COUNT(*) FROM analysis_runs GROUP BY 1")
        ),
        "first_run": con.execute("SELECT MIN(created_at) FROM analysis_runs").fetchone()[0],
        "last_run": con.execute("SELECT MAX(created_at) FROM analysis_runs").fetchone()[0],
    }
    con.close()
    return result


def backtest() -> dict[str, Any]:
    results = json.loads((EVALUATION / "results.json").read_text())
    trades = pd.read_csv(EVALUATION / "trades.csv")
    config = json.loads((EVALUATION / "run.json").read_text())["config"]
    long_, short = config["long_verdicts"], config["short_verdicts"]
    trades["leg"] = trades["verdict"].map(
        lambda v: "long" if v in long_ else "short" if v in short else "hold"
    )
    post = trades[pd.to_datetime(trades["filing_date"]) > config["knowledge_cutoff"]]
    post_1y = post.dropna(subset=["excess_1Y"])
    windows = []
    for year, group in trades.groupby("fiscal_year"):
        entry = pd.to_datetime(group["entry_date"])
        windows.append(
            {
                "fiscal_year": int(year),
                "n": int(len(group)),
                "entry_p10": entry.quantile(0.1).date().isoformat(),
                "entry_median": entry.median().date().isoformat(),
                "entry_p90": entry.quantile(0.9).date().isoformat(),
            }
        )
    return {
        "source_sha256": sha256(EVALUATION / "results.json"),
        "trades_sha256": sha256(EVALUATION / "trades.csv"),
        "knowledge_cutoff": config["knowledge_cutoff"],
        "price_end": config["price_end"],
        "counts": results["counts"],
        "verdicts_by_vintage": results["verdicts_by_vintage"],
        "horizons": results["horizons"],
        "vintages": results["vintages"],
        "primary": results["primary"],
        "entry_windows": windows,
        "post_cutoff_1y": {
            leg: sorted(post_1y.loc[post_1y["leg"] == leg, "excess_1Y"].round(5).tolist())
            for leg in ("long", "short")
        },
        "post_cutoff_1y_top": post_1y.nlargest(3, "excess_1Y")[
            ["ticker", "verdict", "filing_date", "excess_1Y"]
        ].to_dict("records"),
    }


def origin() -> dict[str, Any]:
    """The 2025 origin project, read-only: reading counts by day, and the ledger test."""
    readings = sorted(ORIGIN.glob("analyzed_10k/*/*.json"))
    days = Counter(datetime.fromtimestamp(p.stat().st_mtime).date().isoformat() for p in readings)
    years = sorted({int(p.stem[:4]) for p in readings if p.stem[:4].isdigit()})
    stamps = Counter()
    for path in ORIGIN.glob("company_results/*.json"):
        stamps[str(json.loads(path.read_text()).get("analysis_date", ""))[:4]] += 1
    ledger = json.loads((EVALUATION / "origin-ledger/results.json").read_text())
    return {
        "root": str(ORIGIN),
        "model": "gemini-2.5-flash-preview-04-17",
        "filing_readings": len(readings),
        "companies_read": len({p.parent.name for p in readings}),
        "fiscal_years": [years[0], years[-1]],
        "readings_by_day": dict(sorted(days.items())),
        "excellent_factor_files": len(list(ORIGIN.glob("excellent_company_factors/*.json"))),
        "meta_analysis": {
            k: json.loads((ORIGIN / "top_50_meta_analysis.json").read_text())[k]
            for k in ("total_companies_analyzed", "analysis_date")
        },
        "self_reported_analysis_year": dict(stamps),
        "ledger_source_sha256": sha256(EVALUATION / "origin-ledger/results.json"),
        "ledger": ledger,
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    sources = [DB, ARCHIVE, EVALUATION / "results.json", EVALUATION / "trades.csv"]
    run: dict[str, Any] = {
        "stage": "whitepaper-figure-data",
        "timestamp": datetime.now(UTC).isoformat(),
        "versions": {"python": sys.version.split()[0], "pandas": pd.__version__},
        "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in sources + [Path(__file__)]},
    }
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    con = connect(DB)
    evidence = {
        "milestones": {k: {"commit": c, "date": git_date(c)} for k, c in MILESTONES.items()},
        "corpus": corpus(con),
        "specimen": specimen(con),
        "market_batch": batch_rhythm(con, MARKET_BATCH, "SimplifiedAnalysis"),
        "options_batch": batch_rhythm(con, OPTIONS_BATCH, "AsymmetricOptionsV4"),
        "archive": archive(),
        "backtest": backtest(),
        "origin": origin(),
        "february_report": {
            "source": "experimental/backtester/BACKTEST_REPORT.md",
            "kind": "reported",
            "date": "2026-02-12",
            "signals": 4689,
            "tickers": 515,
            "headline": {
                "1Y_alpha": 0.071,
                "1Y_p": 0.003,
                "2Y_alpha": 0.141,
                "2Y_p": 0.0008,
                "2Y_clustered_p": 0.041,
            },
        },
    }
    con.close()
    path = OUT / "evidence.json"
    path.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    run["outputs"] = {"evidence.json": sha256(path)}
    (OUT / "run.json").write_text(json.dumps(run, indent=2) + "\n")
    print(json.dumps({k: v for k, v in evidence["corpus"].items()}, indent=2))
    print(evidence["specimen"]["final_verdict_opening"])
    print(evidence["market_batch"]["per_quota_day"], evidence["market_batch"]["failure_categories"])
    print(evidence["milestones"])


if __name__ == "__main__":
    main()
