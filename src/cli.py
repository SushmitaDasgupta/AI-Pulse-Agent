"""Typer CLI entrypoint: `pulsator run` / `pulsator run --stage <id>`."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from src.agent.graph import run_graph
from src.config import STAGE_IDS, load_config

app = typer.Typer(
    name="pulsator",
    help=(
        "AI Review Pulsator — weekly ChatGPT Play Store review pulse. "
        "P1: acquire/normalize/scrub. P2: theme/select/compose/validate. "
        "P3: publish_docs/draft_email via Railway MCP. "
        "P4: schedule via GitHub Actions (or Railway cron) → pulsator run."
    ),
    add_completion=False,
)


class StageId(str, Enum):
    acquire = "acquire"
    normalize = "normalize"
    scrub = "scrub"
    theme = "theme"
    select = "select"
    compose = "compose"
    publish_docs = "publish_docs"
    draft_email = "draft_email"
    ingest = "ingest"  # acquire + normalize + scrub bundle
    pulse = "pulse"  # theme + select + compose + validate (offline on cleaned corpus)
    validate = "validate"
    publish = "publish"


@app.callback()
def main() -> None:
    """AI Review Pulsator CLI."""


@app.command("run")
def run(
    stage: Optional[StageId] = typer.Option(
        None,
        "--stage",
        help=(
            "Optional stage id. Pipeline: "
            + ", ".join(STAGE_IDS)
            + ". Bundles: ingest, pulse. Graph aliases: validate, publish."
        ),
    ),
    config: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        "-c",
        help="Path to config.yaml",
        exists=False,
        dir_okay=False,
    ),
    require_mcp: bool = typer.Option(
        False,
        "--require-mcp",
        help=(
            "Hard-fail if Google Doc append or Gmail draft fails "
            "(recommended for scheduled weekly runs). "
            "Also settable via REQUIRE_MCP=true."
        ),
    ),
) -> None:
    """Run the weekly pulse graph (P1 ingest + P2 theme/select/compose + P3 delivery)."""
    if require_mcp:
        os.environ["REQUIRE_MCP"] = "true"

    cfg = load_config(config)
    typer.echo(f"config loaded: app_id={cfg.app_id} acquire.mode={cfg.acquire.mode}")
    typer.echo(f"play_url: {cfg.play_url}")
    typer.echo(f"require_mcp: {cfg.langchain.require_mcp}")
    if cfg.acquire.mode == "file":
        fixture = cfg.fixture_path()
        typer.echo(f"file-mode source preference: {fixture} (exists={fixture.exists()})")
    if stage:
        typer.echo(f"stage filter: {stage.value}")

    result = run_graph(
        config_path=str(config),
        stage=stage.value if stage else None,
    )
    for message in result.get("messages") or []:
        typer.echo(f"  • {message}")
    skipped = result.get("skipped") or []
    if skipped:
        typer.echo(f"skipped nodes: {', '.join(skipped)}")
    if result.get("cleaned_path"):
        typer.echo(
            f"cleaned: {result['cleaned_path']} (reviews={result.get('review_count', 0)})"
        )
    if result.get("themes_path"):
        typer.echo(f"themes: {result['themes_path']}")
    if result.get("selection_path"):
        typer.echo(f"selection: {result['selection_path']}")
    if result.get("pulse_md_path"):
        typer.echo(f"pulse: {result['pulse_md_path']}")
    if result.get("doc_url"):
        typer.echo(f"doc: {result['doc_url']}")
    if result.get("email_draft_id"):
        typer.echo(f"email_draft: {result['email_draft_id']}")
    typer.echo("run complete (exit 0)")


@app.command("stages")
def stages() -> None:
    """List documented pipeline stage IDs."""
    typer.echo("Pipeline stage IDs:")
    for stage_id in STAGE_IDS:
        typer.echo(f"  - {stage_id}")
    typer.echo("Bundle: ingest (= acquire → normalize → scrub)")
    typer.echo(
        "Bundle: pulse (= theme → select → compose → validate) — uses cleaned corpus"
    )
    typer.echo(
        "Graph: acquire → normalize → scrub → theme → select → compose → validate → publish → draft_email"
    )
    typer.echo(
        "Scheduler (P4): GitHub Actions Weekly Pulse → pulsator run --require-mcp"
    )


if __name__ == "__main__":
    app()
