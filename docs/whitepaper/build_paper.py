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
    body = re.sub(r"## Contents\n.*?(?=## 1\. )", "", body, flags=re.S)
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
    blocks, out, figures, illustrations = ast["blocks"], [], [], []
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
            if "Answers" in headers:
                widths = [0.22, 0.2, 0.11, 0.47]
            elif "Sample" in headers:
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
                widths = [0.34, 0.12, 0.12, 0.42]
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
            if "illustration" in image["c"][0][1]:
                original_path = image["c"][2][0]
                asset = HERE / original_path
                if not asset.exists():
                    raise FileNotFoundError(asset)
                attrs = dict(image["c"][0][2])
                width = float(attrs.get("width", "100%").rstrip("%")) / 100
                # Keep the Part II synthesis on its page after Latin Modern reflow.
                if original_path.endswith("art-spot-compass.png"):
                    width = 0.30
                caption_block = blocks[i + 1]
                assert caption_block["t"] == "Para"
                caption_tex = subprocess.run(
                    [args.pandoc, "-f", "json", "-t", "latex"],
                    input=json.dumps({**ast, "blocks": [caption_block]}), text=True,
                    check=True, capture_output=True).stdout.strip()
                alt = " ".join(x.get("c", "") for x in image["c"][1] if x["t"] == "Str")
                latex = (r"\par\addvspace{7pt}\noindent\begin{minipage}{\linewidth}\centering" + "\n"
                         + rf"\includegraphics[width={width:.2f}\linewidth]{{{original_path}}}" + "\n"
                         + r"\par\vspace{4pt}{\footnotesize\raggedright " + caption_tex + r"\par}" + "\n"
                         + r"\end{minipage}\par\addvspace{7pt}")
                out.append({"t": "RawBlock", "c": ["latex", latex]})
                illustrations.append({"asset": original_path, "alt": alt,
                                      "sha256": hashlib.sha256(asset.read_bytes()).hexdigest()})
                i += 2
                continue
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
    assert len(figures) == 17
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
        "≤": r"\leq",
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
    result = result.replace("\\begin{figure}", "\\begin{figure}[H]")
    # Keep evidence adjacent to its argument. Only the three large opener
    # figures may float over following prose, within a bounded section.
    for stem in ("02-lineage", "05-execution", "06-quota-clock", "07-database", "08-catalogue", "10-before-after", "11-verdict-ladder", "16-shortcomings", "17-sealed-bet"):
        result = re.sub(
            r"\\begin\{figure\}\[H\].*?\\end\{figure\}",
            lambda m: m[0].replace("[H]", "[!htbp]", 1) if "fig:" + stem in m[0] else m[0],
            result, flags=re.S,
        )
    for heading in ("3. From scripts to a processor", "8. Was it right?"):
        result = result.replace(r"\section{" + heading, r"\FloatBarrier" + "\n" + r"\section{" + heading)
    for heading in ("Part I · Building the reader", "Part II · What it read", "Part III · What it taught", "Appendix A: Methods"):
        result = result.replace(r"\section{" + heading, r"\FloatBarrier" + "\n" + r"\section{" + heading)
    for heading in (
        "Part I · Building the reader",
        "Part II · What it read",
        "Part III · What it taught",
        "Appendix A: Methods",
    ):
        result = result.replace(
            r"\section{" + heading + "}", r"\clearpage" + "\n" + r"\section{" + heading + "}"
        )
    for heading in ("8.3 Outlier sensitivity and company-level outcomes", "8.4 A ledger written in 2025", "8.5 A ledger written in February 2026"):
        result = result.replace(r"\subsection{" + heading, r"\FloatBarrier" + "\n" + r"\subsection{" + heading)
    # Keep the conclusion and its small closing illustration together.
    result = result.replace(r"\section{12. Conclusion}", r"\FloatBarrier\begin{minipage}{\linewidth}\setlength{\parskip}{5pt}" + "\n" + r"\section{12. Conclusion}")
    result = result.replace("\\clearpage\n\\section{Appendix A: Methods}", "\\end{minipage}\n\\clearpage\n\\section{Appendix A: Methods}")
    for heading in ("Part I · Building the reader", "Part II · What it read", "Part III · What it taught"):
        result = result.replace(r"\section{" + heading + "}", r"\section*{" + heading + "}" + "\n" + r"\addcontentsline{toc}{part}{" + heading + "}")
    # Every table is short enough for one page. Keep its header and rows together.
    def compact_table(match: re.Match[str]) -> str:
        original = match[0]
        cap = re.search(r"\\caption\{(.*?)\}\\tabularnewline", original, re.S)
        caption = ""
        if cap:
            caption = r"\captionof{table}{" + cap[1] + "}\n"
            original = original[:cap.start()] + original[cap.end():]
        original = re.sub(r"\\toprule.*?\\endfirsthead", "", original, count=1, flags=re.S)
        table = original.replace(r"\begin{longtable}[]", r"\begin{tabular}")
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
            + caption + table
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
            r"\mbox{" + m.group(0) + "}"
            if len(m[1]) < 32
            else "\\path{" + m[1].replace("\\_", "_").replace("\\-", "-") + "}"
        ),
        result,
    )
    # Listings' inline form breaks identifiers at hyphens; keep short names
    # whole and give long repository paths explicit break opportunities.
    result = re.sub(
        r"\\passthrough\{\\lstinline!([^!]*)!\}",
        lambda m: r"\mbox{\small\texttt{" + m[1] + "}}" if len(m[1]) < 32
        else r"\path{" + m[1].replace(r"\_", "_") + "}", result,
    )
    # Make every prose reference navigate to its numbered evidence figure.
    labels = {str(f["number"]): "fig:" + Path(f["asset"]).stem for f in figures}
    result = re.sub(r"\bFigure\s+(\d+)\b", lambda m: rf"\hyperref[{labels[m[1]]}]{{Figure~{m[1]}}}", result)
    figure_titles = {
        f["number"]: Path(f["asset"]).stem[3:].replace("-", " ").capitalize()
        for f in figures
    }
    counter = iter(range(1,18))
    result = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", lambda m: m[0].replace(r"\caption{", r"\caption[" + figure_titles[next(counter)] + "]{", 1), result, flags=re.S)
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
        "illustrations": illustrations,
        "cover": {"asset": "figures/art/art-cover.png", "sha256": hashlib.sha256((HERE / "figures/art/art-cover.png").read_bytes()).hexdigest()},
        "editorial_source": f"{STEM}.md",
    }
    (HERE / "document-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Generated LaTeX with {len(figures)} figures, {len(illustrations)} illustrations and an illustrated cover.")


if __name__ == "__main__":
    main()
