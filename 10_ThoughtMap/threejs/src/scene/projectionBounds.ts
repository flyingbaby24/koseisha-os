/**
 * Bounds and the single presentation transform applied to the projection.
 *
 * Pure math, no three.js and no DOM, so it is fully unit testable.
 *
 * The rule this file exists to enforce: semantic geometry stays in the data.
 * The projection's own shape — including the fact that one axis may be far
 * wider than another — is meaningful. So the map is placed in the scene with
 * exactly one *uniform* scale and one centre offset. Scaling x, y and z
 * independently to fill the viewport would stretch the space and misrepresent
 * the distances UMAP produced.
 */

export interface Point3 {
  x: number;
  y: number;
  z: number;
}

export interface ProjectionBounds {
  min: Point3;
  max: Point3;
  center: Point3;
  size: Point3;
  /** Largest single-axis extent. Drives the uniform scale. */
  maxExtent: number;
  /** Radius of the sphere around `center` containing every point. */
  radius: number;
  count: number;
}

export interface ProjectionTransform {
  /** One factor for all three axes. Never per-axis. */
  scale: number;
  /** World-space offset applied after scaling, so the cloud sits at the origin. */
  offset: Point3;
}

const EMPTY_BOUNDS: ProjectionBounds = {
  min: { x: 0, y: 0, z: 0 },
  max: { x: 0, y: 0, z: 0 },
  center: { x: 0, y: 0, z: 0 },
  size: { x: 0, y: 0, z: 0 },
  maxExtent: 0,
  radius: 0,
  count: 0,
};

/**
 * World-space extent the map is scaled to occupy along its widest axis.
 * Arbitrary but fixed, so camera distances and point sizes are predictable
 * regardless of what range UMAP happens to output for a given corpus.
 */
export const TARGET_WORLD_EXTENT = 100;

export function computeBounds(points: ReadonlyArray<Point3>): ProjectionBounds {
  if (points.length === 0) {
    return { ...EMPTY_BOUNDS };
  }

  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;
  let counted = 0;

  for (const point of points) {
    if (!Number.isFinite(point.x) || !Number.isFinite(point.y) || !Number.isFinite(point.z)) {
      // A non-finite coordinate would poison the bounds and blank the canvas.
      // The generator rejects these, so reaching here means bad data upstream.
      continue;
    }
    counted += 1;
    if (point.x < minX) minX = point.x;
    if (point.y < minY) minY = point.y;
    if (point.z < minZ) minZ = point.z;
    if (point.x > maxX) maxX = point.x;
    if (point.y > maxY) maxY = point.y;
    if (point.z > maxZ) maxZ = point.z;
  }

  if (counted === 0) {
    return { ...EMPTY_BOUNDS };
  }

  const center = { x: (minX + maxX) / 2, y: (minY + maxY) / 2, z: (minZ + maxZ) / 2 };
  const size = { x: maxX - minX, y: maxY - minY, z: maxZ - minZ };

  let radiusSquared = 0;
  for (const point of points) {
    if (!Number.isFinite(point.x) || !Number.isFinite(point.y) || !Number.isFinite(point.z)) {
      continue;
    }
    const dx = point.x - center.x;
    const dy = point.y - center.y;
    const dz = point.z - center.z;
    const distance = dx * dx + dy * dy + dz * dz;
    if (distance > radiusSquared) {
      radiusSquared = distance;
    }
  }

  return {
    min: { x: minX, y: minY, z: minZ },
    max: { x: maxX, y: maxY, z: maxZ },
    center,
    size,
    maxExtent: Math.max(size.x, size.y, size.z),
    radius: Math.sqrt(radiusSquared),
    count: counted,
  };
}

/**
 * The single uniform scale + centre offset that places the cloud at the origin
 * at a predictable size, without distorting its proportions.
 */
export function computeTransform(
  bounds: ProjectionBounds,
  targetExtent = TARGET_WORLD_EXTENT,
): ProjectionTransform {
  // A degenerate cloud (one node, or all nodes coincident) has no extent to
  // scale from; fall back to 1 rather than dividing by zero.
  const scale = bounds.maxExtent > 0 ? targetExtent / bounds.maxExtent : 1;

  return {
    scale,
    offset: {
      x: -bounds.center.x * scale,
      y: -bounds.center.y * scale,
      z: -bounds.center.z * scale,
    },
  };
}

/** Apply the transform to one point, matching what the scene graph does. */
export function applyTransform(point: Point3, transform: ProjectionTransform): Point3 {
  return {
    x: point.x * transform.scale + transform.offset.x,
    y: point.y * transform.scale + transform.offset.y,
    z: point.z * transform.scale + transform.offset.z,
  };
}

/** True when the cloud has real volume rather than sitting on a plane. */
export function isVolumetric(bounds: ProjectionBounds, minRatio = 0.05): boolean {
  if (bounds.maxExtent <= 0) {
    return false;
  }
  const smallest = Math.min(bounds.size.x, bounds.size.y, bounds.size.z);
  return smallest / bounds.maxExtent >= minRatio;
}
