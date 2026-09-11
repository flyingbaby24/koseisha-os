import {
  Box3,
  PerspectiveCamera,
  Sphere,
  Vector3,
  type Object3D,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import { computeClippingPlanes, computeFitDistance, computeFocusDistance } from "./cameraFraming";

const DEFAULT_FOV = 50;
const DEFAULT_POSITION = new Vector3(0, 0, 90);
const DEFAULT_TARGET = new Vector3(0, 0, 0);

/**
 * Canonical viewing direction, used when framing the map for the first time.
 * Only its direction matters; fitBox replaces the magnitude with the distance
 * that actually frames the content.
 */
const DEFAULT_VIEW_DIRECTION = new Vector3(0, 0, 1);

/**
 * Owns the perspective camera and orbit/pan/zoom input.
 *
 * Emits `onChange` whenever the view actually moved, so the scene can render on
 * demand instead of running a full render loop while the user is idle.
 */
export class CameraController {
  readonly camera: PerspectiveCamera;

  private readonly controls: OrbitControls;
  private readonly listeners = new Set<() => void>();
  private readonly homePosition = DEFAULT_POSITION.clone();
  private readonly homeTarget = DEFAULT_TARGET.clone();

  private readonly scratchBox = new Box3();
  private readonly scratchSphere = new Sphere();
  private readonly scratchSize = new Vector3();
  private readonly scratchCenter = new Vector3();
  private readonly scratchDirection = new Vector3();
  private motionQuery: MediaQueryList | null = null;
  private handleMotionPreference: (() => void) | null = null;

  constructor(domElement: HTMLElement, aspect: number) {
    this.camera = new PerspectiveCamera(DEFAULT_FOV, aspect, 0.1, 4000);
    this.camera.position.copy(this.homePosition);

    this.controls = new OrbitControls(this.camera, domElement);
    this.controls.target.copy(this.homeTarget);
    // Inertia after a drag is the only sustained motion in the scene. Someone
    // who has asked for reduced motion gets the camera stopping when their
    // hand does, rather than gliding — navigation is unchanged, only the
    // coasting goes (T7 #34).
    this.controls.enableDamping = !prefersReducedMotion();
    this.controls.dampingFactor = 0.08;
    this.controls.rotateSpeed = 0.7;
    this.controls.zoomSpeed = 0.9;
    this.controls.panSpeed = 0.8;
    this.controls.screenSpacePanning = true;
    this.controls.minDistance = 1;
    this.controls.maxDistance = 2000;
    this.controls.addEventListener("change", this.handleChange);
    this.controls.update();

    // Honour the preference changing while the page is open.
    this.motionQuery = matchMediaSafe("(prefers-reduced-motion: reduce)");
    if (this.motionQuery) {
      this.handleMotionPreference = () => {
        this.controls.enableDamping = !this.motionQuery?.matches;
      };
      this.motionQuery.addEventListener("change", this.handleMotionPreference);
    }
  }

  /** Register a callback fired when the camera moved and a redraw is needed. */
  onChange(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Advance damping. Returns true while the camera is still settling, so the
   * caller knows another frame is required.
   */
  update(): boolean {
    return this.controls.update();
  }

  setAspect(aspect: number): void {
    if (!Number.isFinite(aspect) || aspect <= 0) {
      return;
    }
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
  }

  /**
   * Redefine what Reset returns to.
   *
   * Before any map is loaded the home view is the arbitrary default. Once the
   * projection exists, the meaningful "home" is the fitted whole-map view from
   * the canonical angle, so the map load calls this.
   */
  setHome(position: Vector3, target: Vector3): void {
    this.homePosition.copy(position);
    this.homeTarget.copy(target);
  }

  /**
   * Return to the home view: canonical orientation *and* fitted distance.
   *
   * This is what distinguishes Reset from Fit All. Reset restores the default
   * viewing angle as well as the framing; Fit All re-frames from wherever the
   * user is currently looking.
   */
  reset(): void {
    this.discardPendingInput();
    this.camera.position.copy(this.homePosition);
    this.controls.target.copy(this.homeTarget);
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.emitChange();
  }

  /** Frame an explicit bounding box, keeping the current viewing direction. */
  fitBox(box: Box3, padding = 1.2): void {
    if (box.isEmpty()) {
      this.reset();
      return;
    }

    // Must happen before the viewing direction is sampled below, so the fit is
    // computed from where the camera actually ends up rather than mid-glide.
    this.discardPendingInput();

    box.getSize(this.scratchSize);
    box.getCenter(this.scratchCenter);

    const distance = computeFitDistance({
      size: { x: this.scratchSize.x, y: this.scratchSize.y, z: this.scratchSize.z },
      fovDegrees: this.camera.fov,
      aspect: this.camera.aspect,
      padding,
    });

    box.getBoundingSphere(this.scratchSphere);
    const planes = computeClippingPlanes(distance, this.scratchSphere.radius);
    this.camera.near = planes.near;
    this.camera.far = planes.far;

    // Keep the user's current angle; only the distance and target change.
    this.scratchDirection.subVectors(this.camera.position, this.controls.target);
    if (this.scratchDirection.lengthSq() < 1e-8) {
      this.scratchDirection.copy(DEFAULT_POSITION);
    }
    this.scratchDirection.normalize().multiplyScalar(distance);

    this.controls.target.copy(this.scratchCenter);
    this.camera.position.copy(this.scratchCenter).add(this.scratchDirection);
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.emitChange();
  }

  /**
   * Move to look at one point from a readable distance.
   *
   * Distinct from Reset, Fit All and Fit Results. The current viewing
   * *direction* is preserved and only the target and distance change, so
   * focusing a result never spins the space to an unfamiliar angle. The
   * distance comes from the map's own extent, not a constant tuned to one
   * corpus.
   */
  focusPoint(point: Vector3, mapExtent: number, fraction?: number): void {
    this.discardPendingInput();

    const distance = computeFocusDistance(mapExtent, fraction);

    this.scratchDirection.subVectors(this.camera.position, this.controls.target);
    if (this.scratchDirection.lengthSq() < 1e-8) {
      this.scratchDirection.copy(DEFAULT_VIEW_DIRECTION);
    }
    this.scratchDirection.normalize().multiplyScalar(distance);

    const planes = computeClippingPlanes(distance, Math.max(mapExtent, distance));
    this.camera.near = planes.near;
    this.camera.far = planes.far;

    this.controls.target.copy(point);
    this.camera.position.copy(point).add(this.scratchDirection);
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.emitChange();
  }

  /**
   * Frame a set of world-space points.
   *
   * One point degenerates to a focus rather than a zero-sized box, which would
   * otherwise put the camera inside the node.
   */
  fitPoints(points: readonly Vector3[], mapExtent: number, padding = 1.4): boolean {
    if (points.length === 0) {
      return false;
    }

    if (points.length === 1) {
      this.focusPoint(points[0]!, mapExtent);
      return true;
    }

    this.scratchBox.makeEmpty();
    for (const point of points) {
      this.scratchBox.expandByPoint(point);
    }

    // Results that happen to be coincident (or collinear on some axis) would
    // give a degenerate box; fitBox already guards each axis, but a fully
    // empty box means nothing usable was supplied.
    if (this.scratchBox.isEmpty()) {
      return false;
    }

    // A tightly clustered result set — ten works by one author sitting almost
    // on top of each other — has a box small enough that a literal fit puts
    // the camera inside the cloud. Never approach a group more closely than a
    // single node, so the framing stays readable instead of collapsing.
    this.scratchBox.getSize(this.scratchSize);
    const extent = Math.max(this.scratchSize.x, this.scratchSize.y, this.scratchSize.z);

    if (extent < computeFocusDistance(mapExtent)) {
      this.scratchBox.getCenter(this.scratchCenter);
      this.focusPoint(this.scratchCenter, mapExtent);
      return true;
    }

    this.fitBox(this.scratchBox, padding);
    return true;
  }

  /** Frame everything renderable under `object`. */
  fitObject(object: Object3D, padding = 1.2): void {
    this.scratchBox.setFromObject(object);
    this.fitBox(this.scratchBox, padding);
  }

  /**
   * Frame a box from the canonical default direction and adopt it as home.
   *
   * Used once when the map loads: it gives Reset Camera a meaningful target
   * instead of the pre-map `[0, 0, 90]` placeholder.
   */
  fitBoxAsHome(box: Box3, padding = 1.2): void {
    if (box.isEmpty()) {
      return;
    }

    // Face the map down -Z, the same orientation the default view used, so a
    // first load is predictable rather than depending on any earlier drag.
    this.discardPendingInput();
    box.getCenter(this.scratchCenter);
    this.controls.target.copy(this.scratchCenter);
    this.camera.position.copy(this.scratchCenter).add(DEFAULT_VIEW_DIRECTION);
    this.controls.update();

    this.fitBox(box, padding);

    this.homePosition.copy(this.camera.position);
    this.homeTarget.copy(this.controls.target);
  }

  dispose(): void {
    if (this.motionQuery && this.handleMotionPreference) {
      this.motionQuery.removeEventListener("change", this.handleMotionPreference);
    }
    this.controls.removeEventListener("change", this.handleChange);
    this.controls.dispose();
    this.listeners.clear();
  }

  /**
   * Drop rotation/pan/zoom that the user's last gesture has not finished
   * applying, before the camera is placed programmatically.
   *
   * While damping is on, OrbitControls carries those deltas across frames. A
   * Reset or Fit that just assigns a position would be dragged off it over the
   * following frames. Running one update with damping off flushes the deltas
   * and zeroes them; only then is it safe to assign the new position. Doing
   * this *after* assignment would instead apply the whole leftover delta to the
   * fresh position, which is the bug this replaced.
   */
  private discardPendingInput(): void {
    const damping = this.controls.enableDamping;
    this.controls.enableDamping = false;
    this.controls.update();
    this.controls.enableDamping = damping;
  }

  private readonly handleChange = (): void => {
    this.emitChange();
  };

  private emitChange(): void {
    for (const listener of this.listeners) {
      listener();
    }
  }
}


/**
 * `matchMedia`, or null where it does not exist.
 *
 * Tests run in a DOM-less environment and older embedded browsers lack it, so
 * a missing `matchMedia` must mean "no preference expressed", not a crash.
 */
function matchMediaSafe(query: string): MediaQueryList | null {
  try {
    return typeof globalThis.matchMedia === "function" ? globalThis.matchMedia(query) : null;
  } catch {
    return null;
  }
}

/** Whether this viewer has asked the system for reduced motion. */
export function prefersReducedMotion(): boolean {
  return matchMediaSafe("(prefers-reduced-motion: reduce)")?.matches ?? false;
}
