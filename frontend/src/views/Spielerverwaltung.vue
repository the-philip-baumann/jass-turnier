<template>
  <div>
    <h3>Spieler</h3>

    <template v-if="tournament.status !== 'started'">
      <template v-if="!tournament.players_imported">
        <div class="card form-card import-card">
          <div class="field">
            <label>Anmeldeliste (CSV)</label>
            <input ref="fileInput" type="file" accept=".csv,text/csv" @change="onFileSelected" />
          </div>
          <button type="button" :disabled="!selectedFile || importing" @click="importCsv">
            {{ importing ? "Importiere…" : "CSV importieren" }}
          </button>
        </div>
        <p v-if="importError" class="error">{{ importError }}</p>
      </template>
      <p v-else class="success">Anmeldeliste wurde bereits importiert.</p>
      <p v-if="importSummary" class="success">{{ importSummary }}</p>

      <form @submit.prevent="addPlayer" class="card form-card">
        <div class="field number-field">
          <label>Nummer</label>
          <input v-model.number="newNumber" type="number" min="1" required />
        </div>
        <div class="field name-field">
          <label>Vorname</label>
          <input v-model="newVorname" placeholder="Vorname" required />
        </div>
        <div class="field name-field">
          <label>Nachname</label>
          <input v-model="newNachname" placeholder="Nachname" required />
        </div>
        <button type="submit">+ Hinzufügen</button>
      </form>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="registeredError" class="error">{{ registeredError }}</p>
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
              <span v-if="p.registered" class="registered-badge" title="Hat sich angemeldet">✓ angemeldet</span>
            </span>
          </li>
        </ul>
      </div>
    </template>

    <!-- Before start: flat list with edit -->
    <template v-else>
      <ul class="card-list">
        <li v-for="p in sortedPlayers" :key="p.id" class="card player-card">
          <span class="player-number">{{ p.player_number }}</span>
          <template v-if="editingId === p.id">
            <form @submit.prevent="saveEdit(p.id)" class="edit-form">
              <input v-model="editName" required autofocus />
              <button type="submit">Speichern</button>
              <button type="button" class="ghost" @click="cancelEdit">Abbrechen</button>
            </form>
          </template>
          <template v-else>
            <span class="player-name" @click="startEdit(p)">{{ p.name }}</span>
          </template>
          <label class="registered-toggle" :class="{ on: p.registered }" @click.stop>
            <input
              type="checkbox"
              :checked="p.registered"
              @change="saveRegistered(p, $event.target.checked)"
            />
            <span class="toggle-track"><span class="toggle-thumb"></span></span>
            <span class="toggle-label">angemeldet</span>
          </label>
          <button class="danger" @click="removePlayer(p.id)">Entfernen</button>
        </li>
      </ul>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import api from "../api/client";

const props = defineProps({
  id: { type: [String, Number], required: true },
  tournament: { type: Object, required: true },
});
const emit = defineEmits(["changed"]);

const newVorname = ref("");
const newNachname = ref("");
const newNumber = ref(null);
const error = ref("");
const editingId = ref(null);
const editName = ref("");
const registeredError = ref("");

const nextNumber = computed(
  () => Math.max(0, ...props.tournament.players.map((p) => p.player_number)) + 1
);

// Pre-fill the number field with the next free number whenever the player list
// changes (e.g. after adding a player) — the organizer can still overwrite it.
watch(nextNumber, (value) => { newNumber.value = value; }, { immediate: true });

const fileInput = ref(null);
const selectedFile = ref(null);
const importing = ref(false);
const importError = ref("");
const importSummary = ref("");

function onFileSelected(e) {
  selectedFile.value = e.target.files[0] ?? null;
  importError.value = "";
  importSummary.value = "";
}

async function importCsv() {
  if (!selectedFile.value) return;
  importing.value = true;
  importError.value = "";
  importSummary.value = "";
  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);
    const { data } = await api.post(`/tournaments/${props.id}/players/import`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    importSummary.value =
      `${data.created.length} Spieler importiert` +
      (data.skipped_duplicates ? `, ${data.skipped_duplicates} Duplikate übersprungen` : "") +
      (data.skipped_invalid ? `, ${data.skipped_invalid} ungültige Zeilen übersprungen` : "") +
      ".";
    selectedFile.value = null;
    if (fileInput.value) fileInput.value.value = "";
    emit("changed");
  } catch (e) {
    importError.value = e.response?.data?.detail ?? "CSV konnte nicht importiert werden.";
  } finally {
    importing.value = false;
  }
}

const sortedPlayers = computed(() =>
  [...props.tournament.players].sort((a, b) => a.player_number - b.player_number)
);

const groups = computed(() => {
  const map = {};
  // No-shows (registered === false) never get a group assigned when the
  // tournament starts, so they're naturally excluded here.
  for (const p of props.tournament.players) {
    if (p.group_number == null) continue;
    const g = p.group_number;
    if (!map[g]) map[g] = { number: g, players: [] };
    map[g].players.push(p);
  }
  const result = Object.values(map).sort((a, b) => a.number - b.number);
  for (const group of result) {
    group.players.sort((a, b) => a.player_number - b.player_number);
  }
  return result;
});

async function addPlayer() {
  error.value = "";
  try {
    await api.post(`/tournaments/${props.id}/players`, {
      vorname: newVorname.value,
      nachname: newNachname.value,
      player_number: newNumber.value,
    });
    newVorname.value = "";
    newNachname.value = "";
    emit("changed");
  } catch (e) {
    error.value = e.response?.data?.detail ?? "Spieler konnte nicht angelegt werden.";
  }
}

function startEdit(player) {
  editingId.value = player.id;
  editName.value = player.name;
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
    });
    editingId.value = null;
    emit("changed");
  } catch (e) {
    error.value = e.response?.data?.detail ?? "Spieler konnte nicht aktualisiert werden.";
  }
}

async function saveRegistered(player, registered) {
  registeredError.value = "";
  try {
    await api.patch(`/tournaments/${props.id}/players/${player.id}/registered`, {
      registered,
    });
    emit("changed");
  } catch (e) {
    registeredError.value = e.response?.data?.detail ?? "Anmeldestatus konnte nicht gespeichert werden.";
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
.name-field input { min-width: 10rem; }

.error {
  color: #c0392b;
  font-weight: 500;
  margin: 0 0 1rem;
}

.success {
  color: #1e7e34;
  font-weight: 500;
  margin: 0 0 1rem;
}

.import-card {
  align-items: flex-end;
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
  display: grid;
  grid-template-columns: 2.6rem 1fr 7.5rem 6.5rem;
  align-items: center;
  gap: 0.85rem;
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

.registered-badge {
  font-size: 0.75rem;
  font-weight: 600;
  color: #1e7e34;
  background: #e6f4ea;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.registered-toggle {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-muted);
  cursor: pointer;
  user-select: none;
}

.registered-toggle input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.toggle-track {
  position: relative;
  display: inline-block;
  width: 2.4rem;
  height: 1.35rem;
  border-radius: 999px;
  background: #d9dde2;
  transition: background 0.18s ease;
  flex-shrink: 0;
}

.toggle-thumb {
  position: absolute;
  top: 0.15rem;
  left: 0.15rem;
  width: 1.05rem;
  height: 1.05rem;
  border-radius: 50%;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  transition: transform 0.18s ease;
}

.registered-toggle.on .toggle-track {
  background: #2e9e5b;
}

.registered-toggle.on .toggle-thumb {
  transform: translateX(1.05rem);
}

.registered-toggle:focus-within .toggle-track {
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.registered-toggle.on .toggle-label {
  color: #1e7e34;
}

.toggle-label {
  transition: color 0.18s ease;
}

.player-name {
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-sm);
  padding: 0.2rem 0.4rem;
  margin: -0.2rem -0.4rem;
  transition: background 0.12s ease;
}

.player-name:hover {
  background: var(--color-primary-light);
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
