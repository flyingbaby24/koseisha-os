from __future__ import annotations

import csv
from pathlib import Path

from .models import Concept


DEFAULT_CONCEPTS_PATH = Path(__file__).with_name("source_of_thought_concepts.csv")


def load_concepts(path: str | Path = DEFAULT_CONCEPTS_PATH) -> list[Concept]:
    concept_path = Path(path)
    if not concept_path.exists():
        raise FileNotFoundError(f"Concept CSV not found: {concept_path}")

    concepts: list[Concept] = []
    with concept_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"Japanese", "English", "Category"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Concept CSV missing column(s): {', '.join(sorted(missing))}")

        for row in reader:
            label_ja = str(row.get("Japanese", "") or "").strip()
            label_en = str(row.get("English", "") or "").strip()
            category = str(row.get("Category", "") or "").strip()
            if label_ja and label_en:
                concepts.append(Concept(label_ja=label_ja, label_en=label_en, category=category))

    if not concepts:
        raise ValueError(f"Concept CSV has no usable rows: {concept_path}")
    return concepts

