import { onMounted, onUnmounted, reactive } from "vue";

// Central, module-level registry of all currently-active shortcuts so a
// help overlay can list "what works right now" regardless of which view
// registered it. Entries are added/removed as components mount/unmount.
const registry = reactive([]);

function isTypingTarget(el) {
  if (!el) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (el.isContentEditable) return true;
  return false;
}

function normalizeCombo(event) {
  const parts = [];
  if (event.ctrlKey || event.metaKey) parts.push("mod");
  if (event.altKey) parts.push("alt");
  if (event.shiftKey) parts.push("shift");
  parts.push(event.key.length === 1 ? event.key.toLowerCase() : event.key.toLowerCase());
  return parts.join("+");
}

/**
 * Register a set of keyboard shortcuts for the lifetime of the calling
 * component. Automatically ignores keystrokes while the user is typing in
 * an input/textarea/select/contenteditable field, unless a binding sets
 * `allowInInput: true` (e.g. Escape to close a dialog).
 *
 * @param {Array<{
 *   keys: string,            // e.g. "escape", "?", "mod+k", "1"
 *   description: string,     // shown in the help overlay
 *   handler: (event: KeyboardEvent) => void,
 *   allowInInput?: boolean,  // fire even while focus is in a text field
 *   when?: () => boolean,    // optional guard, checked before firing
 *   group?: string,          // section heading in the help overlay
 * }>} bindings
 */
export function useKeyboardShortcuts(bindings) {
  const entries = bindings.map((b) => ({ ...b }));

  function onKeydown(event) {
    const combo = normalizeCombo(event);
    for (const binding of entries) {
      if (binding.keys !== combo) continue;
      if (binding.when && !binding.when()) continue;
      if (!binding.allowInInput && isTypingTarget(event.target)) continue;
      binding.handler(event);
      return;
    }
  }

  onMounted(() => {
    window.addEventListener("keydown", onKeydown);
    registry.push(...entries);
  });

  onUnmounted(() => {
    window.removeEventListener("keydown", onKeydown);
    for (const entry of entries) {
      const idx = registry.indexOf(entry);
      if (idx !== -1) registry.splice(idx, 1);
    }
  });
}

/** Read-only view of every shortcut currently registered, for the help overlay. */
export function useActiveShortcuts() {
  return registry;
}

export const KEY_LABELS = {
  escape: "Esc",
  "mod+k": "⌘/Strg+K",
  "?": "?",
};

export function formatKeys(keys) {
  return KEY_LABELS[keys] ?? keys.replace("mod+", "⌘/Strg+").toUpperCase();
}
