"""Theme chain: Groq classifies reviews; Gemini writes theme descriptions."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from src.agent.catalog import CATALOG, CATALOG_BY_ID, PAIN_THEME_IDS, classify_review
from src.agent.corpus import CorpusStats, corpus_stats, load_cleaned, stratified_sample
from src.agent.llm import get_classify_model, get_generate_model
from src.agent.schemas import DateWindow, ThemeRecord, ThemesResult
from src.config import AppConfig
from src.ingest.models import CanonicalReview, CleanedExport


def assign_themes_keyword(reviews: list[CanonicalReview]) -> dict[str, str]:
    """Deterministic catalog baseline (used when Groq is offline / for unlabeled rows)."""
    return {r.review_id: classify_review(r.text) for r in reviews}


# Back-compat alias used by select_chain
assign_themes = assign_themes_keyword


def _complaint_score(reviews: list[CanonicalReview]) -> float:
    if not reviews:
        return 0.0
    return sum((6 - r.rating) for r in reviews) / len(reviews) * len(reviews)


def build_themes_result(
    export: CleanedExport,
    assignments: dict[str, str],
    *,
    stats: CorpusStats | None = None,
) -> ThemesResult:
    stats = stats or corpus_stats(export)
    by_theme: dict[str, list[CanonicalReview]] = defaultdict(list)
    for review in export.reviews:
        tid = assignments.get(review.review_id, "t_praise")
        by_theme[tid].append(review)

    total = max(len(export.reviews), 1)
    themes: list[ThemeRecord] = []
    for catalog in CATALOG:
        rows = by_theme.get(catalog.theme_id, [])
        if not rows:
            continue
        avg = sum(r.rating for r in rows) / len(rows)
        examples = sorted(rows, key=lambda r: (r.rating, -len(r.text.split())))[:5]
        themes.append(
            ThemeRecord(
                theme_id=catalog.theme_id,
                label=catalog.label,
                description=catalog.description,
                review_count=len(rows),
                share=round(len(rows) / total, 4),
                avg_rating=round(avg, 2),
                example_ids=[r.review_id for r in examples],
            )
        )

    themes.sort(key=lambda t: (0 if t.theme_id in PAIN_THEME_IDS else 1, -t.review_count))
    if len(themes) > 5:
        themes = [t for t in themes if t.theme_id in PAIN_THEME_IDS][:5]

    window = DateWindow(
        start=stats.date_min or (export.window.start if export.window else ""),
        end=stats.date_max or (export.window.end if export.window else ""),
    )
    return ThemesResult(
        app_id=export.app_id,
        window=window,
        generated_at=datetime.now(timezone.utc),
        themes=themes,
    )


def rank_pain_themes(
    themes: ThemesResult,
    assignments: dict[str, str],
    reviews: list[CanonicalReview],
) -> list[ThemeRecord]:
    """Complaint-weighted ranking for pulse Top 3 (excludes pure praise)."""
    by_id = {r.review_id: r for r in reviews}
    scored: list[tuple[float, ThemeRecord]] = []
    for theme in themes.themes:
        if theme.theme_id not in PAIN_THEME_IDS:
            continue
        members = [
            by_id[i]
            for i, tid in assignments.items()
            if tid == theme.theme_id and i in by_id
        ]
        scored.append((_complaint_score(members), theme))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored]


def _parse_classify_lines(text: str) -> dict[str, str]:
    allowed = set(CATALOG_BY_ID)
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip().strip("`")
        if not line or line.lower().startswith("review"):
            continue
        if "\t" in line:
            rid, tid = line.split("\t", 1)
        elif "|" in line:
            rid, tid = line.split("|", 1)
        elif ":" in line:
            rid, tid = line.split(":", 1)
        else:
            parts = line.split()
            if len(parts) < 2:
                continue
            rid, tid = parts[0], parts[-1]
        rid = rid.strip().strip("\"'")
        tid = tid.strip().strip("\"'")
        if tid in allowed and rid:
            out[rid] = tid
    return out


def classify_with_groq(
    cfg: AppConfig,
    reviews: list[CanonicalReview],
) -> dict[str, str]:
    """
    Label a stratified sample with Groq into catalog theme_ids.

    Falls back to {} if Groq / key / package is unavailable.
    """
    model = get_classify_model(cfg)
    if model is None or not reviews:
        return {}

    prompt_path = cfg.resolve(cfg.paths.prompts_dir) / "classify_batch.txt"
    system = (
        prompt_path.read_text(encoding="utf-8")
        if prompt_path.exists()
        else "Classify each review_id into one theme_id. Output review_id<TAB>theme_id"
    )
    batch_size = max(int(cfg.langchain.classify_batch_size or 20), 1)
    assignments: dict[str, str] = {}

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError:
        return {}

    for i in range(0, len(reviews), batch_size):
        batch = reviews[i : i + batch_size]
        lines = []
        for review in batch:
            snippet = " ".join(review.text.split()[:40])
            lines.append(f"{review.review_id}\t[{review.rating}★] {snippet}")
        try:
            msg = model.invoke(
                [
                    SystemMessage(content=system),
                    HumanMessage(
                        content="Classify these reviews:\n" + "\n".join(lines)
                    ),
                ]
            )
            content = getattr(msg, "content", "") or ""
            if isinstance(content, list):
                # Gemini-style content blocks
                content = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                )
            parsed = _parse_classify_lines(str(content))
            assignments.update(parsed)
        except Exception:
            # Keep going; keyword baseline remains for failures.
            continue
    return assignments


def run_theme_chain(
    cfg: AppConfig,
    *,
    sample_size: int | None = None,
) -> tuple[ThemesResult, dict[str, str], CorpusStats]:
    """
    Label cleaned corpus into ≤5 catalog themes.

    1. Keyword baseline on full corpus (accurate N for offline / unlabelled rows)
    2. Groq re-labels a stratified sample (classification LLM)
    3. Gemini enriches theme descriptions (generation LLM)
    """
    export = load_cleaned(cfg)
    stats = corpus_stats(export)
    assignments = assign_themes_keyword(export.reviews)

    n_sample = sample_size or int(cfg.langchain.classify_sample_size or 900)
    sample = stratified_sample(export.reviews, size=min(n_sample, len(export.reviews)))
    groq_labels = classify_with_groq(cfg, sample)
    if groq_labels:
        assignments.update(groq_labels)

    result = build_themes_result(export, assignments, stats=stats)
    result = _gemini_enrich_descriptions(cfg, result, sample, assignments)
    return result, assignments, stats


def _gemini_enrich_descriptions(
    cfg: AppConfig,
    themes: ThemesResult,
    sample: list[CanonicalReview],
    assignments: dict[str, str],
) -> ThemesResult:
    model = get_generate_model(cfg)
    if model is None:
        return themes

    prompt_path = cfg.resolve(cfg.paths.prompts_dir) / "theme_enrich.txt"
    if not prompt_path.exists():
        return themes

    evidence: dict[str, list[str]] = defaultdict(list)
    for review in sample:
        tid = assignments.get(review.review_id)
        if not tid or tid not in PAIN_THEME_IDS:
            continue
        if len(evidence[tid]) >= 8:
            continue
        if review.rating > 3:
            continue
        evidence[tid].append(f"[{review.rating}★] {review.text[:180]}")

    snippets = []
    for theme in themes.themes:
        if theme.theme_id not in evidence:
            continue
        snippets.append(
            f"## {theme.label} ({theme.theme_id})\n" + "\n".join(evidence[theme.theme_id])
        )
    if not snippets:
        return themes

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        msg = model.invoke(
            [
                SystemMessage(content=prompt_path.read_text(encoding="utf-8")),
                HumanMessage(content="\n\n".join(snippets)),
            ]
        )
        text = getattr(msg, "content", "") or ""
        if isinstance(text, list):
            text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in text
            )
        updates: dict[str, str] = {}
        for line in str(text).splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()
            if key in CATALOG_BY_ID and val:
                updates[key] = val[:240]
        if not updates:
            return themes
        new_themes = [
            theme.model_copy(update={"description": updates[theme.theme_id]})
            if theme.theme_id in updates
            else theme
            for theme in themes.themes
        ]
        return themes.model_copy(update={"themes": new_themes})
    except Exception:
        return themes


def write_themes(cfg: AppConfig, result: ThemesResult, path: Path | None = None) -> Path:
    out = path or cfg.resolve(cfg.paths.themes)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return out


def load_themes(cfg: AppConfig, path: Path | None = None) -> ThemesResult:
    out = path or cfg.resolve(cfg.paths.themes)
    return ThemesResult.model_validate_json(out.read_text(encoding="utf-8"))
