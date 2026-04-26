import logging
from datetime import datetime
from pathlib import Path


def _find_first(directory: Path, pattern: str):
    """Return the first file matching pattern in directory, or None."""
    matches = sorted(directory.glob(pattern))
    return matches[0] if matches else None


def collect_run_artifacts(output_dir: Path, use_case: str) -> dict:
    """Collect generated artifacts for one use-case run."""
    return {
        "use_case": use_case,
        "output_dir": output_dir,
        "csv": _find_first(output_dir, "memory_usage_*.csv"),
        "analysis": _find_first(output_dir, "memory_analysis_*.txt"),
        "stacked_plot": _find_first(output_dir, "memory_stacked_line_chart_*.png"),
        "total_plot": _find_first(output_dir, "memory_total_*.png"),
        "cpu_plot": _find_first(output_dir, "cpu_usage_*.png"),
        "app_info": output_dir / "app_info.txt",
    }


def _read_text_if_exists(path: Path | None) -> str:
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return "Not available."


def _render_path_for_html(report_file: Path, target_path: Path) -> str:
    return str(target_path.relative_to(report_file.parent)).replace("\\", "/")


def generate_batch_report(run_artifacts: list[dict], app_name_internal: str) -> Path:
    """Generate one HTML report that aggregates multiple use-case runs."""
    output_root = Path("output")
    output_root.mkdir(parents=True, exist_ok=True)
    batch_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_root / f"batch_report_{app_name_internal}_{batch_stamp}.html"

    cards = []
    for index, run in enumerate(run_artifacts, start=1):
        use_case = run["use_case"]
        pretty_name = use_case.replace("_", " ").title()

        cards.append("    <section class=\"run-card\">")
        cards.append(
            f"      <h2><span class=\"badge\">#{index}</span> {pretty_name} <small>({use_case})</small></h2>"
        )

        app_info = _read_text_if_exists(run.get("app_info"))
        analysis = _read_text_if_exists(run.get("analysis"))

        cards.append("      <div class=\"meta-grid\">")
        cards.append("        <article>")
        cards.append("          <h3>Run Info</h3>")
        cards.append(f"          <pre>{app_info}</pre>")
        cards.append("        </article>")
        cards.append("        <article>")
        cards.append("          <h3>Analysis</h3>")
        cards.append(f"          <pre>{analysis}</pre>")
        cards.append("        </article>")
        cards.append("      </div>")

        for title, artifact_key in [
            ("Memory Usage (Stacked)", "stacked_plot"),
            ("Total Memory", "total_plot"),
            ("CPU Usage", "cpu_plot"),
        ]:
            image_path = run.get(artifact_key)
            cards.append("      <article class=\"plot\">")
            cards.append(f"        <h3>{title}</h3>")
            if image_path and image_path.exists():
                relative = _render_path_for_html(report_file, image_path)
                cards.append(f"        <img src=\"{relative}\" alt=\"{title} for {use_case}\" loading=\"lazy\">")
            else:
                cards.append("        <p>Image not available.</p>")
            cards.append("      </article>")

        cards.append("    </section>")

    order = " -> ".join(run["use_case"] for run in run_artifacts)

    html = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        "  <title>Batch Memory Report</title>",
        "  <style>",
        "    :root { --bg: #f3f2ed; --card: #fffdf8; --ink: #1d2a30; --muted: #5a6970; --line: #d9ddd3; --accent: #0f6f65; --accent-2: #d97706; }",
        "    * { box-sizing: border-box; }",
        "    body { margin: 0; color: var(--ink); font-family: \"Segoe UI\", \"Helvetica Neue\", Helvetica, Arial, sans-serif; background: linear-gradient(165deg, #e8f0e2 0%, var(--bg) 40%, #f7efe1 100%); }",
        "    .wrap { max-width: 1220px; margin: 0 auto; padding: 24px; }",
        "    header { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px; margin-bottom: 16px; }",
        "    h1 { margin: 0 0 8px; font-size: 1.6rem; }",
        "    .meta { margin: 0; color: var(--muted); }",
        "    .run-card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px; margin-bottom: 16px; }",
        "    h2 { margin: 0 0 10px; color: var(--accent); }",
        "    h2 small { color: var(--muted); font-weight: normal; }",
        "    .badge { display: inline-flex; align-items: center; justify-content: center; min-width: 30px; height: 30px; border-radius: 99px; background: var(--accent-2); color: #fff; font-size: 0.9rem; margin-right: 8px; }",
        "    .meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; margin-bottom: 12px; }",
        "    article { background: #fff; border: 1px solid var(--line); border-radius: 10px; padding: 12px; }",
        "    h3 { margin: 0 0 8px; color: var(--accent); font-size: 1rem; }",
        "    pre { margin: 0; white-space: pre-wrap; word-break: break-word; background: #fbfcfa; border: 1px solid var(--line); border-radius: 8px; padding: 10px; font-size: 0.92rem; line-height: 1.45; }",
        "    .plot { margin-top: 12px; }",
        "    img { width: 100%; height: auto; border: 1px solid var(--line); border-radius: 8px; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <main class=\"wrap\">",
        "    <header>",
        "      <h1>Android Memory Monitor Batch Report</h1>",
        f"      <p class=\"meta\"><strong>Application:</strong> {app_name_internal}</p>",
        f"      <p class=\"meta\"><strong>Use-case order:</strong> {order}</p>",
        f"      <p class=\"meta\"><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
        "    </header>",
    ]

    html.extend(cards)
    html.extend([
        "  </main>",
        "</body>",
        "</html>",
    ])

    report_file.write_text("\n".join(html) + "\n", encoding="utf-8")
    logging.info(f"Batch report generated: {report_file}")
    return report_file
