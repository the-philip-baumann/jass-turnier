<template>
  <div>
    <h2>Sitzplan</h2>

    <div v-if="tournament.status !== 'started'" class="empty-state">
      Das Turnier wurde noch nicht gestartet.
    </div>

    <div v-else-if="loading" class="empty-state">Lade Sitzplan…</div>

    <div v-else-if="rounds.length === 0" class="empty-state">
      Kein Spielplan vorhanden.
    </div>

    <div v-else>
      <!-- Round tabs -->
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

      <!-- Tables for selected round -->
      <div class="tables-grid" :style="`grid-template-columns: repeat(${tournament.tables_per_row}, minmax(0, 1fr))`">
        <div
          v-for="game in currentRoundGames"
          :key="game.id"
          class="table-card card"
        >
          <div class="table-meta">
            <span class="table-label">Tisch {{ game.table_number }}</span>
            <span class="group-badge">Gruppe {{ groupOf(game) }}</span>
          </div>
          <svg
            :viewBox="`0 0 ${SVG_W} ${SVG_H}`"
            :width="SVG_W"
            :height="SVG_H"
            class="table-svg"
            xmlns="http://www.w3.org/2000/svg"
          >
            <!-- Table surface -->
            <rect
              :x="TABLE_X"
              :y="TABLE_Y"
              :width="TABLE_W"
              :height="TABLE_H"
              rx="10"
              fill="#2d6a4f"
              stroke="#1b4332"
              stroke-width="2"
            />
            <!-- Team legend lines -->
            <line
              :x1="SVG_W / 2 - 18" :y1="TABLE_Y + TABLE_H / 2"
              :x2="SVG_W / 2 + 18" :y2="TABLE_Y + TABLE_H / 2"
              stroke="rgba(255,255,255,0.25)" stroke-width="1" stroke-dasharray="3 3"
            />
            <line
              :x1="TABLE_X + TABLE_W / 2" :y1="SVG_H / 2 - 18"
              :x2="TABLE_X + TABLE_W / 2" :y2="SVG_H / 2 + 18"
              stroke="rgba(255,255,255,0.25)" stroke-width="1" stroke-dasharray="3 3"
            />

            <!-- Seats: North (Team1[0]), South (Team1[1]), West (Team2[0]), East (Team2[1]) -->
            <g v-for="seat in seatsFor(game)" :key="seat.pos">
              <!-- Seat circle -->
              <circle
                :cx="seat.cx" :cy="seat.cy"
                r="36"
                :fill="seat.team === 1 ? '#d99a3d' : '#3a86c8'"
                stroke="white"
                stroke-width="2"
              />
              <!-- Player number -->
              <text
                :x="seat.cx" :y="seat.cy + 1"
                text-anchor="middle"
                dominant-baseline="middle"
                font-size="24"
                font-weight="700"
                fill="white"
                font-family="Georgia, serif"
              >{{ seat.playerNumber }}</text>
            </g>
          </svg>
          <div class="legend">
            <span class="legend-item team1">■ Team 1</span>
            <span class="legend-item team2">■ Team 2</span>
          </div>
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

// SVG layout constants
const SVG_W = 320;
const SVG_H = 320;
const TABLE_W = 160;
const TABLE_H = 110;
const TABLE_X = (SVG_W - TABLE_W) / 2;
const TABLE_Y = (SVG_H - TABLE_H) / 2;
const CX = SVG_W / 2;
const CY = SVG_H / 2;

const SEAT_DEFS = [
  { pos: "N", team: 1, cx: CX,         cy: TABLE_Y - 44            },
  { pos: "S", team: 1, cx: CX,         cy: TABLE_Y + TABLE_H + 44  },
  { pos: "W", team: 2, cx: 42,         cy: CY                      },
  { pos: "E", team: 2, cx: SVG_W - 42, cy: CY                      },
];

const playerMap = computed(() => {
  const map = {};
  for (const p of props.tournament.players ?? []) map[p.id] = p;
  return map;
});

function groupOf(game) {
  const pid = game.results?.[0]?.player_id;
  return pid ? (playerMap.value[pid]?.group_number ?? "?") : "?";
}

function seatsFor(game) {
  const t1 = (game.results ?? []).filter((r) => r.team === 1);
  const t2 = (game.results ?? []).filter((r) => r.team === 2);
  const ordered = [t1[0], t1[1], t2[0], t2[1]];
  return SEAT_DEFS.map((def, i) => {
    const result = ordered[i];
    const player = result ? playerMap.value[result.player_id] : null;
    return {
      ...def,
      playerNumber: player?.player_number ?? "?",
    };
  });
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
    .map((n) => ({ number: n, games: map[n].slice().sort((a, b) => a.table_number - b.table_number) }));
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
  gap: 1.25rem;
}

.table-card {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.table-meta {
  display: flex;
  width: 100%;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
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

.table-svg {
  display: block;
}

.legend {
  display: flex;
  gap: 1rem;
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.legend-item.team1 { color: #d99a3d; font-weight: 600; }
.legend-item.team2 { color: #3a86c8; font-weight: 600; }
</style>
