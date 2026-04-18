"""Word2Vec similarity utilities for Person 2 and Person 3 consumption."""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Tuple

import numpy as np
from gensim.models import Word2Vec


_MODEL = None

_SKILL_ALIASES = {
    "java script": "javascript",
    "java_script": "javascript",
    "js": "javascript",
    "node.js": "nodejs",
    "express.js": "express",
    "djan go": "django",
    "dj ango": "django",
    "k8s": "kubernetes",
    "node js": "nodejs",
    "node_js": "nodejs",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "tf": "tensorflow",
    "tensor flow": "tensorflow",
    "keras": "tensorflow",
    "sklearn": "sklearn",
    "scikit learn": "sklearn",
    "scikit_learn": "sklearn",
    "scikitlearn": "sklearn",
    "scikit-learn": "sklearn",
    "sci kit learn": "sklearn",
    "ml": "machine learning",
    "machinelearning": "machine learning",
    "machine learnign": "machine learning",
    "machine learing": "machine learning",
    "dl": "deep learning",
    "deeplearning": "deep learning",
    "deep learing": "deep learning",
    "deeep learning": "deep learning",
    "cnn": "convolutional neural network",
    "convolutional neural networks": "convolutional neural network",
    "convalutional neural networks": "convolutional neural network",
    "convalution neural network": "convolutional neural network",
    "rnn": "recurrent neural network",
    "dl model": "deep learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "cv": "computer vision",
    ".net": "dotnet",
    "c#": "csharp",
}


def _alias_key_primary(text: str) -> str:
    """Primary alias key preserving meaningful symbols and word boundaries."""
    text = text.lower().strip()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _alias_key_compact(text: str) -> str:
    """Compact alias key for forgiving punctuation/spacing variations."""
    return re.sub(r"[^a-z0-9]+", "", _alias_key_primary(text))


_ALIAS_LOOKUP_PRIMARY = {
    _alias_key_primary(alias): canonical for alias, canonical in _SKILL_ALIASES.items()
}
_ALIAS_LOOKUP_COMPACT = {
    _alias_key_compact(alias): canonical for alias, canonical in _SKILL_ALIASES.items()
}

_RELATED_SKILL_GROUPS = [
    {"python", "flask", "django", "fastapi", "sqlalchemy", "pytest"},
    {"javascript", "typescript", "react", "vue", "nodejs", "express", "html", "css"},
    {"docker", "kubernetes", "ci_cd", "terraform", "devops"},
    {"postgresql", "mysql", "redis", "sql", "mongodb"},
    {"aws", "gcp", "azure", "cloud"},
    {"csharp", "dotnet"},
    {
        "machine learning",
        "deep learning",
        "tensorflow",
        "pytorch",
        "sklearn",
        "convolutional neural network",
        "recurrent neural network",
        "neural network",
        "data engineering",
        "python",
        "artificial intelligence",
        "natural language processing",
        "computer vision",
        "data science",
    },
]


def _model_path() -> Path:
    local_path = Path(__file__).resolve().parent / "models" / "skill_w2v.model"
    if local_path.exists():
        return local_path

    legacy_path = Path(__file__).resolve().parents[2] / "talent_ai" / "person1" / "models" / "skill_w2v.model"
    return legacy_path


def load_model(force_reload: bool = False) -> Word2Vec:
    """Load and cache the trained Word2Vec model."""
    global _MODEL
    if _MODEL is None or force_reload:
        path = _model_path()
        if not path.exists():
            raise FileNotFoundError(
                f"Model not found at {path}. Train it first with word2vec_trainer.py"
            )
        _MODEL = Word2Vec.load(str(path))
    return _MODEL


def _normalize_skill_text(skill: str) -> str:
    original = str(skill)
    text = _alias_key_primary(original)

    # Resolve aliases with primary key first, compact fallback second.
    aliased = _ALIAS_LOOKUP_PRIMARY.get(text)
    if aliased is None:
        aliased = _ALIAS_LOOKUP_COMPACT.get(_alias_key_compact(original), text)

    # Canonical output should also be space-normalized.
    aliased = re.sub(r"[-_/]+", " ", aliased)
    aliased = re.sub(r"[^a-z0-9\s]+", " ", aliased)
    aliased = re.sub(r"\s+", " ", aliased).strip()
    return aliased


def _tokenize_skill(skill: str) -> List[str]:
    normalized = _normalize_skill_text(skill)
    return [tok for tok in re.split(r"[^a-z0-9]+", normalized) if tok]


def _lexical_similarity(skill_a: str, skill_b: str) -> float:
    a = _normalize_skill_text(skill_a)
    b = _normalize_skill_text(skill_b)
    if a == b:
        return 1.0

    a_tokens = set(_tokenize_skill(a))
    b_tokens = set(_tokenize_skill(b))
    token_union = a_tokens.union(b_tokens)
    token_score = (len(a_tokens.intersection(b_tokens)) / len(token_union)) if token_union else 0.0

    a_chars = set(a.replace(" ", ""))
    b_chars = set(b.replace(" ", ""))
    char_union = a_chars.union(b_chars)
    char_score = (len(a_chars.intersection(b_chars)) / len(char_union)) if char_union else 0.0
    return max(token_score, char_score)


def _same_related_group(skill_a: str, skill_b: str) -> bool:
    a = _normalize_skill_text(skill_a)
    b = _normalize_skill_text(skill_b)
    for group in _RELATED_SKILL_GROUPS:
        if a in group and b in group:
            return True
    return False


def get_skill_vector(skill: str) -> np.ndarray:
    """Return embedding vector for a single or multi-token skill phrase."""
    model = load_model()
    normalized = _normalize_skill_text(skill)
    if normalized in model.wv.key_to_index:
        return np.array(model.wv[normalized])

    compact = normalized.replace(" ", "")
    if compact in model.wv.key_to_index:
        return np.array(model.wv[compact])

    tokens = _tokenize_skill(normalized)
    vectors = [model.wv[token] for token in tokens if token in model.wv.key_to_index]

    if not vectors:
        return np.zeros(model.vector_size, dtype=float)
    return np.mean(vectors, axis=0)


def skill_similarity(skill_a: str, skill_b: str) -> float:
    """Cosine similarity in [0, 1] for two skill strings."""
    if _normalize_skill_text(skill_a) == _normalize_skill_text(skill_b):
        return 1.0

    vec_a = get_skill_vector(skill_a)
    vec_b = get_skill_vector(skill_b)

    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        if _same_related_group(skill_a, skill_b):
            return 0.72
        return 0.0

    cosine = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
    # Convert [-1, 1] cosine range to [0, 1] as required by downstream scoring.
    score = (cosine + 1.0) / 2.0

    # Keep same-stack skills reasonably high even if lexical overlap is low.
    if _same_related_group(skill_a, skill_b):
        score = max(score, 0.72)

    # Penalize semantically noisy similarities when lexical overlap is weak
    # and they are not from the same skill family.
    lexical = _lexical_similarity(skill_a, skill_b)
    if not _same_related_group(skill_a, skill_b) and lexical < 0.2:
        score *= 0.35
    elif not _same_related_group(skill_a, skill_b) and lexical < 0.4:
        score *= 0.7

    return round(max(0.0, min(1.0, score)), 4)


def most_similar_skills(skill: str, topn: int = 5) -> List[Tuple[str, float]]:
    """Return most similar skills from vocabulary."""
    model = load_model()
    normalized = _normalize_skill_text(skill)

    if normalized in model.wv.key_to_index:
        return [(word, round(score, 4)) for word, score in model.wv.most_similar(normalized, topn=topn)]

    compact = normalized.replace(" ", "")
    if compact in model.wv.key_to_index:
        return [(word, round(score, 4)) for word, score in model.wv.most_similar(compact, topn=topn)]

    tokens = _tokenize_skill(normalized)

    for token in tokens:
        if token in model.wv.key_to_index:
            return [(word, round(score, 4)) for word, score in model.wv.most_similar(token, topn=topn)]

    # Fallback for OOV phrases: compare against first N vocabulary tokens.
    candidates = list(model.wv.key_to_index.keys())[:5000]
    scored = [(cand, skill_similarity(skill, cand)) for cand in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:topn]


if __name__ == "__main__":
    dummy_candidate = {
        "name": "Demo Candidate",
        "skills": ["python", "fastapi", "docker"],
    }
    print("Dummy candidate:", dummy_candidate)
    try:
        print("Similarity python vs python:", skill_similarity("python", "python"))
        print("Most similar to react:", most_similar_skills("react", topn=5))
    except FileNotFoundError as exc:
        print(exc)
