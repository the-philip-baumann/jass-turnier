<template>
  <div>
    <h2>Turniere</h2>

    <form @submit.prevent="createTournament" class="card form-card">
      <div class="field">
        <label>Name des Turniers</label>
        <input v-model="name" placeholder="z.B. Schwingerfest Jass" required />
      </div>
      <div class="field">
        <label>Datum</label>
        <input v-model="date" type="date" required />
      </div>
      <button type="submit">+ Turnier erstellen</button>
    </form>

    <div v-if="tournaments.length === 0" class="empty-state">
      Noch keine Turniere angelegt. Lege oben dein erstes Turnier an.
    </div>

    <ul class="card-list">
      <li v-for="t in tournaments" :key="t.id" class="card tournament-card">
        <router-link :to="`/tournaments/${t.id}`" class="tournament-link">
          <span class="tournament-name">{{ t.name }}</span>
          <span class="tournament-date">📅 {{ t.date }}</span>
        </router-link>
        <button class="danger" @click="remove(t.id)">Löschen</button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import api from "../api/client";

const tournaments = ref([]);
const name = ref("");
const date = ref("");

async function load() {
  const res = await api.get("/tournaments");
  tournaments.value = res.data;
}

async function createTournament() {
  await api.post("/tournaments", { name: name.value, date: date.value });
  name.value = "";
  date.value = "";
  await load();
}

async function remove(id) {
  await api.delete(`/tournaments/${id}`);
  await load();
}

onMounted(load);
</script>

<style scoped>
.form-card {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 2rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.field label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.card-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.tournament-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.tournament-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.tournament-link {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  text-decoration: none;
  flex: 1;
}

.tournament-name {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--color-text);
}

.tournament-date {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.empty-state {
  text-align: center;
  color: var(--color-text-muted);
  padding: 2.5rem 1rem;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
}
</style>
