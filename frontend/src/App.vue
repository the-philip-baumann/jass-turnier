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
  </div>
</template>

<script setup>
import { useRoute } from "vue-router";

const route = useRoute();
</script>

<style scoped>
header {
  background: linear-gradient(135deg, var(--color-primary-dark), var(--color-primary));
  color: white;
  padding: 1.5rem 2.5rem 0;
  box-shadow: var(--shadow-md);
  position: sticky;
  top: 0;
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 1.1rem;
}

.brand-icon {
  font-size: 1.6rem;
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
  padding: 2.5rem;
  max-width: 980px;
  margin: 0 auto;
}
</style>
