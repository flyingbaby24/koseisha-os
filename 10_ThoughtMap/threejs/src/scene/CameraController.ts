import {
  Box3,
  PerspectiveCamera,
  Sphere,
  Vector3,
  type Object3D,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import {
  NO_INSETS,
  computeClippingPlanes,
  computeFitDistance,
  computeFocusDistance,
  computeViewWindow,
  easeInOutCubic,
  type ViewInsets,
} from "./cameraFraming";

const DEFAULT_FOV = 50;

/** Length of a programmatic move. Long enough to follow, short enough not to wait on. */
const TRANSITION_MS = 720;

/** Options shared by every programmatic camera move. */
export interface MoveOptions {
  /**
   * Glide to the destination instead of jumping. Ignored (always a jump) when
   * the viewer has asked for reduced motion.
   */
  animate?: boolean;
}

interface Transition {
  started: number;
  duration: number;
  fromTarget: Vector3;
  toTarget: Vector3;
  fromDirection: Vector3;
  toDirection: Vector3;
  fromDistance: number;
  toDistance: number;
  /** Extra pull-back at mid-flight, as a fraction of distance. */
  lift: number;
  near: number;
  far: number;
}
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
  /**
   * The field of view the scene is designed around. `camera.fov` can be wider
   * while a view offset is active (see `setViewport`); point sizing and
   * framing always use this.
   */
  readonly baseFov = DEFAULT_FOV;

  private readonly controls: OrbitControls;
  private readonly listeners = new Set<() => void>();
  private readonly homePosition = DEFAULT_POSITION.clone();
  private readonly homeTarget = DEFAULT_TARGET.clone();

  private readonly scratchBox = new Box3();
  private readonly scratchSphere = new Sphere();
  private readonly scratchSize = new Vector3();
  private readonly scratchCenter = new Vector3();
  private readonly scratchDirection = new Vector3();
  private readonly scratchTarget = new Vector3();
  private readonly scratchPosition = new Vector3();
  /** Vertical fov and aspect of the visible map window, used for framing. */
  private fitFov = DEFAULT_FOV;
  private fitAspect: number;
  private transition: Transition | null = null;
  private motionQuery: MediaQueryList | null = null;
  private handleMotionPreference: (() => void) | null = null;

  constructor(domElement: HTMLElement, aspect: number) {
    this.camera = new PerspectiveCamera(DEFAULT_FOV, aspect, 0.1, 4000);
    this.camera.position.copy(this.homePosition);
    this.fitAspect = aspect > 0 && Number.isFinite(aspect) ? aspect : 1;

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
    // Zoom toward what is under the pointer, as map software does. Exploring a
    // dense region no longer means zooming and then panning to correct.
    this.controls.zoomToCursor = true;
    this.controls.minDistance = 1;
    this.controls.maxDistance = 2000;
    this.controls.addEventListener("change", this.handleChange);
    // The person's hand always wins over a programmatic glide.
    this.controls.addEventListener("start", this.cancelTransition);
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
   * Advance damping or an in-flight move. Returns true while the camera is
   * still settling, so the caller knows another frame is required.
   */
  update(now: number = performance.now()): boolean {
    if (this.transition) {
      this.stepTransition(now);
      return true;
    }
    return this.controls.update();
  }

  /** True while a programmatic move is gliding. */
  get isTransitioning(): boolean {
    return this.transition !== null;
  }

  /** Distance from the camera to the point it orbits. */
  get focusDistance(): number {
    return this.camera.position.distanceTo(this.controls.target);
  }

  setAspect(aspect: number): void {
    if (!Number.isFinite(aspect) || aspect <= 0) {
      return;
    }
    this.camera.clearViewOffset();
    this.camera.fov = this.baseFov;
    this.camera.aspect = aspect;
    this.fitFov = this.baseFov;
    this.fitAspect = aspect;
    this.camera.updateProjectionMatrix();
  }

  /**
   * Size the camera to the canvas, centred on the part of it that is visible.
   *
   * `insets` is the space panels cover on each edge. The optical centre moves
   * to the middle of what is left, so focusing a document puts it where the
   * reader is looking instead of behind a panel, and framing fits the visible
   * window rather than the whole canvas. Pixel scale is unchanged.
   */
  setViewport(width: number, height: number, insets: ViewInsets = NO_INSETS): void {
    if (!(width > 0) || !(height > 0)) {
      return;
    }
    const view = computeViewWindow(width, height, insets, this.baseFov);

    this.camera.fov = view.fov;
    this.camera.aspect = view.aspect;
    if (view.active) {
      this.camera.setViewOffset(
        view.fullWidth,
        view.fullHeight,
        view.offsetX,
        view.offsetY,
        width,
        height,
      );
    } else {
      this.camera.clearViewOffset();
    }
    this.fitFov = view.visibleFov;
    this.fitAspect = view.visibleAspect;
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
  reset(options: MoveOptions = {}): void {
    this.discardPendingInput();
    const distance = this.homePosition.distanceTo(this.homeTarget);
    const planes = computeClippingPlanes(distance, distance);
    this.moveTo(this.homePosition, this.homeTarget, options, {
      near: Math.min(this.camera.near, planes.near),
      far: Math.max(this.camera.far, planes.far),
    });
  }

  /** Frame an explicit bounding box, keeping the current viewing direction. */
  fitBox(box: Box3, padding = 1.2, options: MoveOptions = {}): void {
    if (box.isEmpty()) {
      this.reset(options);
      return;
    }

    // Must happen before the viewing direction is sampled below, so the fit is
    // computed from where the camera actually ends up rather than mid-glide.
    this.discardPendingInput();

    box.getSize(this.scratchSize);
    box.getCenter(this.scratchCenter);

    // Framed against the visible map window, not the whole canvas, so the
    // fitted content is not partly behind a panel.
    const distance = computeFitDistance({
      size: { x: this.scratchSize.x, y: this.scratchSize.y, z: this.scratchSize.z },
      fovDegrees: this.fitFov,
      aspect: this.fitAspect,
      padding,
    });

    box.getBoundingSphere(this.scratchSphere);
    const planes = computeClippingPlanes(distance, this.scratchSphere.radius);

    // Keep the user's current angle; only the distance and target change.
    this.scratchDirection.subVectors(this.camera.position, this.controls.target);
    if (this.scratchDirection.lengthSq() < 1e-8) {
      this.scratchDirection.copy(DEFAULT_POSITION);
    }
    this.scratchDirection.normalize().multiplyScalar(distance);

    const position = this.scratchPosition.copy(this.scratchCenter).add(this.scratchDirection);
    this.moveTo(position, this.scratchCenter, options, planes);
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
  focusPoint(
    point: Vector3,
    mapExtent: number,
    fraction?: number,
    options: MoveOptions = {},
  ): void {
    this.discardPendingInput();

    const distance = computeFocusDistance(mapExtent, fraction);

    this.scratchDirection.subVectors(this.camera.position, this.controls.target);
    if (this.scratchDirection.lengthSq() < 1e-8) {
      this.scratchDirection.copy(DEFAULT_VIEW_DIRECTION);
    }
    this.scratchDirection.normalize().multiplyScalar(distance);

    const planes = computeClippingPlanes(distance, Math.max(mapExtent, distance));
    this.scratchTarget.copy(point);
    const position = this.scratchPosition.copy(point).add(this.scratchDirection);
    this.moveTo(position, this.scratchTarget, options, planes);
  }

  /**
   * Frame a set of world-space points.
   *
   * One point degenerates to a focus rather than a zero-sized box, which would
   * otherwise put the camera inside the node.
   */
  fitPoints(
    points: readonly Vector3[],
    mapExtent: number,
    padding = 1.4,
    options: MoveOptions = {},
  ): boolean {
    if (points.length === 0) {
      return false;
    }

    if (points.length === 1) {
      this.focusPoint(points[0]!, mapExtent, undefined, options);
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
      this.focusPoint(this.scratchCenter, mapExtent, undefined, options);
      return true;
    }

    this.fitBox(this.scratchBox, padding, options);
    return true;
  }

  /** Frame everything renderable under `object`. */
  fitObject(object: Object3D, padding = 1.2, options: MoveOptions = {}): void {
    this.scratchBox.setFromObject(object);
    this.fitBox(this.scratchBox, padding, options);
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
    this.transition = null;
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
    this.transition = null;
    this.controls.removeEventListener("change", this.handleChange);
    this.controls.removeEventListener("start", this.cancelTransition);
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

  /**
   * Place the camera, either at once or by gliding there.
   *
   * The glide keeps the motion legible: the target slides, the viewing
   * direction turns along the shorter arc, distance changes geometrically (so
   * zooming feels even at every scale), and a long hop pulls back slightly at
   * mid-flight so the surroundings stay in view and the reader keeps their
   * bearings instead of being teleported.
   */
  private moveTo(
    position: Vector3,
    target: Vector3,
    options: MoveOptions,
    planes: { near: number; far: number },
  ): void {
    const animate = options.animate === true && !prefersReducedMotion();
    const fromDistance = this.camera.position.distanceTo(this.controls.target);
    const toDistance = position.distanceTo(target);
    const fromDirection = this.camera.position.clone().sub(this.controls.target);
    const toDirection = position.clone().sub(target);
    const degenerate =
      fromDistance < 1e-6 ||
      toDistance < 1e-6 ||
      fromDirection.normalize().dot(toDirection.normalize()) < -0.95;

    if (!animate || degenerate) {
      this.transition = null;
      this.camera.near = planes.near;
      this.camera.far = planes.far;
      this.controls.target.copy(target);
      this.camera.position.copy(position);
      this.camera.updateProjectionMatrix();
      this.controls.update();
      this.emitChange();
      return;
    }

    const travel = this.controls.target.distanceTo(target);
    const lift = Math.min(0.6, (travel / Math.max(fromDistance, toDistance)) * 0.2);

    this.transition = {
      started: performance.now(),
      duration: TRANSITION_MS,
      fromTarget: this.controls.target.clone(),
      toTarget: target.clone(),
      fromDirection,
      toDirection,
      fromDistance,
      toDistance,
      lift,
      near: planes.near,
      far: planes.far,
    };

    // Planes wide enough for the whole flight, tightened again on arrival.
    this.camera.near = Math.min(this.camera.near, planes.near);
    this.camera.far = Math.max(this.camera.far, planes.far * (1 + lift));
    this.camera.updateProjectionMatrix();
    this.emitChange();
  }

  private stepTransition(now: number): void {
    const flight = this.transition;
    if (!flight) {
      return;
    }

    const t = Math.min(1, Math.max(0, (now - flight.started) / flight.duration));
    const e = easeInOutCubic(t);

    this.controls.target.lerpVectors(flight.fromTarget, flight.toTarget, e);
    this.scratchDirection.lerpVectors(flight.fromDirection, flight.toDirection, e).normalize();
    const distance =
      Math.exp(Math.log(flight.fromDistance) * (1 - e) + Math.log(flight.toDistance) * e) *
      (1 + flight.lift * Math.sin(Math.PI * e));

    this.camera.position.copy(this.controls.target).addScaledVector(this.scratchDirection, distance);

    if (t >= 1) {
      this.transition = null;
      this.controls.target.copy(flight.toTarget);
      this.camera.position.copy(flight.toTarget).addScaledVector(flight.toDirection, flight.toDistance);
      this.camera.near = flight.near;
      this.camera.far = flight.far;
      this.camera.updateProjectionMatrix();
    }

    this.controls.update();
    this.emitChange();
  }

  /** Stop a glide where it is; the user has taken over. */
  private readonly cancelTransition = (): void => {
    const flight = this.transition;
    if (!flight) {
      return;
    }
    this.transition = null;
    this.camera.far = Math.max(this.camera.far, flight.far);
    this.camera.updateProjectionMatrix();
  };

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
