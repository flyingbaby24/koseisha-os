import { Box3, Scene, WebGLRenderer } from "three";

import type { MapNode } from "../api/mapTypes";
import { BackgroundRenderer } from "./BackgroundRenderer";
import { CameraController } from "./CameraController";
import { NO_INSETS, type ViewInsets } from "./cameraFraming";
import { NodeRenderer } from "./NodeRenderer";

const MAX_PIXEL_RATIO = 2;

/**
 * Owns the renderer, the scene graph, and the render loop.
 *
 * Render-on-demand: a frame is drawn only when something asked for it (camera
 * moved, viewport resized, scene content changed) or while orbit damping is
 * still settling. Nothing is computed while the user is idle.
 */
export class ThoughtMapScene {
  readonly scene = new Scene();
  readonly camera: CameraController;

  readonly nodes = new NodeRenderer();
  /** Exposed so the interaction layer can attach pointer handlers and measure. */
  readonly renderer: WebGLRenderer;

  private readonly container: HTMLElement;
  private readonly background = new BackgroundRenderer();
  private readonly resizeObserver: ResizeObserver;
  private readonly disposers: Array<() => void> = [];

  /** The part of the canvas not covered by panels; see `setSafeArea`. */
  private safeArea: HTMLElement | null = null;
  private frameHandle = 0;
  private needsRender = true;
  private running = false;
  private disposed = false;

  constructor(container: HTMLElement) {
    this.container = container;

    this.renderer = new WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, MAX_PIXEL_RATIO));
    this.renderer.domElement.classList.add("tm-canvas");

    // A screen reader otherwise meets an unlabelled canvas and can say nothing
    // about it. The map is a second view of data that is fully available as
    // text — the results list and the radar's numeric table — so the honest
    // label says what it shows and where to read it instead (T7 #33).
    this.renderer.domElement.setAttribute("role", "img");
    this.renderer.domElement.setAttribute(
      "aria-label",
      "Thought space: a 3D map of the document corpus. Search results are " +
        "highlighted here and listed as text in the Results panel.",
    );
    this.container.appendChild(this.renderer.domElement);

    const { width, height } = this.measure();
    this.renderer.setSize(width, height, false);

    this.camera = new CameraController(this.renderer.domElement, width / height);
    this.camera.setViewport(width, height);
    this.disposers.push(this.camera.onChange(() => this.requestRender()));

    this.background.applyTo(this.scene);
    this.nodes.addTo(this.scene);
    this.syncPointScale();

    this.resizeObserver = new ResizeObserver(() => this.handleResize());
    this.resizeObserver.observe(this.container);
  }

  start(): void {
    if (this.running || this.disposed) {
      return;
    }
    this.running = true;
    this.requestRender();
    this.frameHandle = requestAnimationFrame(this.tick);
  }

  stop(): void {
    this.running = false;
    if (this.frameHandle !== 0) {
      cancelAnimationFrame(this.frameHandle);
      this.frameHandle = 0;
    }
  }

  /** Ask for one more frame. Cheap and safe to call repeatedly. */
  requestRender(): void {
    this.needsRender = true;
  }

  /**
   * Centre the camera on an element's rectangle instead of the whole canvas.
   *
   * The canvas fills the window behind translucent panels; the element is the
   * gap between them (the map window). Measured on every resize of either the
   * canvas or the element, so a layout change re-centres without anyone
   * having to call this again. Null restores whole-canvas centring.
   */
  setSafeArea(element: HTMLElement | null): void {
    if (this.safeArea) {
      this.resizeObserver.unobserve(this.safeArea);
    }
    this.safeArea = element;
    if (element) {
      this.resizeObserver.observe(element);
    }
    this.handleResize();
  }

  /** Frame everything currently in the scene except the decorative background. */
  fitAll(padding = 1.2): void {
    const box = new Box3();
    let hasContent = false;

    for (const child of this.scene.children) {
      if (child === this.background.object || child === this.nodes.emphasisObject) {
        continue;
      }
      box.expandByObject(child);
      hasContent = true;
    }

    if (!hasContent || box.isEmpty()) {
      this.camera.reset();
      return;
    }

    this.camera.fitBox(box, padding);
  }

  /**
   * Install the projection and frame it.
   *
   * Geometry is built once here, not per frame, and a single render is
   * requested afterwards — the map does not start an animation loop.
   */
  setMapNodes(nodes: readonly MapNode[]): void {
    this.nodes.setNodes(nodes);

    if (nodes.length > 0) {
      const box = new Box3().setFromObject(this.nodes.object);
      // Adopting this as home is what makes Reset Camera mean "the whole map"
      // instead of the pre-map placeholder position.
      this.camera.fitBoxAsHome(box);
    }

    this.requestRender();
  }

  /** Frame the whole map from the current viewing angle, gliding there. */
  fitAllNodes(padding = 1.2): void {
    if (this.nodes.count === 0) {
      this.camera.reset({ animate: true });
      return;
    }
    this.camera.fitObject(this.nodes.object, padding, { animate: true });
  }

  /** Back to the home view, gliding there. */
  resetCamera(): void {
    this.camera.reset({ animate: true });
  }

  dispose(): void {
    if (this.disposed) {
      return;
    }
    this.disposed = true;
    this.stop();
    this.resizeObserver.disconnect();

    for (const dispose of this.disposers) {
      dispose();
    }
    this.disposers.length = 0;

    this.camera.dispose();
    this.nodes.dispose();
    this.background.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }

  private readonly tick = (): void => {
    if (!this.running) {
      return;
    }

    // Damping keeps moving the camera for a few frames after input stops.
    const settling = this.camera.update();

    if (this.needsRender || settling) {
      this.needsRender = false;
      // Two uniform writes, only on frames that are actually drawn.
      this.nodes.setDepthCue(this.camera.focusDistance);
      this.renderer.render(this.scene, this.camera.camera);
    }

    this.frameHandle = requestAnimationFrame(this.tick);
  };

  private handleResize(): void {
    const { width, height } = this.measure();
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, MAX_PIXEL_RATIO));
    this.renderer.setSize(width, height, false);
    this.camera.setViewport(width, height, this.measureSafeArea());
    // Point size is expressed in device pixels, so it has to follow the
    // drawing buffer rather than staying fixed across viewport changes.
    this.syncPointScale();
    this.requestRender();
  }

  private syncPointScale(): void {
    // The base fov, not camera.fov: a view offset widens the latter without
    // changing pixel scale, and point size must not change with it.
    this.nodes.setViewportScale(
      this.renderer.domElement.height,
      this.camera.baseFov,
      this.renderer.getPixelRatio(),
    );
  }

  private measureSafeArea(): ViewInsets {
    if (!this.safeArea) {
      return NO_INSETS;
    }
    const outer = this.container.getBoundingClientRect();
    const inner = this.safeArea.getBoundingClientRect();
    if (inner.width <= 0 || inner.height <= 0) {
      return NO_INSETS;
    }
    const clamp = (value: number) => Math.max(0, Math.round(value));
    return {
      top: clamp(inner.top - outer.top),
      right: clamp(outer.right - inner.right),
      bottom: clamp(outer.bottom - inner.bottom),
      left: clamp(inner.left - outer.left),
    };
  }

  private measure(): { width: number; height: number } {
    const rect = this.container.getBoundingClientRect();
    return {
      width: Math.max(1, Math.floor(rect.width)),
      height: Math.max(1, Math.floor(rect.height)),
    };
  }
}
