/**
 * Double tap: the second press within this long of the first release
 * (Android's DOUBLE_TAP_TIMEOUT).
 *
 * Shared by the map's gesture handling and the screen layout, which must not
 * move under a finger that may still be tapping. Kept apart from both so the
 * layout code does not pull the 3D modules into the first download.
 */
export const DOUBLE_TAP_MS = 300;
