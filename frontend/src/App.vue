<template>
  <div class="app">
    <header v-if="!route.params.id">
      <div class="brand">
        <span class="brand-icon">🃏</span>
        <h1>Jass Turnier Verwaltung</h1>
      </div>
      <nav>
        <router-link to="/">Turnierübersicht</router-link>
      </nav>
    </header>
    <main>
      <router-view />
    </main>

    <ShortcutsHelp v-model:open="helpOpen" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useKeyboardShortcuts } from "./composables/useKeyboardShortcuts";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";

const route = useRoute();
const router = useRouter();

const helpOpen = ref(false);

useKeyboardShortcuts([
  {
    keys: "?",
    description: "Tastenkürzel-Hilfe anzeigen",
    group: "Allgemein",
    handler: () => { helpOpen.value = !helpOpen.value; },
  },
  {
    keys: "u",
    description: "Zurück zur Turnierübersicht",
    group: "Allgemein",
    when: () => !!route.params.id,
    handler: () => router.push("/"),
  },
]);
</script>

<style scoped>
header {
  background:
    radial-gradient(ellipse 80% 120% at 85% -20%, rgba(217, 154, 61, 0.18) 0%, transparent 55%),
    linear-gradient(135deg, #0f3b28, var(--color-primary-dark) 40%, var(--color-primary));
  color: white;
  padding: 1.6rem 2.5rem 0;
  box-shadow: var(--shadow-md);
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 3px solid var(--color-accent);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.1rem;
}

.brand-icon {
  font-size: 1.7rem;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: var(--radius-sm);
  width: 2.6rem;
  height: 2.6rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

header h1 {
  margin: 0;
  font-size: 1.5rem;
  color: white;
  font-weight: 600;
  letter-spacing: 0.02em;
}

nav {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

nav a {
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  font-size: 0.92rem;
  font-weight: 500;
  padding: 0.7rem 1rem;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  border-bottom: 3px solid transparent;
  transition: background 0.15s ease, color 0.15s ease;
}

nav a:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
}

nav a.router-link-exact-active {
  border-bottom-color: var(--color-accent);
  color: white;
  background: rgba(255, 255, 255, 0.1);
  font-weight: 600;
}

main {
  padding: 2.5rem clamp(1.25rem, 4vw, 4rem);
  width: 100%;
}
</style>
