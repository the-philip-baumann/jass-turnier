<template>
  <div>
    <h3>Spieler</h3>

    <template v-if="tournament.status !== 'started'">
      <form @submit.prevent="addPlayer" class="card form-card">
        <div class="field number-field">
          <label>Nummer</label>
          <input v-model.number="newNumber" type="number" min="1" placeholder="Nr." required />
        </div>
        <div class="field name-field">
          <label>Name</label>
          <input v-model="newName" placeholder="Spielername" required />
        </div>
        <button type="submit">+ Hinzufügen</button>
      </form>
      <p v-if="error" class="error">{{ error }}</p>
    </template>

    <div v-if="tournament.players.length === 0" class="empty-state">
      Noch keine Spieler für dieses Turnier erfasst.
    </div>

    <!-- After start: grouped view -->
    <template v-if="tournament.status === 'started'">
      <div v-for="group in groups" :key="group.number" class="group-section">
        <h4 class="group-title">
          <span class="group-badge">Gruppe {{ group.number }}</span>
          <span class="group-count">{{ group.players.length }} Spieler</span>
        </h4>
        <ul class="card-list">
          <li v-for="p in group.players" :key="p.id" class="card player-card">
            <span class="player-info">
              <span class="player-number">{{ p.player_number }}</span>
              <span class="player-name">{{ p.name }}</span>
            </span>
          </li>
        </ul>
      </div>
    </template>

    <!-- Before start: flat list with edit -->
    <template v-else>
      <ul class="card-list">
        <li v-for="p in tournament.players" :key="p.id" class="card player-card">
          <template v-if="editingId === p.id">
            <form @submit.prevent="saveEdit(p.id)" class="edit-form">
              <input v-model.number="editNumber" type="number" min="1" required />
              <input v-model="editName" required />
              <button type="submit">Speichern</button>
              <button type="button" class="ghost" @click="cancelEdit">Abbrechen</button>
            </form>
          </template>
          <template v-else>
            <span class="player-info" @click="startEdit(p)">
              <span class="player-number">{{ p.player_number }}</span>
              <span class="player-name">{{ p.name }}</span>
            </span>
            <button class="danger" @click="removePlayer(p.id)">Entfernen</button>
          </template>
        </li>
      </ul>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import api from "../api/client";

const props = defineProps({
  id: { type: [String, Number], required: true },
  tournament: { type: Object, required: true },
});
const emit = defineEmits(["changed"]);

const newName = ref("");
const newNumber = ref(null);
const error = ref("");
const editingId = ref(null);
const editName = ref("");
const editNumber = ref(null);

const groups = computed(() => {
  const map = {};
  for (const p of props.tournament.players) {
    const g = p.group_number ?? 0;
    if (!map[g]) map[g] = { number: g, players: [] };
    map[g].players.push(p);
  }
  return Object.values(map).sort((a, b) => a.number - b.number);
});

async function addPlayer() {
  error.value = "";
  try {
    await api.post(`/tournaments/${props.id}/players`, {
      name: newName.value,
      player_number: newNumber.value,
    });
    newName.value = "";
    newNumber.value = null;
    emit("changed");
  } catch (e) {
    error.value = e.response?.data?.detail ?? "Spieler konnte nicht angelegt werden.";
  }
}

function startEdit(player) {
  editingId.value = player.id;
  editName.value = player.name;
  editNumber.value = player.player_number;
  error.value = "";
}

function cancelEdit() {
  editingId.value = null;
}

async function saveEdit(playerId) {
  error.value = "";
  try {
    await api.patch(`/tournaments/${props.id}/players/${playerId}`, {
      name: editName.value,
      player_number: editNumber.value,
    });
    editingId.value = null;
    emit("changed");
  } catch (e) {
    error.value = e.response?.data?.detail ?? "Spieler konnte nicht aktualisiert werden.";
  }
}

async function removePlayer(playerId) {
  await api.delete(`/tournaments/${props.id}/players/${playerId}`);
  emit("changed");
}
</script>

<style scoped>
.form-card {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
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

.number-field input { width: 5rem; }
.name-field input { min-width: 12rem; }

.error {
  color: #c0392b;
  font-weight: 500;
  margin: 0 0 1rem;
}

.group-section {
  margin-bottom: 1.75rem;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0 0 0.75rem;
}

.group-badge {
  background: var(--color-primary);
  color: white;
  font-size: 0.85rem;
  font-weight: 700;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
}

.group-count {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  font-weight: 400;
}

.card-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.player-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.25rem;
}

.player-info {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  cursor: pointer;
  border-radius: var(--radius-sm);
  padding: 0.2rem 0.4rem;
  margin: -0.2rem -0.4rem;
  transition: background 0.12s ease;
}

.player-info:hover {
  background: var(--color-primary-light);
}

.player-number {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary-dark);
  font-weight: 700;
  font-size: 0.9rem;
}

.player-name {
  font-weight: 500;
}

.edit-form {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex: 1;
}

.edit-form input[type="number"] { width: 4.5rem; }
.edit-form input:not([type="number"]) { flex: 1; }

.ghost {
  background: transparent;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}
</style>
