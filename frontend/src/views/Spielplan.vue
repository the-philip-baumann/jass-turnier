<template>
  <div>
    <h2>Spielplan</h2>

    <div v-if="tournament.status !== 'started'" class="empty-state">
      Das Turnier wurde noch nicht gestartet. Starte das Turnier, um den Spielplan zu sehen.
    </div>

    <div v-else-if="loading" class="empty-state">Lade Spielplan…</div>

    <div v-else-if="rounds.length === 0" class="empty-state">
      Kein Spielplan vorhanden.
    </div>

    <div v-else>
      <div class="round-tabs">
        <button
          v-for="r in rounds"
          :key="r.number"
          :class="['round-tab', { active: selectedRound === r.number }]"
          @click="selectedRound = r.number"
        >
          Runde {{ r.number }}
        </button>
      </div>

      <div class="tables-grid">
        <div
          v-for="game in currentRoundGames"
          :key="game.id"
          :class="['card', 'game-card', gameScore(game) ? 'game-card--scored' : 'game-card--open']"
          @click="openScoreModal(game)"
        >
          <div class="table-header">
            <span class="table-label">Tisch {{ game.table_number }}</span>
            <span class="group-badge">Gruppe {{ groupOf(game) }}</span>
          </div>
          <div class="teams">
            <div class="team">
              <span class="team-label">Team 1</span>
              <div v-for="r in team(game, 1)" :key="r.player_id" class="player-row">
                {{ playerName(r.player_id) }}
              </div>
            </div>
            <div class="vs-col">
              <div class="vs">vs</div>
              <div v-if="gameScore(game)" class="score-display">
                {{ gameScore(game) }}
              </div>
            </div>
            <div class="team">
              <span class="team-label">Team 2</span>
              <div v-for="r in team(game, 2)" :key="r.player_id" class="player-row">
                {{ playerName(r.player_id) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Score Modal -->
    <div v-if="modal.open" class="modal-backdrop" @click.self="closeModal">
      <div class="modal-box card">
        <h3>Score eintragen</h3>
        <p class="modal-subtitle">
          Tisch {{ modal.game?.table_number }} · Runde {{ selectedRound }}
        </p>
        <div class="modal-teams">
          <div class="modal-team">
            <div class="modal-team-label">Team 1</div>
            <div v-for="r in team(modal.game, 1)" :key="r.player_id" class="modal-player">
              {{ playerName(r.player_id) }}
            </div>
            <input
              v-model.number="modal.team1Score"
              type="number"
              min="0"
              class="score-input"
              placeholder="Punkte"
              @input="onScoreInput"
            />
          </div>
          <div class="modal-vs">:</div>
          <div class="modal-team">
            <div class="modal-team-label">Team 2</div>
            <div v-for="r in team(modal.game, 2)" :key="r.player_id" class="modal-player">
              {{ playerName(r.player_id) }}
            </div>
            <input
              v-model.number="modal.team2Score"
              type="number"
              min="0"
              class="score-input"
              placeholder="Punkte"
              @input="onScoreInput"
            />
          </div>
        </div>
        <div class="modal-sum" :class="{ valid: sumValid, invalid: modal.touched && !sumValid }">
          Summe: {{ scoreSum }} / {{ expectedSum }}
          <span v-if="sumValid"> ✓</span>
        </div>
        <p v-if="modal.error" class="modal-error">{{ modal.error }}</p>
        <div class="modal-actions">
          <button class="secondary" @click="closeModal">Abbrechen</button>
          <button :disabled="!sumValid || modal.saving" @click="saveScore">
            {{ modal.saving ? "Speichern…" : "Speichern" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import api from "../api/client";

const props = defineProps({
  id: { type: [String, Number], required: true },
  tournament: { type: Object, required: true },
});

const games = ref([]);
const loading = ref(false);
const selectedRound = ref(1);

const modal = ref({
  open: false,
  game: null,
  team1Score: null,
  team2Score: null,
  saving: false,
  error: "",
  touched: false,
});

const playerMap = computed(() => {
  const map = {};
  for (const p of props.tournament.players ?? []) {
    map[p.id] = p;
  }
  return map;
});

const expectedSum = computed(() => 157 * (props.tournament.anzahl_ansagen ?? 1));

const scoreSum = computed(() => {
  const a = Number(modal.value.team1Score) || 0;
  const b = Number(modal.value.team2Score) || 0;
  return a + b;
});

const sumValid = computed(() => scoreSum.value === expectedSum.value);

function playerName(playerId) {
  const p = playerMap.value[playerId];
  return p ? `${p.player_number} – ${p.name}` : `#${playerId}`;
}

function groupOf(game) {
  const pid = game.results?.[0]?.player_id;
  return pid ? (playerMap.value[pid]?.group_number ?? "?") : "?";
}

function team(game, teamNum) {
  return (game.results ?? []).filter((r) => r.team === teamNum);
}

function gameScore(game) {
  const t1 = team(game, 1);
  const t2 = team(game, 2);
  if (!t1.length || !t2.length) return null;
  const pts1 = t1[0]?.points ?? 0;
  const pts2 = t2[0]?.points ?? 0;
  if (pts1 === 0 && pts2 === 0) return null;
  return `${pts1} : ${pts2}`;
}

function openScoreModal(game) {
  const t1 = team(game, 1);
  const t2 = team(game, 2);
  modal.value = {
    open: true,
    game,
    team1Score: t1[0]?.points ?? null,
    team2Score: t2[0]?.points ?? null,
    saving: false,
    error: "",
    touched: false,
  };
}

function closeModal() {
  modal.value.open = false;
}

function onScoreInput() {
  modal.value.touched = true;
  modal.value.error = "";
}

async function saveScore() {
  if (!sumValid.value) return;
  modal.value.saving = true;
  modal.value.error = "";
  try {
    const res = await api.patch(
      `/tournaments/${props.id}/games/${modal.value.game.id}`,
      { team1_score: modal.value.team1Score, team2_score: modal.value.team2Score }
    );
    // Update local game data
    const idx = games.value.findIndex((g) => g.id === modal.value.game.id);
    if (idx !== -1) games.value[idx] = res.data;
    closeModal();
  } catch (e) {
    modal.value.error = e.response?.data?.detail ?? "Fehler beim Speichern.";
  } finally {
    modal.value.saving = false;
  }
}

const rounds = computed(() => {
  const map = {};
  for (const g of games.value) {
    if (!map[g.round_number]) map[g.round_number] = [];
    map[g.round_number].push(g);
  }
  return Object.keys(map)
    .map(Number)
    .sort((a, b) => a - b)
    .map((n) => ({
      number: n,
      games: map[n].slice().sort((a, b) => a.table_number - b.table_number),
    }));
});

const currentRoundGames = computed(() => {
  const r = rounds.value.find((r) => r.number === selectedRound.value);
  return r ? r.games : [];
});

async function load() {
  if (props.tournament.status !== "started") return;
  loading.value = true;
  try {
    const res = await api.get(`/tournaments/${props.id}/games`);
    games.value = res.data;
    selectedRound.value = rounds.value[0]?.number ?? 1;
  } finally {
    loading.value = false;
  }
}

watch(() => props.tournament.status, load);
onMounted(load);
</script>

<style scoped>
.round-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.round-tab {
  background: transparent;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  font-weight: 500;
  font-size: 0.88rem;
  padding: 0.4rem 0.9rem;
}

.round-tab:hover {
  background: var(--color-primary-light);
  color: var(--color-primary-dark);
}

.round-tab.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.tables-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}

.game-card {
  padding: 1rem 1.25rem;
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.1s, border-color 0.15s;
}

.game-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-1px);
}

.game-card--scored {
  border-left: 4px solid var(--color-primary);
  background: var(--color-primary-light);
}

.game-card--open {
  border-left: 4px solid var(--color-accent);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.table-label {
  font-weight: 700;
  color: var(--color-primary-dark);
}

.group-badge {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-primary-dark);
  background: var(--color-primary-light);
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
}

.teams {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.team {
  flex: 1;
}

.team-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.35rem;
}

.player-row {
  font-size: 0.9rem;
  padding: 0.2rem 0;
  border-bottom: 1px solid var(--color-border);
}

.player-row:last-child {
  border-bottom: none;
}

.vs-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 1.4rem;
  gap: 0.35rem;
}

.vs {
  font-weight: 700;
  color: var(--color-accent);
  font-size: 0.85rem;
}

.score-display {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-primary-dark);
  white-space: nowrap;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-box {
  width: min(480px, 92vw);
  padding: 1.75rem 2rem;
}

.modal-box h3 {
  margin: 0 0 0.2rem;
  font-size: 1.15rem;
}

.modal-subtitle {
  color: var(--color-text-muted);
  font-size: 0.88rem;
  margin: 0 0 1.25rem;
}

.modal-teams {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}

.modal-team {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.modal-team-label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin-bottom: 0.2rem;
}

.modal-player {
  font-size: 0.88rem;
  color: var(--color-text);
}

.score-input {
  width: 100%;
  margin-top: 0.6rem;
  font-size: 1.1rem;
  font-weight: 700;
  text-align: center;
  padding: 0.5rem;
}

.modal-vs {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--color-accent);
  padding-top: 2rem;
}

.modal-sum {
  font-size: 0.88rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: var(--color-text-muted);
}

.modal-sum.valid {
  color: var(--color-primary);
}

.modal-sum.invalid {
  color: var(--color-danger);
}

.modal-error {
  color: var(--color-danger);
  font-size: 0.88rem;
  font-weight: 500;
  margin-bottom: 0.75rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
</style>
