"""Generate LaTeX from the canonical Markdown with matching figures and captions.

Requires Pandoc 3.x. Example:
  python docs/whitepaper/build_paper.py --pandoc /path/to/pandoc
Then run pdflatex twice, or tectonic, in docs/whitepaper/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
STEM = "eon-whitepaper"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandoc", default=shutil.which("pandoc"))
    args = parser.parse_args()
    if not args.pandoc:
        parser.error("Pandoc 3.x is required; install it or supply --pandoc PATH")
    source = (HERE / f"{STEM}.md").read_text()
    title, subtitle = source.splitlines()[0][2:], source.splitlines()[2][4:]
    author_match = re.search(r"^\*\*Author:\*\* (.+)$", source[: source.index("## Abstract")], re.M)
    if author_match is None:
        raise ValueError("The Markdown title block must include an Author line")
    body = source[source.index("## Abstract") :]
    body = re.sub(r"## Contents\n.*?(?=## 1\. The question)", "", body, flags=re.S)
    # Article body starts at section level; numbers are editorial text in both formats.
    body = re.sub(r"^#{2,}", lambda m: m.group()[1:], body, flags=re.M)
    # Literal code stays literal; TeX listings is configured to wrap long records.
    ast = json.loads(
        subprocess.run(
            [args.pandoc, "-f", "markdown-implicit_figures+smart", "-t", "json"],
            input=body,
            text=True,
            check=True,
            capture_output=True,
        ).stdout
    )
    blocks, out, figures = ast["blocks"], [], []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if block["t"] == "CodeBlock" and out and out[-1]["t"] == "Para":
            # A short lead-in belongs with its quotation or code example.
            lead = out.pop()
            opening = (
                r"\par\noindent\begin{minipage}{\linewidth}"
                if block["t"] == "CodeBlock"
                else r"\begin{samepage}"
            )
            closing = r"\end{minipage}\par" if block["t"] == "CodeBlock" else r"\end{samepage}"
            out.extend(
                [
                    {"t": "RawBlock", "c": ["latex", opening]},
                    lead,
                    block,
                    {"t": "RawBlock", "c": ["latex", closing]},
                ]
            )
            i += 1
            continue
        if block["t"] == "Table":
            # Pandoc's pipe-width guesses waste space on short identifier columns.
            # These are presentation widths only; all cells stay in source order.
            headers = json.dumps(block["c"][3])
            count = len(block["c"][2])
            if "Sample" in headers:
                widths = [0.19, 0.22, 0.35, 0.24]
            elif "Vintage" in headers:
                widths = [0.14, 0.24, 0.18, 0.18, 0.26]
            elif "Amendment" in headers:
                widths = [0.36, 0.40, 0.24]
            elif "Constraint" in headers:
                widths = [0.34, 0.66]
            elif "Path" in headers:
                widths = [0.55, 0.45]
            elif count == 4:
                widths = [0.52, 0.16, 0.16, 0.16]
            elif count == 3:
                widths = [0.50, 0.25, 0.25]
            else:
                widths = [0.62, 0.38]
            for spec, width in zip(block["c"][2], widths, strict=True):
                spec[1] = {"t": "ColWidth", "c": width}
        if block["t"] == "HorizontalRule":
            i += 1
            continue
        if block["t"] == "Para" and len(block["c"]) == 1 and block["c"][0]["t"] == "Image":
            image = block["c"][0]
            caption_block = blocks[i + 1]
            assert caption_block["t"] == "Para" and caption_block["c"][0]["t"] == "Emph"
            inlines = caption_block["c"][0]["c"]
            number = inlines[2]["c"].rstrip(".")
            assert inlines[0] == {"t": "Str", "c": "Figure"}
            assert int(number) == len(figures) + 1
            caption = {"t": "Plain", "c": inlines[4:]}
            original_path = image["c"][2][0]
            pdf_path = str(Path(original_path).with_suffix(".pdf"))
            if not (HERE / pdf_path).exists():
                raise FileNotFoundError(pdf_path)
            image["c"][2][0] = pdf_path
            image["c"][0][2] = [["width", "100%"]]
            label = "fig:" + Path(pdf_path).stem
            out.append(
                {
                    "t": "Figure",
                    "c": [[label, [], []], [None, [caption]], [{"t": "Plain", "c": [image]}]],
                }
            )
            figures.append({"number": int(number), "asset": pdf_path})
            i += 2
            continue
        out.append(block)
        i += 1
    assert len(figures) == 9
    ast["blocks"] = out
    result = subprocess.run(
        [
            args.pandoc,
            "-f",
            "json",
            "-t",
            "latex",
            "--top-level-division=section",
            "--listings",
            "--wrap=auto",
            "--columns=95",
        ],
        input=json.dumps(ast),
        text=True,
        check=True,
        capture_output=True,
    ).stdout
    # Support the older TeX Live bundle shipped by Tectonic as well as current TeX.
    result = result.replace(r"\def\LTcaptype{none}", r"\def\LTcaptype{table}")
    for symbol, command in {
        "\u00d7": r"\times",
        "\u2212": "-",
        "≥": r"\geq",
        "≈": r"\approx",
        "→": r"\rightarrow",
    }.items():
        result = result.replace(symbol, r"\ensuremath{" + command + "}")
    # Pandoc wraps long heading text. Normalize it before matching float boundaries.
    result = re.sub(
        r"(\\(?:sub)?section\{)([^{}]*)(\})",
        lambda m: m[1] + " ".join(m[2].split()) + m[3],
        result,
    )
    # Let prose fill the space before a large plate, but never leave its section.
    result = result.replace("\\begin{figure}", "\\begin{figure}[!htbp]")
    # Figures may drift past a heading onto the next page; flafter keeps them
    # after their first mention. Barriers only where a new part of the argument starts.
    for heading in ("7. The February backtest, and the problem of memory", "10. What the work taught me", "Appendix A: reproduction"):
        result = result.replace(r"\section{" + heading, r"\FloatBarrier" + "\n" + r"\section{" + heading)
    for heading in (
        "1. The question",
        "Appendix B: glossary",
        "Appendix C: figures at a glance",
    ):
        result = result.replace(
            r"\section{" + heading + "}", r"\clearpage" + "\n" + r"\section{" + heading + "}"
        )
    # Every table is short enough for one page. Keep its header and rows together.
    def compact_table(match: re.Match[str]) -> str:
        table = match[0].replace(r"\begin{longtable}[]", r"\begin{tabular}")
        table = table.replace(r"\endhead", "")
        table = table.replace("\\bottomrule\\noalign{}\n\\endlastfoot", "")
        table = table.replace(r"\end{longtable}", "\\bottomrule\\noalign{}\n\\end{tabular}")
        table = table.replace(
            r"\begin{minipage}[b]{\linewidth}\raggedright",
            r"\begin{minipage}[b]{\linewidth}\raggedright\bfseries",
        )
        table = re.sub(r"(\d[\d.,]*) (MB|GB|KB|ms)\b", r"\1~\2", table)
        return (
            "\\par\\addvspace{8pt}\\noindent\\begin{minipage}{\\linewidth}\\small\n"
            + table
            + "\n\\end{minipage}\\par\\addvspace{8pt}"
        )

    result = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}", compact_table, result, flags=re.S)
    # Keep the release identity and at-a-glance summary from splitting mid-record.
    result = re.sub(
        r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}",
        lambda m: "\\par\\noindent\\begin{minipage}{\\linewidth}\n"
        + m[0]
        + "\n\\end{minipage}\\par",
        result,
        flags=re.S,
    )
    # Let long monospaced paths in tables wrap at natural punctuation.
    result = re.sub(
        r"\\texttt\{([^{}]+)\}",
        lambda m: (
            m.group(0)
            if len(m[1]) < 32
            else "\\path{" + m[1].replace("\\_", "_").replace("\\-", "-") + "}"
        ),
        result,
    )
    header = (HERE / "paper-preamble.tex").read_text()
    header = header.replace("PAPER_AUTHOR", author_match[1])
    header = header.replace("PAPER_RUNNING_TITLE", title)
    header = header.replace("PAPER_TITLE", title.replace(", ", r",\\[.15em] ", 1)).replace(
        "PAPER_SUBTITLE", subtitle
    )
    generated = "% Generated by build_paper.py from " + STEM + ".md.\n"
    generated += "% Edit Markdown, then regenerate; do not edit this file independently.\n"
    generated += header + "\n" + result + "\n\\end{document}\n"
    (HERE / f"{STEM}.tex").write_text(generated)
    report: dict[str, Any] = {
        "markdown_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "latex_sha256": hashlib.sha256(generated.encode()).hexdigest(),
        "preamble_sha256": hashlib.sha256((HERE / "paper-preamble.tex").read_bytes()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "pandoc": subprocess.run(
            [args.pandoc, "--version"], text=True, capture_output=True, check=True
        ).stdout.splitlines()[0],
        "figures": figures,
        "editorial_source": f"{STEM}.md",
    }
    (HERE / "document-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Generated matching LaTeX with nine figures and all three appendices.")


if __name__ == "__main__":
    main()
