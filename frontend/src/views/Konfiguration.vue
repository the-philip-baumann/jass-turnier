<template>
  <div>
    <h3>Konfiguration</h3>
    <p v-if="tournament.status === 'started'" class="locked-hint">
      🔒 Turnier wurde gestartet – Konfiguration kann nicht mehr geändert werden.
    </p>
    <div v-if="tournament.status === 'started'" class="reset-section card">
      <div class="reset-info">
        <strong>Turnier zurücksetzen</strong>
        <p>Löscht den Spielplan und setzt das Turnier in den Setup-Modus zurück. Die Spieler bleiben erhalten.</p>
      </div>
      <button class="danger reset-btn" @click="confirmReset">Turnier zurücksetzen</button>
    </div>
    <p v-if="resetError" class="error">{{ resetError }}</p>
    <form @submit.prevent="save" class="card form-card">
      <div class="field">
        <label>Anzahl Runden</label>
        <input v-model.number="rounds" type="number" min="1" required :disabled="tournament.status === 'started'" />
      </div>
      <div class="field">
        <label>Anzahl Gruppen</label>
        <input v-model.number="numGroups" type="number" min="1" required :disabled="tournament.status === 'started'" />
      </div>
      <div class="field">
        <label>Tische pro Reihe</label>
        <input v-model.number="tablesPerRow" type="number" min="1" required />
      </div>
      <div class="field">
        <label>Anzahl Ansagen</label>
        <input v-model.number="anzahlAnsagen" type="number" min="1" required />
      </div>
      <button type="submit" :disabled="tournament.status === 'started'">Speichern</button>
      <span v-if="saved" class="saved-hint">✓ Gespeichert</span>
    </form>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import api from "../api/client";

const props = defineProps({
  id: { type: [String, Number], required: true },
  tournament: { type: Object, required: true },
});
const emit = defineEmits(["changed"]);

const rounds = ref(props.tournament.rounds);
const numGroups = ref(props.tournament.num_groups);
const tablesPerRow = ref(props.tournament.tables_per_row);
const anzahlAnsagen = ref(props.tournament.anzahl_ansagen ?? 1);
const saved = ref(false);
const resetError = ref("");

watch(
  () => props.tournament,
  (t) => {
    rounds.value = t.rounds;
    numGroups.value = t.num_groups;
    tablesPerRow.value = t.tables_per_row;
    anzahlAnsagen.value = t.anzahl_ansagen ?? 1;
  },
  { deep: true }
);

async function confirmReset() {
  if (!window.confirm("Spielplan wirklich löschen und Turnier zurücksetzen?")) return;
  resetError.value = "";
  try {
    await api.post(`/tournaments/${props.id}/reset`);
    emit("changed");
  } catch (e) {
    resetError.value = e.response?.data?.detail ?? "Reset fehlgeschlagen.";
  }
}

async function save() {
  await api.patch(`/tournaments/${props.id}`, {
    rounds: rounds.value,
    num_groups: numGroups.value,
    tables_per_row: tablesPerRow.value,
    anzahl_ansagen: anzahlAnsagen.value,
  });
  saved.value = true;
  setTimeout(() => (saved.value = false), 2000);
  emit("changed");
}
</script>

<style scoped>
.locked-hint {
  color: var(--color-text-muted);
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.form-card {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
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

.field input {
  width: 6rem;
}

.reset-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
  border-color: rgba(193, 84, 60, 0.3);
}

.reset-info strong {
  display: block;
  margin-bottom: 0.25rem;
  color: var(--color-danger);
}

.reset-info p {
  margin: 0;
  font-size: 0.88rem;
  color: var(--color-text-muted);
}

.reset-btn {
  flex-shrink: 0;
  padding: 0.5rem 1rem;
  font-size: 0.88rem;
}

.error {
  color: var(--color-danger);
  font-weight: 500;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.saved-hint {
  color: var(--color-primary);
  font-weight: 600;
  font-size: 0.9rem;
}
</style>
