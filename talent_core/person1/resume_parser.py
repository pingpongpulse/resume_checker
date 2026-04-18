"""Resume parsing utilities for Person 1.

Parses resume text into the required candidate_profile structure.
"""

from __future__ import annotations

import re
from typing import Dict, List

import spacy


SECTION_PATTERN = re.compile(
    r"\b(SKILLS?|TECHNICAL SKILLS|EDUCATION|EXPERIENCE|WORK EXPERIENCE|PROJECTS?)\b",
    flags=re.IGNORECASE,
)

SKILL_KEYWORDS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "c++",
    "sql",
    "fastapi",
    "flask",
    "django",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "postgresql",
    "mysql",
    "redis",
    "git",
    "ci_cd",
    "rest_api",
    "pandas",
    "numpy",
    "react",
    "vue",
    "node",
}

DEGREE_HINTS = [
    "b.tech",
    "b.e",
    "bachelor",
    "m.tech",
    "m.s",
    "master",
    "phd",
    "computer science",
    "information technology",
    "software engineering",
]

ROLE_HINTS = [
    "engineer",
    "developer",
    "intern",
    "analyst",
    "scientist",
    "consultant",
    "manager",
]

URL_PATTERN = re.compile(
    r"((?:https?://)?(?:www\.)?(?:github\.com|linkedin\.com/in)/[A-Za-z0-9._%+-/]+)",
    flags=re.IGNORECASE,
)


try:
    NLP = spacy.load("en_core_web_sm")
except OSError:
    NLP = None


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip(".,;)")
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _extract_profile_links(text: str) -> Dict[str, str]:
    """Extract GitHub/LinkedIn profile links from resume text."""
    links: Dict[str, str] = {}
    for raw in URL_PATTERN.findall(text):
        url = _normalize_url(raw)
        lower = url.lower()
        if "github.com/" in lower and "github" not in links:
            links["github"] = url
        elif "linkedin.com/in/" in lower and "linkedin" not in links:
            links["linkedin"] = url
    return links


def split_sections(text: str) -> Dict[str, str]:
    """Split resume text into coarse sections based on common headers."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    sections: Dict[str, List[str]] = {
        "skills": [],
        "education": [],
        "experience": [],
        "projects": [],
    }

    current = None
    for line in lines:
        match = SECTION_PATTERN.search(line)
        if match:
            header = match.group(1).lower()
            if "skill" in header:
                current = "skills"
            elif "education" in header:
                current = "education"
            elif "experience" in header:
                current = "experience"
            elif "project" in header:
                current = "projects"
            continue

        if current in sections:
            sections[current].append(line)

    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _extract_name(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if NLP is not None:
        doc = NLP("\n".join(lines[:8]))
        for ent in doc.ents:
            if ent.label_ == "PERSON" and len(ent.text.split()) <= 4:
                return _normalize_space(ent.text)

    for line in lines[:5]:
        if "@" not in line and len(line.split()) in (2, 3):
            return _normalize_space(line)

    return "Unknown"


def _extract_skills(skills_text: str, full_text: str) -> List[str]:
    source = f"{skills_text}\n{full_text}".lower()
    found = sorted({skill for skill in SKILL_KEYWORDS if skill in source})

    if found:
        return found

    tokens = re.split(r"[,/|\n]", skills_text.lower())
    return sorted({tok.strip() for tok in tokens if tok.strip()})


def _extract_projects(projects_text: str) -> List[Dict[str, List[str]]]:
    projects: List[Dict[str, List[str]]] = []
    if not projects_text:
        return projects

    chunks = [chunk.strip("-• ") for chunk in projects_text.splitlines() if chunk.strip()]
    for chunk in chunks[:6]:
        parts = re.split(r"[:|-]", chunk, maxsplit=1)
        name = _normalize_space(parts[0])
        tech_text = parts[1] if len(parts) > 1 else ""

        tech = [
            tok.strip().lower()
            for tok in re.split(r"[,/|]", tech_text)
            if tok.strip()
        ]
        if not tech:
            tech = [skill for skill in SKILL_KEYWORDS if skill in chunk.lower()]

        projects.append({"name": name or "Untitled Project", "tech": sorted(set(tech))})

    return projects


def _extract_experience(experience_text: str) -> List[Dict[str, object]]:
    experience: List[Dict[str, object]] = []
    if not experience_text:
        return experience

    lines = [ln.strip("-• ") for ln in experience_text.splitlines() if ln.strip()]
    for line in lines[:8]:
        years_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)", line, flags=re.I)
        years = float(years_match.group(1)) if years_match else 0.0

        segments = [seg.strip() for seg in re.split(r"[-|,]", line) if seg.strip()]
        company = segments[0] if segments else "Unknown Company"

        role = "Unknown Role"
        for seg in segments[1:] + segments[:1]:
            if any(hint in seg.lower() for hint in ROLE_HINTS):
                role = seg
                break

        experience.append({"company": company, "role": role, "years": years})

    return experience


def _extract_education(education_text: str, full_text: str) -> Dict[str, str]:
    degree = "Unknown Degree"
    university = "Unknown University"

    lines = [ln.strip("-• ") for ln in education_text.splitlines() if ln.strip()]
    if not lines:
        lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()][:20]

    for line in lines:
        low = line.lower()
        if any(hint in low for hint in DEGREE_HINTS):
            degree = line
            break

    if NLP is not None:
        doc = NLP("\n".join(lines[:10]))
        for ent in doc.ents:
            if ent.label_ == "ORG" and "university" in ent.text.lower() or "institute" in ent.text.lower():
                university = _normalize_space(ent.text)
                break

    if university == "Unknown University":
        for line in lines:
            low = line.lower()
            if "university" in low or "institute" in low or "college" in low:
                university = _normalize_space(line)
                break

    return {"degree": degree, "university": university}


def parse_resume_text(text: str) -> Dict[str, object]:
    """Parse raw resume text and return required candidate_profile dict."""
    sections = split_sections(text)

    candidate_profile = {
        "name": _extract_name(text),
        "skills": _extract_skills(sections.get("skills", ""), text),
        "projects": _extract_projects(sections.get("projects", "")),
        "experience": _extract_experience(sections.get("experience", "")),
        "education": _extract_education(sections.get("education", ""), text),
        "links": _extract_profile_links(text),
    }
    return candidate_profile


def parse_resume(text: str) -> Dict[str, object]:
    """Backward-compatible alias used by integration tests."""
    return parse_resume_text(text)


if __name__ == "__main__":
    dummy_resume = """
    Aarav Menon
    SKILLS
    Python, FastAPI, Docker, PostgreSQL, AWS, Git
    EXPERIENCE
    BlueOrbit Systems - Senior Backend Engineer - 4.5 years
    PROJECTS
    Order API: Python, FastAPI, PostgreSQL, Docker
    EDUCATION
    B.Tech in Computer Science
    National Institute of Technology Trichy
    github.com/aarav-menon
    linkedin.com/in/aarav-menon
    """

    print(parse_resume_text(dummy_resume))
