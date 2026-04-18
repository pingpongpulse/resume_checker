"""End-to-end integration pipeline for Person 1 + Person 2 + Person 3.

- Person 1: resume parsing + semantic skill similarity
- Person 2: fit scoring and explainability
- Person 3: interactive graph rendering
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pdfplumber

from dummy_data import JOB_DESC, PERFECT_MATCH, WEAK_MATCH, HIDDEN_TALENT
from graph_builder import render_match_graph
from github_scraper import extract_github_username, get_github_data
from portfolio_scraper import scrape_portfolio_text
from scorer import compute_fit_score
from talent_core.person1.resume_parser import parse_resume_text

JOB_DEF = JOB_DESC

DEMO_CANDIDATES = [
    ("perfect", PERFECT_MATCH),
    ("weak", WEAK_MATCH),
    ("hidden", HIDDEN_TALENT),
]


def _merge_evidence_skills(candidate_profile: dict[str, Any]) -> dict[str, Any]:
    """Merge resume skills with GitHub language evidence into a deduplicated skill list.

    Project tech extracted from PDFs can contain noisy free-text fragments and numbers,
    so we intentionally avoid promoting project strings into the core skill list used by
    scoring and graph nodes.
    """
    merged = {str(skill).strip().lower() for skill in candidate_profile.get("skills", []) if str(skill).strip()}

    github = candidate_profile.get("github", {})
    for language in github.get("languages", []):
        normalized = str(language).strip().lower()
        if normalized:
            merged.add(normalized)

    candidate_profile["skills"] = sorted(merged)
    return candidate_profile

def extract_text_from_pdf(pdf_path: Path) -> str:
    full_text = ""
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text


def build_candidate_from_resume(pdf_path: Path) -> dict[str, Any]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"Resume not found: {pdf_path}")

    full_text = extract_text_from_pdf(pdf_path)
    candidate_profile = parse_resume_text(full_text)

    github_link = candidate_profile.get("links", {}).get("github")
    if github_link:
        username = extract_github_username(github_link)
        github_data = get_github_data(username, JOB_DEF["required_skills"])
        candidate_profile["github"] = github_data

        candidate_profile = _merge_evidence_skills(candidate_profile)
    else:
        candidate_profile["github"] = {"repo_count": 0, "languages": [], "has_deployed": False}

    portfolio_link = candidate_profile.get("links", {}).get("portfolio")
    if portfolio_link:
        candidate_profile["portfolio_text"] = scrape_portfolio_text(portfolio_link)
    else:
        candidate_profile["portfolio_text"] = ""

    candidate_profile = _merge_evidence_skills(candidate_profile)
    return candidate_profile


def run_pipeline(pdf_path: Path, output_dir: str = "graph_output") -> dict[str, Any]:
    candidate = build_candidate_from_resume(pdf_path)
    match_result = compute_fit_score(candidate, JOB_DEF)

    output_file, analytics = render_match_graph(
        match_result,
        candidate_name=candidate.get("name", "candidate").replace(" ", "_"),
        job_title=JOB_DEF["title"],
        output_dir=output_dir,
    )

    return {
        "candidate_profile": candidate,
        "match_result": match_result,
        "graph_file": output_file,
        "graph_analytics": analytics,
    }


def run_demo_pipeline(output_dir: str = "graph_output") -> list[dict[str, Any]]:
    """Run the standard 3-scenario demo and return structured results."""
    results: list[dict[str, Any]] = []

    for scenario_type, candidate in DEMO_CANDIDATES:
        enriched_candidate = _merge_evidence_skills(dict(candidate))
        match_result = compute_fit_score(enriched_candidate, JOB_DEF)
        output_file, analytics = render_match_graph(
            match_result,
            candidate_name=enriched_candidate.get("name", "candidate").replace(" ", "_"),
            job_title=JOB_DEF["title"],
            output_dir=output_dir,
            scenario_type=scenario_type,
        )
        results.append(
            {
                "scenario": scenario_type,
                "candidate_name": enriched_candidate.get("name", "candidate"),
                "match_result": match_result,
                "graph_file": output_file,
                "graph_analytics": analytics,
            }
        )

    return results


def main() -> None:
    print("Running demo pipeline for perfect, weak, and hidden candidates...\n")
    results = run_demo_pipeline(output_dir="graph_output")

    for item in results:
        score = item["match_result"].get("fit_score", 0)
        print(f"[{item['scenario'].upper()}] {item['candidate_name']} -> fit_score: {score}")
        print(json.dumps(item["match_result"], indent=2))
        print(f"Graph file: {item['graph_file']}")
        print(f"Graph analytics: {json.dumps(item['graph_analytics'], indent=2)}")
        print("-" * 80)

    # Optional extra run: try an available local PDF resume if present.
    project_root = Path(__file__).resolve().parent
    known_resumes = [
        project_root / "P_Sai_Lekhya_Resume_compressed (1).pdf",
        project_root / "P_Sai_Lekhya_Resume - Google Docs.pdf",
    ]
    for pdf_path in known_resumes:
        if not pdf_path.exists():
            continue
        print(f"\nRunning optional resume pipeline on: {pdf_path.name}")
        result = run_pipeline(pdf_path)
        print(json.dumps(result["match_result"], indent=2))
        print(f"Graph file: {result['graph_file']}")
        print(f"Graph analytics: {json.dumps(result['graph_analytics'], indent=2)}")
        break


if __name__ == "__main__":
    main()
