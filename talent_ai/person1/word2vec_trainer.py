"""Train skip-gram Word2Vec from resume + job description corpora."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable, List

import pandas as pd
from gensim.models import Word2Vec
from gensim.parsing.preprocessing import STOPWORDS


TEXT_COLUMN_HINTS = [
    "resume",
    "job",
    "description",
    "skills",
    "text",
    "summary",
    "profile",
]


SKILL_CO_OCCURRENCE_PHRASES = [
    "python flask django fastapi rest_api backend api",
    "python flask django web application backend development",
    "python flask sqlalchemy postgres redis docker",
    "django flask python microservice api testing pytest",
    "javascript react vue nodejs frontend web",
    "docker kubernetes ci_cd devops deployment cloud",
    "aws kubernetes docker terraform cloud infrastructure",
    "postgresql mysql database sql backend data",
    "python machine learning deep learning tensorflow pytorch sklearn",
    "python scikit learn sklearn pandas numpy machine learning",
    "tensorflow keras deep learning neural network cnn rnn lstm",
    "convolutional neural network cnn computer vision deep learning",
    "natural language processing nlp transformers bert deep learning",
    "ml machine learning model training evaluation feature engineering",
    "dl deep learning tensorflow pytorch gpu neural network",
]


def _clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9_\s]", " ", text)
    tokens = [tok for tok in text.split() if tok not in STOPWORDS and len(tok) > 1]
    return " ".join(tokens)


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    return [s.strip() for s in re.split(r"[.!?;]\s+", text) if s.strip()]


def _pick_text_columns(df: pd.DataFrame) -> List[str]:
    all_cols = [str(col) for col in df.columns]

    # Prefer semantically named columns first, regardless of dtype.
    hinted = [
        col for col in all_cols if any(hint in col.lower() for hint in TEXT_COLUMN_HINTS)
    ]
    if hinted:
        return hinted

    # Fallback: include columns that appear to contain textual values.
    text_like: List[str] = []
    for col in all_cols:
        series = df[col]
        if str(series.dtype) in ("object", "string"):
            text_like.append(col)
            continue

        non_null = series.dropna()
        if non_null.empty:
            continue

        sample = str(non_null.iloc[0])
        if any(ch.isalpha() for ch in sample):
            text_like.append(col)

    return text_like or all_cols


def build_corpus_from_data(data_dir: str | Path, corpus_path: str | Path) -> List[List[str]]:
    """Load all CSV files, clean/tokenize text, and write corpus.txt."""
    data_dir = Path(data_dir)
    corpus_path = Path(corpus_path)
    corpus_path.parent.mkdir(parents=True, exist_ok=True)

    sentences_tokens: List[List[str]] = []
    corpus_lines: List[str] = []

    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    for csv_path in csv_files:
        df = pd.read_csv(csv_path, low_memory=False)
        text_columns = _pick_text_columns(df)
        if not text_columns:
            continue

        for _, row in df.iterrows():
            combined_text = " ".join(str(row[col]) for col in text_columns if pd.notna(row[col]))
            cleaned = _clean_text(combined_text)
            for sentence in _split_sentences(cleaned):
                tokens = sentence.split()
                if tokens:
                    sentences_tokens.append(tokens)
                    corpus_lines.append(" ".join(tokens))

    # Augment with curated tech co-occurrence phrases to stabilize semantic neighborhoods.
    for phrase in SKILL_CO_OCCURRENCE_PHRASES:
        tokens = phrase.split()
        for _ in range(40):
            sentences_tokens.append(tokens)
            corpus_lines.append(" ".join(tokens))

    corpus_path.write_text("\n".join(corpus_lines), encoding="utf-8")
    return sentences_tokens


def train_word2vec(
    tokenized_sentences: Iterable[List[str]],
    model_path: str | Path,
    vector_size: int = 100,
    window: int = 5,
    min_count: int = 2,
    epochs: int = 10,
) -> Word2Vec:
    """Train skip-gram Word2Vec and save the model."""
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    sentences = list(tokenized_sentences)
    if not sentences:
        raise ValueError("Tokenized corpus is empty. Check CSV column mapping and text cleaning.")

    model = Word2Vec(
        sentences=sentences,
        sg=1,
        vector_size=vector_size,
        window=window,
        min_count=min_count,
        workers=1,
        seed=42,
        epochs=epochs,
    )
    model.save(str(model_path))
    return model


def main() -> None:
    root = Path(__file__).resolve().parent
    data_dir = root / "data"
    models_dir = root / "models"
    corpus_path = data_dir / "corpus.txt"
    model_path = models_dir / "skill_w2v.model"

    tokenized = build_corpus_from_data(data_dir, corpus_path)
    model = train_word2vec(tokenized, model_path)

    for pair in [("python", "python"), ("react", "vue")]:
        a, b = pair
        if a in model.wv.key_to_index and b in model.wv.key_to_index:
            print(f"similarity({a}, {b}) = {model.wv.similarity(a, b):.4f}")
        else:
            print(f"similarity({a}, {b}) = N/A (token missing)")


if __name__ == "__main__":
    main()
