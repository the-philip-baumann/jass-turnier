<template>
  <Teleport to="body">
    <div v-if="open" class="shortcuts-backdrop" @click.self="close">
      <div class="shortcuts-box card" role="dialog" aria-modal="true" aria-label="Tastenkürzel">
        <div class="shortcuts-header">
          <h3>⌨️ Tastenkürzel</h3>
          <button type="button" class="secondary shortcuts-close" @click="close">✕</button>
        </div>

        <div v-if="groups.length === 0" class="empty-state">
          Auf dieser Seite sind keine Tastenkürzel verfügbar.
        </div>

        <div v-for="group in groups" :key="group.name" class="shortcuts-group">
          <h4>{{ group.name }}</h4>
          <ul>
            <li v-for="s in group.items" :key="s.keys + s.description">
              <kbd>{{ formatKeys(s.keys) }}</kbd>
              <span>{{ s.description }}</span>
            </li>
          </ul>
        </div>

        <p class="shortcuts-hint">
          Kürzel wirken nicht, während du in einem Eingabefeld tippst (außer Esc). Mit
          <kbd>?</kbd> öffnest/schliesst du dieses Fenster.
        </p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from "vue";
import {
  useActiveShortcuts,
  useKeyboardShortcuts,
  formatKeys,
} from "../composables/useKeyboardShortcuts";

const props = defineProps({
  open: { type: Boolean, required: true },
});
const emit = defineEmits(["update:open"]);

function close() {
  emit("update:open", false);
}

useKeyboardShortcuts([
  {
    keys: "escape",
    description: "Dialog schliessen",
    allowInInput: true,
    when: () => props.open,
    handler: close,
  },
]);

const activeShortcuts = useActiveShortcuts();

const groups = computed(() => {
  const map = new Map();
  for (const s of activeShortcuts) {
    // The help overlay's own Escape binding isn't worth listing.
    if (s.description === "Dialog schliessen" && s.keys === "escape" && !s.group) continue;
    const groupName = s.group ?? "Allgemein";
    if (!map.has(groupName)) map.set(groupName, []);
    map.get(groupName).push(s);
  }
  return Array.from(map.entries()).map(([name, items]) => ({ name, items }));
});
</script>

<style scoped>
.shortcuts-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 24, 16, 0.5);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.shortcuts-box {
  width: min(480px, 92vw);
  max-height: 80vh;
  overflow-y: auto;
  padding: 1.5rem 1.75rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.shortcuts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.shortcuts-header h3 {
  margin: 0;
}

.shortcuts-close {
  padding: 0.35rem 0.65rem;
  font-size: 0.85rem;
}

.shortcuts-group {
  margin-bottom: 1.1rem;
}

.shortcuts-group h4 {
  margin: 0 0 0.5rem;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.shortcuts-group ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.shortcuts-group li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.92rem;
}

kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.75rem;
  padding: 0.15rem 0.5rem;
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-primary-dark);
  background: var(--color-primary-light);
  border: 1px solid rgba(30, 107, 79, 0.2);
  border-radius: var(--radius-sm);
}

.shortcuts-hint {
  margin: 1rem 0 0;
  font-size: 0.8rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}
</style>
