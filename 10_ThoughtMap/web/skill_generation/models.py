from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Concept:
    label_ja: str
    label_en: str
    category: str
    similarity: float = 0.0
    rank: int = 0

    @property
    def key(self) -> str:
        return self.label_en.strip().lower().replace(" ", "_")


@dataclass(frozen=True)
class Condition:
    condition_type: str
    parameter: str = ""
    operator: str = ""
    value: float = 0.0


@dataclass(frozen=True)
class Effect:
    effect_order: int
    effect_type: str
    target: str
    parameter: str
    operation: str
    value: float
    value_type: str
    duration: int
    probability: float


@dataclass(frozen=True)
class Cost:
    sp: int = 0
    hp_percent: float = 0.0
    consume_action: bool = False


@dataclass(frozen=True)
class Skill:
    skill_id: str
    doc_id: str
    name_ja: str
    name_en: str
    concepts: list[Concept]
    trigger: str
    conditions: list[Condition]
    effects: list[Effect]
    cost: Cost
    cooldown: int
    generation_version: int
    description_ja: str
    description_en: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkillInput:
    doc_id: str
    embedding: list[float]
    parameter_scores: dict[str, float]
    title: str = ""
    author: str = ""
    source_type: str = ""
    text_excerpt: str = ""
    user_id: str | None = None


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    candidate_type: str
    label: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateMatch:
    candidate: Candidate
    similarity: float
    rank: int

