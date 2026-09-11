import "./styles/main.css";

import { ThoughtMapApiClient } from "./api/ThoughtMapApiClient";
import { DeploymentController } from "./app/DeploymentController";
import { SearchScreen } from "./app/SearchScreen";
import type { ThoughtMapInteractionController } from "./app/ThoughtMapInteractionController";
import type { ThoughtMapScene } from "./scene/ThoughtMapScene";

/**
 * Wiring only.
 *
 * Scene work belongs in `src/scene`, application state in `src/app`, API access
 * in `src/api`, and DOM panels in `src/ui`. This file must stay a composition
 * root and never grow logic of its own.
 *
 * Load order matters here (T6 #29, #38). The search UI is built and made
 * interactive first; Three.js, the scene and the 12.6 MB map arrive afterwards
 * on their own schedule. Three.js is ~470 kB of the bundle, so importing it
 * statically would have made every first paint wait for a library the first
 * interaction does not need. Both `ThoughtMapScene` and
 * `ThoughtMapInteractionController` are therefore imported dynamically, and
 * only their types are imported above — `import type` is erased at build time
 * and pulls nothing into the entry chunk.
 */
function main(): void {
  const viewport = document.getElementById("tm-viewport");
  const uiMount = document.getElementById("tm-ui");

  if (!uiMount) {
    showFatal("UI mount #tm-ui was not found.");
    return;
  }

  const client = new ThoughtMapApiClient();
  const screen = new SearchScreen(uiMount, client);

  // What this deployment offers, and whether it is ready. Neither blocks the
  // UI: search is usable while both are still in flight.
  const deployment = new DeploymentController(screen.state, client);
  void deployment.loadFeatures().then(() => screen.enableLibraryIfAvailable());
  void deployment.start();

  if (!viewport) {
    showFatal("Viewport element #tm-viewport was not found.");
    return;
  }

  let scene: ThoughtMapScene | null = null;
  let interaction: ThoughtMapInteractionController | null = null;
  let disposeTooltip: (() => void) | null = null;

  // The camera bar is bound immediately but does nothing until the scene
  // exists, rather than being absent and appearing later — a control that
  // moves after the page settles is worse than one that is briefly inert.
  bindCameraControls(
    () => scene,
    () => interaction,
    screen,
  );

  const sceneReady = startScene(viewport, screen)
    .then((started) => {
      if (!started) {
        return;
      }
      scene = started.scene;
      interaction = started.interaction;
      disposeTooltip = started.dispose;
      exposeDevHandle(started.scene, screen, started.interaction);
    })
    .catch((error: unknown) => {
      // The map is one view of the corpus, not the application. Losing it must
      // leave search, results, the radar and the library working.
      console.error("[ThoughtMap] Thought space unavailable.", error);
      screen.state.mapFailed(
        "The 3D thought space could not be started in this browser.",
      );
    });

  window.addEventListener(
    "beforeunload",
    () => {
      void sceneReady.then(() => {
        disposeTooltip?.();
        interaction?.dispose();
        scene?.dispose();
      });
      deployment.dispose();
      screen.dispose();
    },
    { once: true },
  );
}

interface StartedScene {
  scene: ThoughtMapScene;
  interaction: ThoughtMapInteractionController;
  dispose: () => void;
}

/**
 * Bring up WebGL, the interaction controller and the map data.
 *
 * Returns null rather than throwing when WebGL is simply unavailable, because
 * that is a supported outcome: the app runs without a map.
 */
async function startScene(
  viewport: HTMLElement,
  screen: SearchScreen,
): Promise<StartedScene | null> {
  const [{ ThoughtMapScene }, { ThoughtMapInteractionController }, { MapTooltip }] =
    await Promise.all([
      import("./scene/ThoughtMapScene"),
      import("./app/ThoughtMapInteractionController"),
      import("./ui/MapTooltip"),
    ]);

  let scene: ThoughtMapScene;
  try {
    scene = new ThoughtMapScene(viewport);
  } catch (error) {
    console.error("[ThoughtMap] WebGL could not be initialised.", error);
    screen.state.mapFailed(
      // MapStatusView already appends "Search remains available."; saying it
      // twice reads as a script rather than an explanation.
      "WebGL could not be initialised, so the thought space cannot be drawn. " +
        "Check that hardware acceleration is enabled.",
    );
    return null;
  }

  scene.start();

  const tooltip = new MapTooltip(viewport);
  const interaction = new ThoughtMapInteractionController(
    scene,
    screen.state,
    screen.selection,
    {
      onHover: (info) => (info ? tooltip.show(info) : tooltip.hide()),
    },
  );

  // The scene follows map state rather than being driven directly, so the
  // shared state stays the single source of truth for what is on screen.
  let renderedNodes: unknown = null;
  const unsubscribe = screen.state.subscribe((snapshot) => {
    if (snapshot.mapNodes !== renderedNodes) {
      renderedNodes = snapshot.mapNodes;
      scene.setMapNodes(snapshot.mapNodes);
    }
    interaction.syncFromState(snapshot);
    updateFitResultsEnabled(interaction.canFitResults(snapshot));
  });

  // Selecting anywhere — result row or map node — takes the camera to the
  // node. One path, so the two can never disagree.
  const unwatchSelection = screen.onSelectionChange((docId) => {
    if (docId !== null) {
      interaction.focusDocument(docId);
    }
  });

  // Started only now, so the map download never competes with the assets the
  // first interaction needs. A map failure is reported in the UI and must not
  // stop search working.
  void screen.map.load();

  return {
    scene,
    interaction,
    dispose: () => {
      unwatchSelection();
      unsubscribe();
      tooltip.hide();
    },
  };
}

/**
 * Dev-only inspection handle.
 *
 * A WebGL scene has no DOM to read back, so without this there is no way to
 * check camera state or node counts from the console or from an automated
 * browser check. `import.meta.env.DEV` is statically false in a production
 * build, so the whole block is dropped by the bundler.
 */
function exposeDevHandle(
  scene: ThoughtMapScene,
  screen: SearchScreen,
  interaction: ThoughtMapInteractionController,
): void {
  if (!import.meta.env.DEV) {
    return;
  }
  (window as unknown as { __thoughtmap?: unknown }).__thoughtmap = {
    scene,
    screen,
    interaction,
  };
}

function updateFitResultsEnabled(enabled: boolean): void {
  // Both the desktop bar and the compact mobile controls carry this action.
  const buttons = document.querySelectorAll<HTMLButtonElement>(
    '[data-camera-action="fit-results"]',
  );
  for (const button of buttons) {
    button.disabled = !enabled;
  }
}

function bindCameraControls(
  getScene: () => ThoughtMapScene | null,
  getInteraction: () => ThoughtMapInteractionController | null,
  screen: SearchScreen,
): void {
  const containers = [
    document.getElementById("tm-camera-controls"),
    document.getElementById("tm-camera-compact"),
  ].filter((element): element is HTMLElement => element !== null);

  if (containers.length === 0) {
    return;
  }

  const handleClick = (event: Event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const scene = getScene();
    if (!scene) {
      return;
    }

    // Three distinct behaviours, not duplicates of each other:
    //   Reset Camera — back to the default angle *and* the fitted whole-map
    //                  framing adopted when the projection loaded.
    //   Fit All      — re-frame the whole map from wherever you are looking now.
    //   Fit Results  — frame only the current search results.
    const action = target.dataset["cameraAction"];
    if (action === "reset") {
      scene.resetCamera();
    } else if (action === "fit-all") {
      scene.fitAllNodes();
    } else if (action === "fit-results") {
      getInteraction()?.fitResults(screen.state.getState());
    }
  };

  for (const container of containers) {
    container.addEventListener("click", handleClick);
  }
}

function showFatal(message: string, error?: unknown): void {
  if (error !== undefined) {
    console.error("[ThoughtMap]", message, error);
  }

  const app = document.getElementById("app");
  if (!app) {
    return;
  }

  const panel = document.createElement("div");
  panel.className = "tm-fatal";

  const heading = document.createElement("h1");
  heading.textContent = "ThoughtMap could not start";

  const detail = document.createElement("p");
  detail.textContent = message;

  panel.append(heading, detail);
  app.replaceChildren(panel);
}

main();
