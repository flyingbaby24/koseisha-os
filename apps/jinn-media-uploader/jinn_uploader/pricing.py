"""Monthly cost estimate for R2 Standard storage (egress is free on R2)."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Pricing

GB = 1_000_000_000  # Decimal GB, the conservative reading of "GB-month".


@dataclass
class CostEstimate:
    storage_gb: float
    billable_storage_gb: float
    storage_usd: float
    class_a_ops: int
    class_b_ops: int
    class_a_usd: float
    class_b_usd: float
    total_usd: float
    total_jpy: float

    @property
    def within_free_tier(self) -> bool:
        return self.total_usd <= 0


def estimate(storage_bytes: int, class_a_ops: int = 0, class_b_ops: int = 0, pricing: Pricing | None = None) -> CostEstimate:
    p = pricing or Pricing()
    gb = storage_bytes / GB
    billable_gb = max(0.0, gb - p.free_storage_gb)
    storage_usd = billable_gb * p.storage_per_gb_month
    a_usd = max(0.0, class_a_ops / 1e6 - p.free_class_a_million) * p.class_a_per_million
    b_usd = max(0.0, class_b_ops / 1e6 - p.free_class_b_million) * p.class_b_per_million
    total = storage_usd + a_usd + b_usd
    return CostEstimate(
        storage_gb=gb,
        billable_storage_gb=billable_gb,
        storage_usd=storage_usd,
        class_a_ops=class_a_ops,
        class_b_ops=class_b_ops,
        class_a_usd=a_usd,
        class_b_usd=b_usd,
        total_usd=total,
        total_jpy=total * p.usd_jpy,
    )


def upload_class_a_ops(size: int, multipart_threshold: int, part_size: int) -> int:
    """Class A operations one upload costs: 1 PUT, or create + N parts + complete."""
    if size < multipart_threshold:
        return 1
    parts = max(1, -(-size // part_size))
    return parts + 2
