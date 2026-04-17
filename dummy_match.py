"""Hardcoded match_result dicts for graph_builder.py testing.

Person 2 will eventually replace this with real scorer output.
"""

dummy_perfect = {
    "fit_score": 91,
    "breakdown": {
        "skill_score": 95,
        "project_score": 88,
        "github_score": 90,
        "education_score": 100,
    },
    "matched_skills": [
        "python",
        "fastapi",
        "postgresql",
        "docker",
        "kubernetes",
        "aws",
        "redis",
    ],
    "missing_skills": ["pytest"],
    "bonus_skills": ["rust", "graphql", "kafka"],
    "why_high": [
        "Strong Python backend with 4 deployed projects",
        "Docker + K8s matches role exactly",
        "GitHub shows active open source contributions",
    ],
    "why_low": ["No pytest/unit testing evidence found"],
    "suggestions": [
        "Add pytest tests to existing GitHub projects",
        "Get AWS Certified Developer badge",
    ],
}

dummy_weak = {
    "fit_score": 34,
    "breakdown": {
        "skill_score": 20,
        "project_score": 15,
        "github_score": 10,
        "education_score": 40,
    },
    "matched_skills": ["python"],
    "missing_skills": ["fastapi", "postgresql", "docker", "kubernetes"],
    "bonus_skills": ["html", "css"],
    "why_high": ["Has basic Python knowledge"],
    "why_low": [
        "No backend framework experience",
        "No database skills",
        "No deployment or DevOps knowledge",
    ],
    "suggestions": [
        "Learn FastAPI via official docs",
        "Complete PostgreSQL beginner course",
        "Deploy one project using Docker",
    ],
}

dummy_hidden = {
    "fit_score": 76,
    "breakdown": {
        "skill_score": 55,
        "project_score": 80,
        "github_score": 95,
        "education_score": 70,
    },
    "matched_skills": ["python", "fastapi", "postgresql"],
    "missing_skills": ["docker", "kubernetes"],
    "bonus_skills": ["flask", "mysql", "redis"],
    "why_high": [
        "GitHub shows 3 deployed FastAPI apps",
        "12 repos with consistent Python activity",
        "Project work covers 80% of required stack",
    ],
    "why_low": [
        "Resume undersells actual GitHub work",
        "No Docker/K8s on resume or GitHub",
    ],
    "suggestions": [
        "Add Docker to existing deployed projects",
        "Update resume to highlight deployed GitHub apps",
    ],
}

job_title = "Backend Engineer"
