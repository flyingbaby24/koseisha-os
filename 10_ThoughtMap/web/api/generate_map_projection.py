"""CLI: build the cached 3D ThoughtMap projection artifact.

    python -m api.generate_map_projection

Run from `10_ThoughtMap/web`. This is offline work — the API never triggers it.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import get_settings
from .map_projection import (
    DEFAULT_ARTIFACT_PATH,
    ProjectionConfig,
    ProjectionError,
    ProjectionGenerator,
    write_artifact,
)
from .repositories import create_search_index_repository


def build_config(args: argparse.Namespace) -> ProjectionConfig:
    clustering = not args.no_clusters
    return ProjectionConfig(
        n_components=args.dimensions,
        metric=args.metric,
        n_neighbors=args.n_neighbors,
        min_dist=args.min_dist,
        random_seed=args.seed,
        cluster_algorithm="kmeans" if clustering else None,
        cluster_count=args.clusters if clustering else None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic 3D ThoughtMap projection artifact."
    )
    parser.add_argument("--output", default=str(DEFAULT_ARTIFACT_PATH), help="Artifact path.")
    parser.add_argument("--dimensions", type=int, default=3, help="UMAP n_components.")
    parser.add_argument("--metric", default="cosine", help="UMAP metric.")
    parser.add_argument("--n-neighbors", type=int, default=10, help="UMAP n_neighbors.")
    parser.add_argument("--min-dist", type=float, default=0.2, help="UMAP min_dist.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for UMAP and KMeans.")
    parser.add_argument("--clusters", type=int, default=8, help="KMeans cluster count.")
    parser.add_argument("--no-clusters", action="store_true", help="Skip clustering.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and validate, but do not write the artifact.",
    )
    parser.add_argument("--verbose", action="store_true", help="Log progress.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    settings = get_settings()
    repository = create_search_index_repository(settings)
    config = build_config(args)

    generator = ProjectionGenerator(index_loader=repository.load_index, config=config)

    try:
        artifact, stats = generator.generate()
    except ProjectionError as exc:
        print(f"Projection failed: {exc}", file=sys.stderr)
        return 1

    projection = artifact["projection"]

    print("ThoughtMap 3D projection")
    print(f"  backend            : {settings.backend}")
    print(f"  documents          : {stats.document_count}")
    print(f"  embedding dimension: {stats.embedding_dimension}")
    print(f"  algorithm          : {config.algorithm} n_components={config.n_components}")
    print(
        f"  config             : metric={config.metric} n_neighbors={config.n_neighbors} "
        f"min_dist={config.min_dist} seed={config.random_seed}"
    )
    print(f"  fingerprint        : {projection['dataset_fingerprint']}")
    print(f"  runtime            : {stats.runtime_seconds:.1f}s")

    for axis in ("x", "y", "z"):
        low, high = stats.bounds[axis]
        print(f"  {axis} bounds           : {low:.4f} -> {high:.4f}  (var {stats.axis_variance[axis]:.4f})")

    print(f"  bounding radius    : {stats.bounding_sphere_radius:.4f}")

    if stats.cluster_populations:
        populations = ", ".join(
            f"{key}:{value}" for key, value in sorted(stats.cluster_populations.items(), key=lambda kv: int(kv[0]))
        )
        print(f"  clusters           : {config.cluster_algorithm} k={config.cluster_count} -> {populations}")
    else:
        print("  clusters           : none")

    if args.dry_run:
        print("  dry run            : artifact not written")
        return 0

    written = write_artifact(artifact, args.output)
    size_mb = Path(written).stat().st_size / (1024 * 1024)
    print(f"  artifact           : {written}")
    print(f"  artifact size      : {size_mb:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
