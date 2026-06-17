<template>
  <div v-if="tournament">
    <router-link to="/" class="back-link">&larr; Zurück zur Turnierübersicht</router-link>
    <div class="workspace-header">
      <div>
        <h2>{{ tournament.name }}</h2>
        <p class="subtitle">📅 {{ tournament.date }}</p>
      </div>
      <div class="header-actions">
        <span v-if="tournament.status === 'started'" class="status-badge">🟢 Turnier gestartet</span>
        <button v-else @click="startTournament" :disabled="starting">
          {{ starting ? "Wird gestartet…" : "▶ Turnier starten" }}
        </button>
      </div>
    </div>
    <p v-if="startError" class="error">{{ startError }}</p>

    <nav class="tabs">
      <router-link :to="`/tournaments/${id}/spielplan`">📋 Spielplan</router-link>
      <router-link :to="`/tournaments/${id}/sitzplan`">🪑 Sitzplan</router-link>
      <router-link :to="`/tournaments/${id}/spielerverwaltung`">👥 Spielerverwaltung</router-link>
      <router-link :to="`/tournaments/${id}/konfiguration`">⚙️ Konfiguration</router-link>
      <router-link v-if="tournament.status === 'started'" :to="`/tournaments/${id}/spielstand`">🏆 Spielstand</router-link>
    </nav>

    <div class="tab-content">
      <router-view :id="id" :tournament="tournament" @changed="load" />
    </div>
  </div>
  <div v-else-if="notFound" class="empty-state">
    Turnier wurde nicht gefunden.
    <router-link to="/">Zurück zur Übersicht</router-link>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";
import api from "../api/client";

const props = defineProps({ id: { type: [String, Number], required: true } });

const tournament = ref(null);
const notFound = ref(false);
const starting = ref(false);
const startError = ref("");

async function load() {
  notFound.value = false;
  try {
    const res = await api.get(`/tournaments/${props.id}`);
    tournament.value = res.data;
  } catch (e) {
    tournament.value = null;
    notFound.value = true;
  }
}

async function startTournament() {
  starting.value = true;
  startError.value = "";
  try {
    const res = await api.post(`/tournaments/${props.id}/start`);
    tournament.value = res.data;
  } catch (e) {
    startError.value = e.response?.data?.detail ?? "Turnier konnte nicht gestartet werden.";
  } finally {
    starting.value = false;
  }
}

watch(() => props.id, load);
onMounted(load);
</script>

<style scoped>
.back-link {
  display: inline-block;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
  text-decoration: none;
}

.workspace-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.subtitle {
  color: var(--color-text-muted);
  margin-top: -0.5rem;
}

.header-actions {
  flex-shrink: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
  color: var(--color-primary-dark);
  background: var(--color-primary-light);
  padding: 0.6rem 1rem;
  border-radius: var(--radius-md);
}

.error {
  color: #c0392b;
  font-weight: 500;
  margin: -0.5rem 0 1rem;
}

.tabs {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 1.5rem;
}

.tabs a {
  text-decoration: none;
  color: var(--color-text-muted);
  font-weight: 500;
  padding: 0.7rem 1rem;
  border-bottom: 3px solid transparent;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.tabs a:hover {
  color: var(--color-primary-dark);
}

.tabs a.router-link-active {
  color: var(--color-primary-dark);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}
</style>
