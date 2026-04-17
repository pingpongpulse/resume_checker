"""Dummy candidate and job data for a talent intelligence hackathon project."""

# Backend Engineer role definition used by all sample candidates.
JOB_DESC = {
    "title": "Backend Engineer",
    "required_skills": [
        "python",
        "fastapi",
        "docker",
        "postgresql",
        "kubernetes",
        "redis",
        "aws",
        "git",
        "rest_api",
        "ci_cd",
    ],
    "preferred_skills": [
        "microservices",
        "terraform",
        "prometheus",
        "graphql",
    ],
    "experience_years": 5,
    "education_required": "Bachelor's in Computer Science or related field",
}

# 9/10 required skill match, strong relevant experience, and deployed GitHub work.
PERFECT_MATCH = {
    "name": "Aarav Menon",
    "skills": [
        "python",
        "fastapi",
        "docker",
        "postgresql",
        "kubernetes",
        "redis",
        "aws",
        "git",
        "rest_api",
        "linux",
    ],
    "projects": [
        {
            "name": "Scalable Order Service (deployed)",
            "tech": ["python", "fastapi", "docker", "postgresql", "aws"],
        },
        {
            "name": "Realtime Notifications API (deployed)",
            "tech": ["python", "fastapi", "redis", "kubernetes"],
        },
        {
            "name": "CI/CD Deployment Pipeline (deployed)",
            "tech": ["git", "docker", "aws", "ci_cd"],
        },
    ],
    "experience": [
        {
            "company": "BlueOrbit Systems",
            "role": "Senior Python Developer",
            "years": 4.5,
        },
        {
            "company": "CloudNerve Labs",
            "role": "Backend Engineer",
            "years": 3.0,
        },
    ],
    "education": {
        "degree": "B.Tech in Computer Science",
        "university": "National Institute of Technology, Trichy",
    },
    "github": {
        "repo_count": 18,
        "languages": ["Python", "Go", "Shell"],
        "has_deployed": True,
    },
}

# 3/10 required skill match and no GitHub footprint.
WEAK_MATCH = {
    "name": "Riya Sharma",
    "skills": [
        "python",
        "git",
        "rest_api",
        "html",
        "css",
        "javascript",
    ],
    "projects": [
        {
            "name": "Campus Event Portal",
            "tech": ["javascript", "html", "css"],
        },
        {
            "name": "Simple Flask CRUD App",
            "tech": ["python", "sqlite"],
        },
    ],
    "experience": [
        {
            "company": "Internship - EduSoft",
            "role": "Software Intern",
            "years": 0.5,
        }
    ],
    "education": {
        "degree": "B.E. in Information Technology",
        "university": "Pune Institute of Engineering",
    },
    "github": {
        "repo_count": 0,
        "languages": [],
        "has_deployed": False,
    },
}

# "Money shot" profile: resume appears weak, but GitHub activity is strong.
HIDDEN_TALENT = {
    "name": "Karan Iqbal",
    "skills": [
        "python",
        "git",
        "sql",
        "linux",
        "problem_solving",
    ],
    "projects": [
        {
            "name": "Serverless Todo API (deployed)",
            "tech": ["python", "fastapi", "aws", "rest_api"],
        },
        {
            "name": "Containerized Metrics Service (deployed)",
            "tech": ["python", "docker", "redis", "ci_cd"],
        },
        {
            "name": "K8s Job Queue Worker (deployed)",
            "tech": ["python", "kubernetes", "postgresql", "git"],
        },
        {
            "name": "Data Sync Utility",
            "tech": ["python", "postgresql"],
        },
    ],
    "experience": [
        {
            "company": "Freelance",
            "role": "Independent Developer",
            "years": 1.5,
        }
    ],
    "education": {
        "degree": "B.Sc. in Mathematics",
        "university": "Delhi University",
    },
    "github": {
        "repo_count": 12,
        "languages": ["Python", "Dockerfile", "Shell", "YAML"],
        "has_deployed": True,
    },
}

# Optional convenience collection for iteration in experiments.
CANDIDATE_PROFILES = [PERFECT_MATCH, WEAK_MATCH, HIDDEN_TALENT]
