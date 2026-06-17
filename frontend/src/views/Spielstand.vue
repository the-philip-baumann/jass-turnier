<template>
  <div>
    <div class="view-header">
      <h3>Spielstand – Rangliste</h3>
      <button v-if="ranking.length && !loading" class="play-btn" @click="startPresentation">
        ▶ Präsentation
      </button>
    </div>

    <p v-if="loading" class="muted">Lade Spielstand…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <table v-else-if="ranking.length" class="ranking-table">
      <thead>
        <tr>
          <th class="rank-col">Rang</th>
          <th>Spieler</th>
          <th class="num-col">Punkte</th>
          <th class="num-col">Runden</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(entry, idx) in ranking"
          :key="entry.player.id"
          :class="{ 'top-row': idx < 3 }"
        >
          <td class="rank-col">
            <span v-if="idx === 0">🥇</span>
            <span v-else-if="idx === 1">🥈</span>
            <span v-else-if="idx === 2">🥉</span>
            <span v-else>{{ idx + 1 }}</span>
          </td>
          <td>
            <span class="player-num">#{{ entry.player.player_number }}</span>
            {{ entry.player.name }}
          </td>
          <td class="num-col points">{{ entry.totalPoints }}</td>
          <td class="num-col">{{ entry.roundsPlayed }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">Noch keine Spielresultate erfasst.</p>

    <!-- Presentation overlay (full-screen) -->
    <Teleport to="body">
      <div
        v-if="presentationMode"
        ref="overlayEl"
        class="pres-overlay"
        tabindex="0"
        @keydown.right.prevent="advance"
        @keydown.space.prevent="advance"
        @keydown.escape.prevent="endPresentation"
      >
        <canvas ref="confettiCanvas" class="confetti-canvas" />

        <!-- Header bar -->
        <div class="pres-hdr">
          <span class="pres-logo">🏆 Rangliste</span>
          <div class="pres-dots">
            <span
              v-for="(_, i) in presentationStages"
              :key="i"
              class="dot"
              :class="{ 'dot--active': i === currentStageIdx, 'dot--done': i < currentStageIdx }"
            />
          </div>
          <button class="btn-close" @click="endPresentation">✕</button>
        </div>

        <!-- Stage content with slide transition -->
        <Transition name="stg" mode="out-in">
          <div
            :key="currentStageIdx"
            class="pres-stage"
            :style="currentStage?.type === 'podium'
              ? { background: `radial-gradient(ellipse 70% 55% at 50% 52%, ${currentStage.glow}22 0%, transparent 68%)` }
              : undefined"
          >
            <!-- GROUP: list of players revealed with stagger -->
            <template v-if="currentStage?.type === 'group'">
              <h2 class="grp-title">{{ currentStage.label }}</h2>
              <div class="grp-list">
                <div
                  v-for="(entry, i) in currentStage.players"
                  :key="entry.player.id"
                  class="grp-row"
                  :style="{ animationDelay: `${i * 80}ms` }"
                >
                  <span class="gr-rank">{{ entry.rank }}</span>
                  <span class="gr-name">{{ entry.player.name }}</span>
                  <span class="gr-pts">{{ entry.totalPoints }}</span>
                </div>
              </div>
            </template>

            <!-- PODIUM: dramatic individual reveal -->
            <template v-else-if="currentStage?.type === 'podium'">
              <div
                class="pdm"
                :class="`pdm--${currentStage.place}`"
                :style="{ '--glow': currentStage.glow }"
              >
                <div class="pdm-medal">{{ currentStage.medal }}</div>
                <div class="pdm-rank">{{ currentStage.place }}. Platz</div>
                <div class="pdm-name">{{ currentStage.player.player.name }}</div>
                <div class="pdm-pts">{{ currentStage.player.totalPoints }} Punkte</div>
              </div>
            </template>
          </div>
        </Transition>

        <!-- Navigation -->
        <div class="pres-nav">
          <button
            v-if="currentStageIdx < presentationStages.length - 1"
            class="btn-next"
            @click="advance"
          >
            Weiter ▶
          </button>
          <button v-else class="btn-done" @click="endPresentation">
            ✓ Fertig
          </button>
          <span class="nav-hint">Pfeiltaste → oder Leertaste</span>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from "vue";
import api from "../api/client";

const props = defineProps({
  id: { type: [String, Number], required: true },
  tournament: { type: Object, required: true },
});

// ── Normal ranking ────────────────────────────────────────────────────────
const ranking = ref([]);
const loading = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [gamesRes] = await Promise.all([api.get(`/tournaments/${props.id}/games`)]);
    const games = gamesRes.data;
    const players = props.tournament.players;
    const statsMap = {};
    for (const player of players) {
      statsMap[player.id] = { player, totalPoints: 0, rounds: new Set() };
    }
    for (const game of games) {
      const scored = game.results.some((r) => r.points > 0);
      for (const result of game.results) {
        if (statsMap[result.player_id]) {
          statsMap[result.player_id].totalPoints += result.points;
          if (scored) statsMap[result.player_id].rounds.add(game.round_number);
        }
      }
    }
    ranking.value = Object.values(statsMap)
      .map((e) => ({ ...e, roundsPlayed: e.rounds.size }))
      .sort(
        (a, b) =>
          b.totalPoints - a.totalPoints ||
          a.player.player_number - b.player.player_number
      );
  } catch {
    error.value = "Spielstand konnte nicht geladen werden.";
  } finally {
    loading.value = false;
  }
}

watch(() => props.id, load);
onMounted(load);

// ── Presentation mode ─────────────────────────────────────────────────────
const presentationMode = ref(false);
const currentStageIdx = ref(0);
const overlayEl = ref(null);
const confettiCanvas = ref(null);
let stopConfetti = null;

const presentationStages = computed(() => {
  const total = ranking.value.length;
  if (!total) return [];
  const r = ranking.value.map((e, i) => ({ ...e, rank: i + 1 }));
  const stages = [];

  // Plätze N bis 21 (only if more than 20 players)
  if (total > 20) {
    stages.push({
      type: "group",
      players: r.slice(20).reverse(),
      label: `Plätze 21 – ${total}`,
    });
  }
  // Plätze 20 bis 11 (only if more than 10 players)
  if (total > 10) {
    const hi = Math.min(total, 20);
    stages.push({
      type: "group",
      players: r.slice(10, hi).reverse(),
      label: `Plätze 11 – ${hi}`,
    });
  }
  // Plätze 10 bis 4 (only if more than 3 players)
  if (total > 3) {
    const hi = Math.min(total, 10);
    stages.push({
      type: "group",
      players: r.slice(3, hi).reverse(),
      label: `Plätze 4 – ${hi}`,
    });
  }

  if (total >= 3) stages.push({ type: "podium", player: r[2], place: 3, medal: "🥉", glow: "#cd7f32" });
  if (total >= 2) stages.push({ type: "podium", player: r[1], place: 2, medal: "🥈", glow: "#a8a8a8" });
  stages.push({ type: "podium", player: r[0], place: 1, medal: "🥇", glow: "#ffd700" });

  return stages;
});

const currentStage = computed(() => presentationStages.value[currentStageIdx.value] ?? null);

function startPresentation() {
  currentStageIdx.value = 0;
  presentationMode.value = true;
  nextTick(() => overlayEl.value?.focus());
}

function endPresentation() {
  stopConfetti?.();
  stopConfetti = null;
  presentationMode.value = false;
}

function advance() {
  if (currentStageIdx.value < presentationStages.value.length - 1) {
    currentStageIdx.value++;
  }
}

watch(currentStageIdx, async (idx) => {
  stopConfetti?.();
  stopConfetti = null;
  if (presentationStages.value[idx]?.place === 1) {
    await nextTick();
    stopConfetti = launchConfetti(confettiCanvas.value);
  }
});

function launchConfetti(canvas) {
  if (!canvas) return null;
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  const ctx = canvas.getContext("2d");
  const palette = ["#ffd700", "#d4a843", "#ffffff", "#1e6b4f", "#cd7f32", "#8fb4ff", "#ff8888"];
  const pieces = Array.from({ length: 220 }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height - canvas.height,
    w: Math.random() * 14 + 6,
    h: Math.random() * 7 + 3,
    color: palette[Math.floor(Math.random() * palette.length)],
    vy: Math.random() * 3 + 1.5,
    vx: (Math.random() - 0.5) * 1.8,
    spin: (Math.random() - 0.5) * 0.13,
    angle: Math.random() * Math.PI * 2,
    alpha: Math.random() * 0.35 + 0.65,
  }));
  let active = true;
  (function draw() {
    if (!active) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const p of pieces) {
      ctx.save();
      ctx.globalAlpha = p.alpha;
      ctx.translate(p.x, p.y);
      ctx.rotate(p.angle);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
      p.x += p.vx;
      p.y += p.vy;
      p.angle += p.spin;
      if (p.y > canvas.height + 10) { p.y = -10; p.x = Math.random() * canvas.width; }
    }
    requestAnimationFrame(draw);
  })();
  const t = setTimeout(() => { active = false; }, 12000);
  return () => { active = false; clearTimeout(t); };
}
</script>

<style scoped>
/* ── Normal view ─────────────────────────────────────────────────────── */
h3 {
  margin-bottom: 0;
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.play-btn {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: white;
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  box-shadow: 0 2px 10px rgba(30, 107, 79, 0.25);
  transition: all 0.15s ease;
}

.play-btn:hover {
  background: linear-gradient(135deg, var(--color-primary-dark), #0d3325);
  box-shadow: 0 4px 16px rgba(30, 107, 79, 0.38);
  transform: translateY(-1px);
}

.muted { color: var(--color-text-muted); }
.error { color: #c0392b; font-weight: 500; }

.ranking-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}

.ranking-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid var(--color-border);
  color: var(--color-text-muted);
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.ranking-table td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
}

.ranking-table tbody tr:hover { background: var(--color-primary-light); }

.rank-col { width: 3.5rem; text-align: center; }
.num-col { width: 6rem; text-align: right; }

.points {
  font-weight: 700;
  color: var(--color-primary-dark);
}

.player-num {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  margin-right: 0.35rem;
}

.top-row td { background: var(--color-primary-light); }

/* ── Presentation overlay ────────────────────────────────────────────── */
.pres-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: #0a1a0e;
  background-image: radial-gradient(circle at 1px 1px, rgba(255, 255, 255, 0.025) 1px, transparent 0);
  background-size: 36px 36px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  outline: none;
  overflow: hidden;
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
}

.confetti-canvas {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

/* Header */
.pres-hdr {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.9rem 1.6rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  flex-shrink: 0;
}

.pres-logo {
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.38);
}

.pres-dots {
  display: flex;
  gap: 7px;
  align-items: center;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  transition: all 0.3s ease;
}

.dot--active {
  background: #d4a843;
  box-shadow: 0 0 10px #d4a84366;
  transform: scale(1.4);
}

.dot--done { background: rgba(212, 168, 67, 0.4); }

.btn-close {
  background: transparent;
  color: rgba(255, 255, 255, 0.38);
  border: 1px solid rgba(255, 255, 255, 0.14);
  padding: 0.28rem 0.65rem;
  font-size: 0.85rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-close:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.8);
}

/* Stage area */
.pres-stage {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 2.5rem;
  overflow-y: auto;
}

/* Group stage */
.grp-title {
  font-family: "Georgia", serif;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #d4a843;
  margin: 0 0 1.75rem;
  text-align: center;
}

.grp-list {
  width: 100%;
  max-width: 580px;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.grp-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.65rem 1.15rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  color: #fff;
  opacity: 0;
  animation: slideIn 0.38s ease forwards;
}

.gr-rank {
  width: 2.6rem;
  text-align: right;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.36);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.gr-name {
  flex: 1;
  font-size: 1.05rem;
  font-weight: 600;
}

.gr-pts {
  font-size: 0.92rem;
  font-weight: 600;
  color: #d4a843;
  font-variant-numeric: tabular-nums;
}

/* Podium stage */
.pdm {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.7rem;
  text-align: center;
}

.pdm-medal {
  font-size: 6.5rem;
  line-height: 1;
  animation: medalPop 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  filter: drop-shadow(0 0 28px var(--glow));
}

.pdm-rank {
  font-size: 0.92rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--glow);
  opacity: 0;
  animation: fadeUp 0.45s ease 0.55s forwards;
}

.pdm-name {
  font-size: 3.4rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.02em;
  line-height: 1.1;
  opacity: 0;
  animation: fadeUp 0.5s ease 0.75s forwards;
}

.pdm--1 .pdm-name {
  background: linear-gradient(135deg, #ffe566 0%, #d4a843 45%, #fff7c0 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.pdm-pts {
  font-size: 1.25rem;
  color: rgba(255, 255, 255, 0.42);
  opacity: 0;
  animation: fadeUp 0.4s ease 0.95s forwards;
}

/* Navigation */
.pres-nav {
  position: relative;
  z-index: 1;
  padding: 1.2rem 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.btn-next,
.btn-done {
  font-size: 1rem;
  font-weight: 700;
  padding: 0.7rem 2.5rem;
  border-radius: var(--radius-md);
  letter-spacing: 0.05em;
  transition: all 0.15s ease;
}

.btn-next {
  background: linear-gradient(135deg, #1e6b4f, #144d38);
  color: #fff;
  box-shadow: 0 4px 18px rgba(30, 107, 79, 0.45);
}

.btn-next:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(30, 107, 79, 0.58);
  background: linear-gradient(135deg, #248f68, #1e6b4f);
}

.btn-done {
  background: linear-gradient(135deg, #d4a843, #b88520);
  color: #fff;
  box-shadow: 0 4px 18px rgba(212, 168, 67, 0.4);
}

.btn-done:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(212, 168, 67, 0.52);
}

.nav-hint {
  font-size: 0.73rem;
  color: rgba(255, 255, 255, 0.18);
  margin: 0;
}

/* Stage slide transition */
.stg-enter-active {
  transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.stg-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.stg-enter-from {
  opacity: 0;
  transform: translateX(52px);
}

.stg-leave-to {
  opacity: 0;
  transform: translateX(-34px);
}

/* Keyframes */
@keyframes slideIn {
  from { opacity: 0; transform: translateX(55px); }
  to   { opacity: 1; transform: translateX(0); }
}

@keyframes medalPop {
  0%   { transform: scale(0.15) rotate(-22deg); opacity: 0; }
  60%  { transform: scale(1.18) rotate(7deg);  opacity: 1; }
  80%  { transform: scale(0.94) rotate(-3deg); }
  100% { transform: scale(1)    rotate(0deg);  }
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
