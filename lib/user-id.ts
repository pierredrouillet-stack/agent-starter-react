const STORAGE_KEY = 'agent-user-id';

// Used when the browser refuses to keep the id, so it still lasts until the page closes.
let pageId: string | undefined;

/**
 * The anonymous id this browser sends to the agent so it can recognise the same person across
 * calls. Created once and kept in localStorage. Returns undefined when no id can be made, in which
 * case calls start without one.
 */
export function getUserId(): string | undefined {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved) return saved;
  } catch {
    // Storage is blocked or unavailable; fall through to an id for this page only.
  }
  if (pageId) return pageId;

  let id: string;
  try {
    id = window.crypto.randomUUID();
  } catch {
    return undefined; // randomUUID needs a secure context
  }
  pageId = id;
  try {
    window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Kept for this page only.
  }
  return id;
}
