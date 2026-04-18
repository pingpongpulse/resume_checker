"""Person 2 module: GitHub profile/repository enrichment and scoring."""

from __future__ import annotations

import base64
import re
import time
from typing import Any

import requests

BASE_URL = "https://api.github.com/users/"


def extract_github_username(raw_link: str) -> str:
    match = re.search(r"github\.com/([A-Za-z0-9_.\-]+)", raw_link, re.I)
    return match.group(1) if match else raw_link.strip("/")


def _get_readme(username: str, repo: str) -> str:
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/readme"
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return ""
        data = res.json()
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
        return content[:2000]
    except Exception:
        return ""


def compute_github_score(repo_count: int, total_stars: int, active_repos: int) -> int:
    """Return normalized GitHub score in [0, 100]."""
    repo_signal = min(repo_count / 20.0, 1.0)
    activity_signal = min(active_repos / 15.0, 1.0)
    stars_signal = min(total_stars / 200.0, 1.0)

    score = (0.4 * repo_signal) + (0.3 * activity_signal) + (0.3 * stars_signal)
    return int(round(score * 100))


def get_github_data(username: str, required_skills: list[str]) -> dict[str, Any]:
    """Fetch GitHub activity/languages and produce Person 2 output payload."""
    try:
        repos_url = BASE_URL + username + "/repos?per_page=30&sort=updated"
        repos_res = requests.get(repos_url, timeout=10)
        repos = repos_res.json() if repos_res.status_code == 200 else []

        if not isinstance(repos, list):
            return {
                "repo_count": 0,
                "languages": [],
                "has_deployed": False,
                "github_repos": [],
                "github_score": 0,
            }

        req_set = {s.lower() for s in required_skills}
        languages: dict[str, int] = {}
        github_repos: list[dict[str, Any]] = []
        repo_count = 0
        total_stars = 0
        active_repos = 0
        has_deployed = False

        for repo in repos:
            if not isinstance(repo, dict) or "name" not in repo:
                continue

            repo_count += 1
            stars = int(repo.get("stargazers_count", 0) or 0)
            total_stars += stars
            if not repo.get("archived", False):
                active_repos += 1

            repo_name = str(repo["name"])
            homepage = str(repo.get("homepage") or "").strip()
            if homepage:
                has_deployed = True

            lang_url = repo.get("languages_url")
            repo_langs: list[str] = []
            if lang_url:
                lang_res = requests.get(lang_url, timeout=10)
                if lang_res.status_code == 200:
                    for lang, count in lang_res.json().items():
                        low = str(lang).lower()
                        repo_langs.append(low)
                        languages[low] = languages.get(low, 0) + int(count)

            readme = _get_readme(username, repo_name).lower()
            if any(token in readme for token in ["vercel", "render.com", "netlify", "docker", "kubernetes"]):
                has_deployed = True

            github_repos.append(
                {
                    "name": repo_name,
                    "stars": stars,
                    "languages": sorted(set(repo_langs)),
                }
            )
            time.sleep(0.1)

        top_languages = [lang for lang, _ in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:8]]
        prioritized = [l for l in top_languages if l in req_set]
        remaining = [l for l in top_languages if l not in req_set]

        return {
            "repo_count": repo_count,
            "languages": prioritized + remaining,
            "has_deployed": has_deployed,
            "github_repos": github_repos,
            "github_score": compute_github_score(repo_count, total_stars, active_repos),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"GitHub fetch error: {exc}")
        return {
            "repo_count": 0,
            "languages": [],
            "has_deployed": False,
            "github_repos": [],
            "github_score": 0,
        }
