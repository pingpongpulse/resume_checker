"""Scoring module for candidate-role fit in a talent intelligence hackathon."""

from pprint import pprint

from dummy_data import (
    CANDIDATE_PROFILES,
    HIDDEN_TALENT,
    JOB_DESC,
    PERFECT_MATCH,
    WEAK_MATCH,
)


USING_MODEL_SIMILARITY = True

try:
    # Person 1 integration: use the real semantic similarity model.
    from talent_core.person1.utils import skill_similarity
except Exception:
    USING_MODEL_SIMILARITY = False

    # Fallback mock keeps Person 2 workflows unblocked if model assets are unavailable.
    def skill_similarity(a, b):
        import random

        random.seed(hash(a + b) % 100)
        return round(random.uniform(0.3, 0.95), 2)


MATCH_THRESHOLD = 0.6


def _normalize(values):
    return [str(value).strip().lower() for value in values if str(value).strip()]


def _lexical_similarity(a, b):
    """Simple lexical proxy to avoid random high scores on unrelated skills."""
    if a == b:
        return 1.0

    a_tokens = set(a.replace("-", "_").split("_"))
    b_tokens = set(b.replace("-", "_").split("_"))
    token_union = a_tokens.union(b_tokens)
    token_jaccard = (len(a_tokens.intersection(b_tokens)) / len(token_union)) if token_union else 0.0

    # Character-level overlap helps for near variants like "rest_api" and "restapi".
    a_chars = set(a)
    b_chars = set(b)
    char_union = a_chars.union(b_chars)
    char_jaccard = (len(a_chars.intersection(b_chars)) / len(char_union)) if char_union else 0.0

    return max(token_jaccard, char_jaccard)


def _combined_similarity(a, b):
    """Exact matches get 1.0; non-exact pairs use deterministic semantic+lexical similarity."""
    if a == b:
        return 1.0
    model_score = skill_similarity(a, b)
    lexical_score = _lexical_similarity(a, b)
    if lexical_score < 0.4:
        return round(model_score * 0.55, 2)
    return round((0.7 * model_score) + (0.3 * lexical_score), 2)


def _best_similarity(target_skill, candidate_skills):
    """Return best cosine-like similarity for a required skill."""
    if not candidate_skills:
        return 0.0
    return max(_combined_similarity(target_skill, cand_skill) for cand_skill in candidate_skills)


def _match_skills(required_skills, candidate_skills):
    matched_skills = []
    missing_skills = []
    top_matched_skills = []
    skill_scores = {}

    for req_skill in required_skills:
        best_score = _best_similarity(req_skill, candidate_skills)
        skill_scores[req_skill] = round(best_score, 3)
        if best_score >= MATCH_THRESHOLD:
            matched_skills.append(req_skill)
            top_matched_skills.append((req_skill, round(best_score, 2)))
        else:
            missing_skills.append(req_skill)

    bonus_skills = []
    for cand_skill in candidate_skills:
        best_against_required = _best_similarity(cand_skill, required_skills)
        if best_against_required < MATCH_THRESHOLD:
            bonus_skills.append(cand_skill)

    top_matched_skills = sorted(top_matched_skills, key=lambda item: item[1], reverse=True)
    return matched_skills, missing_skills, bonus_skills, top_matched_skills, skill_scores


def _compute_skill_score(matched_skills, required_skills):
    if not required_skills:
        return 0
    score = (len(matched_skills) / len(required_skills)) * 100
    return int(round(score))


def _compute_project_score(projects, required_skills):
    if not projects or not required_skills:
        return 0

    overlap_by_project = []
    req_set = set(required_skills)
    covered_required_skills = set()
    strong_project_count = 0

    for project in projects:
        tech = _normalize(project.get("tech", []))
        if not tech:
            overlap_by_project.append(0.0)
            continue
        matched_in_project = req_set.intersection(tech)
        covered_required_skills.update(matched_in_project)
        if len(matched_in_project) >= 5:
            strong_project_count += 1

        # Focus ratio rewards projects where tech is actually relevant to the JD.
        focus_ratio = len(matched_in_project) / len(tech)
        overlap_by_project.append(focus_ratio)

    avg_focus = sum(overlap_by_project) / len(overlap_by_project)
    coverage_ratio = len(covered_required_skills) / len(required_skills)
    strong_project_ratio = strong_project_count / len(projects)

    # Balance breadth (coverage), focus (relevant tech), and depth (strong projects).
    score = (
        (0.5 * coverage_ratio)
        + (0.2 * avg_focus)
        + (0.3 * strong_project_ratio)
    ) * 100
    return min(100, int(round(score)))


def _compute_github_score(github_data, required_skills):
    raw_score = 0
    repo_count = int(github_data.get("repo_count", 0) or 0)
    has_deployed = bool(github_data.get("has_deployed", False))
    languages = _normalize(github_data.get("languages", []))

    if repo_count >= 5:
        raw_score += 30
    if repo_count >= 10:
        raw_score += 30
    if has_deployed:
        raw_score += 20

    required_language_matches = len(set(languages).intersection(required_skills))
    if required_language_matches > 0:
        raw_score += 20

    # Normalize by activity and language breadth so high scores can differ by profile.
    activity_norm = min(repo_count / 20, 1.0)
    deploy_norm = 1.0 if has_deployed else 0.0
    language_norm = min(required_language_matches / 3, 1.0)
    quality_norm = (0.5 * activity_norm) + (0.3 * deploy_norm) + (0.2 * language_norm)

    normalized_score = int(round(raw_score * quality_norm))
    return min(100, normalized_score)


def _compute_education_score(education_data):
    degree = str(education_data.get("degree", "")).lower()

    if "computer science" in degree or "software engineering" in degree:
        return 100
    if "information technology" in degree or "electronics" in degree:
        return 70
    return 40


def _build_why_high(
    skill_score,
    project_score,
    github_score,
    education_score,
    matched_skills,
    required_skills,
    candidate_profile,
    github_matched_skills,
):
    messages = []

    messages.append(
        f"{len(matched_skills)}/{len(required_skills)} required skills matched "
        f"at threshold >= {MATCH_THRESHOLD}."
    )

    if github_matched_skills:
        preview = ", ".join(github_matched_skills[:5])
        messages.append(
            f"GitHub reveals {len(github_matched_skills)} hidden skills: {preview}"
        )

    if github_score >= 70:
        repo_count = int(candidate_profile.get("github", {}).get("repo_count", 0) or 0)
        has_deployed = bool(candidate_profile.get("github", {}).get("has_deployed", False))
        deploy_text = "with deployed apps" if has_deployed else "without deployment evidence"
        messages.append(
            f"GitHub score is high from normalized activity signals: {repo_count} repos {deploy_text}."
        )
    elif project_score >= 60:
        messages.append("Projects show good overlap with the required backend stack.")

    if project_score >= 60 and github_score >= 70:
        messages.append("Both project evidence and GitHub signals support practical backend execution.")
    if education_score >= 100:
        messages.append("Degree is directly aligned with core software/backend fundamentals.")
    elif education_score >= 70:
        messages.append("Education is reasonably aligned with technical role expectations.")

    if len(messages) < 2:
        messages.append("Candidate has baseline technical indicators that can be strengthened for this role.")
    if len(messages) < 2:
        messages.append("Some relevant experience signals support potential role fit.")

    return messages[:3]


def _build_why_low(skill_score, project_score, github_score, education_score, missing_skills):
    messages = []

    if skill_score < 60:
        missing_preview = ", ".join(missing_skills[:3]) if missing_skills else "multiple core skills"
        messages.append(f"Missing skills include: {missing_preview}.")
    if project_score < 40:
        messages.append("Project tech overlap with required stack is low.")
    if github_score < 50:
        messages.append("GitHub signals are limited (few repos/deployments/language matches).")
    if education_score <= 40:
        messages.append("Education background is less directly related to backend engineering.")
    if not messages and missing_skills:
        messages.append("A few role-critical gaps could slow onboarding.")

    if len(messages) < 2:
        messages.append("Current profile depth may be below the target seniority expectations.")
    if len(messages) < 2:
        messages.append("Evidence of production-grade backend work could be stronger.")

    return messages[:3]


def _build_suggestions(missing_skills, github_score, project_score):
    suggestions = []

    for skill in missing_skills[:2]:
        suggestions.append(f"Learn {skill} - it is required for this role.")

    if github_score < 50:
        suggestions.append("Publish more GitHub repositories and include at least one deployed backend app.")
    elif project_score < 50:
        suggestions.append("Build one end-to-end backend project covering API, database, and deployment.")

    if len(suggestions) < 2:
        suggestions.append("Add measurable impact and architecture details to project descriptions.")
    if len(suggestions) < 2:
        suggestions.append("Practice system design for scalable APIs and document trade-offs in projects.")

    return suggestions[:3]


def compute_fit_score(candidate_profile, job_description):
    """Compute candidate-role fit score and explainability output."""
    required_skills = _normalize(job_description.get("required_skills", []))
    resume_skills = _normalize(candidate_profile.get("skills", []))
    github_languages = _normalize(candidate_profile.get("github", {}).get("languages", []))
    effective_skills = list(dict.fromkeys(resume_skills + github_languages))

    matched_skills, missing_skills, bonus_skills, top_matched_skills, skill_scores = _match_skills(
        required_skills,
        effective_skills,
    )

    resume_skill_set = set(resume_skills)
    github_matched_skills = [skill for skill in matched_skills if skill not in resume_skill_set]

    skill_score = _compute_skill_score(matched_skills, required_skills)
    project_score = _compute_project_score(candidate_profile.get("projects", []), required_skills)
    github_score = _compute_github_score(candidate_profile.get("github", {}), required_skills)
    education_score = _compute_education_score(candidate_profile.get("education", {}))

    fit_score = int(
        round(
            0.4 * skill_score
            + 0.3 * project_score
            + 0.2 * github_score
            + 0.1 * education_score
        )
    )

    why_high = _build_why_high(
        skill_score,
        project_score,
        github_score,
        education_score,
        matched_skills,
        required_skills,
        candidate_profile,
        github_matched_skills,
    )
    why_low = _build_why_low(
        skill_score,
        project_score,
        github_score,
        education_score,
        missing_skills,
    )
    suggestions = _build_suggestions(missing_skills, github_score, project_score)

    match_result = {
        "fit_score": int(fit_score),
        "breakdown": {
            "skill_score": int(skill_score),
            "project_score": int(project_score),
            "github_score": int(github_score),
            "education_score": int(education_score),
        },
        "matched_skills": matched_skills,
        "github_matched_skills": github_matched_skills,
        "top_matched_skills": top_matched_skills,
        "skill_scores": skill_scores,
        "missing_skills": missing_skills,
        "bonus_skills": bonus_skills,
        "why_high": why_high,
        "why_low": why_low,
        "suggestions": suggestions,
    }
    return match_result


def test_all_scenarios():
    """Run sanity checks on all benchmark candidate scenarios."""
    scenarios = [PERFECT_MATCH, WEAK_MATCH, HIDDEN_TALENT]
    results = []

    for candidate in scenarios:
        result = compute_fit_score(candidate, JOB_DESC)
        results.append(
            {
                "name": candidate.get("name", "Unknown"),
                "result": result,
            }
        )

    print("\nSCENARIO SUMMARY")
    print("-" * 86)
    similarity_source = "Person 1 Word2Vec model" if USING_MODEL_SIMILARITY else "mock fallback"
    print(f"Similarity source: {similarity_source}")
    print("Similarity note: exact skill matches are 1.0; non-exact skill pairs use semantic+lexical blending.")
    print(
        f"{'candidate name':<20} | {'fit_score':<9} | {'matched count':<13} | "
        f"{'missing count':<13} | {'github_score':<12}"
    )
    print("-" * 86)
    for item in results:
        result = item["result"]
        print(
            f"{item['name']:<20} | "
            f"{result['fit_score']:<9} | "
            f"{len(result['matched_skills']):<13} | "
            f"{len(result['missing_skills']):<13} | "
            f"{result['breakdown']['github_score']:<12}"
        )
    print("-" * 86)

    print("Top matched skills (with similarity):")
    for item in results:
        top3 = item["result"].get("top_matched_skills", [])[:3]
        print(f"- {item['name']}: {top3}")

    sorted_candidates = sorted(results, key=lambda x: x["result"]["fit_score"], reverse=True)
    print("\nRanked candidates:")
    for rank, item in enumerate(sorted_candidates, start=1):
        print(f"{rank}. {item['name']} ({item['result']['fit_score']})")

    checks = [
        (
            "PERFECT_MATCH fit_score > 80",
            results[0]["result"]["fit_score"] > 80,
        ),
        (
            "WEAK_MATCH fit_score < 50",
            results[1]["result"]["fit_score"] < 50,
        ),
        (
            "HIDDEN_TALENT github_score > 60",
            results[2]["result"]["breakdown"]["github_score"] > 60,
        ),
    ]

    edge_case_candidate = {
        "name": "No Skill Candidate",
        "skills": [],
        "projects": [],
        "experience": [],
        "education": {"degree": "B.A. History", "university": "Sample University"},
        "github": {"repo_count": 0, "languages": [], "has_deployed": False},
    }
    edge_result = compute_fit_score(edge_case_candidate, JOB_DESC)
    checks.append(
        (
            "EDGE_CASE empty skills does not crash",
            isinstance(edge_result.get("fit_score"), int),
        ),
    )

    for label, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {label}")

    assert checks[0][1], "PERFECT_MATCH fit_score should be > 80"
    assert checks[1][1], "WEAK_MATCH fit_score should be < 50"
    assert checks[2][1], "HIDDEN_TALENT github_score should be > 60"
    assert checks[3][1], "Empty-skills edge case should produce a valid result"


if __name__ == "__main__":
    for candidate in CANDIDATE_PROFILES:
        print(f"\n=== {candidate.get('name', 'Unknown Candidate')} ===")
        result = compute_fit_score(candidate, JOB_DESC)
        pprint(result, sort_dicts=False)

    test_all_scenarios()

    random_candidate = {
        "name": "Test User",
        "skills": ["cooking", "drawing"],
        "projects": [],
        "experience": [],
        "education": {"degree": "History", "university": "XYZ"},
        "github": {"repo_count": 0, "languages": [], "has_deployed": False}
    }

    print("\n=== RANDOM TEST ===")
    result = compute_fit_score(random_candidate, JOB_DESC)
    pprint(result, sort_dicts=False)
