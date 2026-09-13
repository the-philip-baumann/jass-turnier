<template>
  <div>
    <div class="view-header">
      <h3>Sponsoren</h3>
      <button v-if="isReadOnly && sponsors.length > 0" class="play-btn" @click="startShow">
        ▶ Sponsoren-Show
      </button>
    </div>

    <template v-if="!isReadOnly">
      <form @submit.prevent="addSponsor" class="card form-card">
        <div class="field name-field">
          <label>Name</label>
          <input v-model="newName" placeholder="Sponsorname" required />
        </div>
        <div class="field logo-field">
          <label>Logo</label>
          <input ref="fileInput" type="file" accept="image/*" @change="onFileChange" required />
        </div>
        <button type="submit" :disabled="saving">
          {{ saving ? "Wird gespeichert…" : "+ Hinzufügen" }}
        </button>
      </form>
      <p v-if="error" class="error">{{ error }}</p>
    </template>

    <div v-if="sponsors.length === 0" class="empty-state">
      Noch keine Sponsoren für dieses Turnier erfasst.
    </div>

    <!-- After start: read-only preview grid; the real slideshow runs full-screen -->
    <div v-else-if="isReadOnly" class="sponsor-grid">
      <div v-for="s in sponsors" :key="s.id" class="card sponsor-tile">
        <img class="sponsor-tile-logo" :src="logoUrl(s)" :alt="`Logo von ${s.name}`" />
        <span class="sponsor-tile-name">{{ s.name }}</span>
      </div>
    </div>

    <!-- Before start: manageable list -->
    <ul v-else class="card-list">
      <li v-for="s in sponsors" :key="s.id" class="card sponsor-card">
        <img class="sponsor-logo" :src="logoUrl(s)" :alt="`Logo von ${s.name}`" />
        <span class="sponsor-name">{{ s.name }}</span>
        <button class="danger" @click="removeSponsor(s.id)">Entfernen</button>
      </li>
    </ul>

    <!-- Full-screen slideshow -->
    <Teleport to="body">
      <div
        v-if="showActive"
        ref="overlayEl"
        class="show-overlay"
        tabindex="0"
        @keydown.right.prevent="next"
        @keydown.left.prevent="prev"
        @keydown.space.prevent="togglePlay"
        @keydown.escape.prevent="endShow"
      >
        <div class="show-hdr">
          <span class="show-logo">🤝 Sponsoren</span>
          <div class="show-dots">
            <button
              v-for="(s, i) in sponsors"
              :key="s.id"
              type="button"
              class="dot"
              :class="{ 'dot--active': i === activeIndex }"
              :aria-label="`Zu ${s.name} wechseln`"
              @click="goTo(i)"
            ></button>
          </div>
          <div class="show-controls">
            <button
              type="button"
              class="btn-icon"
              @click="togglePlay"
              :aria-label="playing ? 'Pause' : 'Weiter automatisch'"
            >
              {{ playing ? "⏸" : "▶" }}
            </button>
            <button type="button" class="btn-close" @click="endShow" aria-label="Show schliessen">
              ✕
            </button>
          </div>
        </div>

        <Transition name="stg" mode="out-in">
          <div v-if="currentSponsor" :key="activeIndex" class="show-stage">
            <div class="logo-card">
              <img :src="logoUrl(currentSponsor)" :alt="`Logo von ${currentSponsor.name}`" />
            </div>
            <p class="show-name">{{ currentSponsor.name }}</p>
          </div>
        </Transition>

        <div v-if="sponsors.length > 1" class="show-progress">
          <div
            :key="`${activeIndex}-${resumeTick}`"
            class="show-progress-fill"
            :class="{ paused: !playing }"
            :style="{ animationDuration: `${SLIDE_INTERVAL_MS}ms` }"
          ></div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import api from "../api/client";
import { useKeyboardShortcuts } from "../composables/useKeyboardShortcuts";

const props = defineProps({
  id: { type: [String, Number], required: true },
  tournament: { type: Object, required: true },
});

const SLIDE_INTERVAL_MS = 5000;

const sponsors = ref([]);
const newName = ref("");
const newLogo = ref(null);
const fileInput = ref(null);
const error = ref("");
const saving = ref(false);

const isReadOnly = computed(() => props.tournament.status === "started");

function logoUrl(sponsor) {
  return `/api/tournaments/${props.id}/sponsors/${sponsor.id}/logo`;
}

function onFileChange(event) {
  newLogo.value = event.target.files[0] ?? null;
}

async function loadSponsors() {
  try {
    const res = await api.get(`/tournaments/${props.id}/sponsors`);
    sponsors.value = res.data;
    if (activeIndex.value >= sponsors.value.length) activeIndex.value = 0;
    if (sponsors.value.length === 0) endShow();
  } catch (e) {
    error.value = "Sponsoren konnten nicht geladen werden.";
  }
}

async function addSponsor() {
  error.value = "";
  if (!newLogo.value) {
    error.value = "Bitte ein Logo auswählen.";
    return;
  }
  saving.value = true;
  try {
    const formData = new FormData();
    formData.append("name", newName.value);
    formData.append("logo", newLogo.value);
    await api.post(`/tournaments/${props.id}/sponsors`, formData);
    newName.value = "";
    newLogo.value = null;
    if (fileInput.value) fileInput.value.value = "";
    await loadSponsors();
  } catch (e) {
    error.value = e.response?.data?.detail ?? "Sponsor konnte nicht angelegt werden.";
  } finally {
    saving.value = false;
  }
}

async function removeSponsor(sponsorId) {
  await api.delete(`/tournaments/${props.id}/sponsors/${sponsorId}`);
  await loadSponsors();
}

watch(() => props.id, loadSponsors);
onMounted(loadSponsors);

// ── Full-screen slideshow ──────────────────────────────────────────────────
const showActive = ref(false);
const activeIndex = ref(0);
const playing = ref(true);
const resumeTick = ref(0);
const overlayEl = ref(null);
let timer = null;

const currentSponsor = computed(() => sponsors.value[activeIndex.value] ?? null);

function clearTimer() {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
}

function scheduleAdvance() {
  clearTimer();
  if (showActive.value && playing.value && sponsors.value.length > 1) {
    timer = setTimeout(() => {
      activeIndex.value = (activeIndex.value + 1) % sponsors.value.length;
    }, SLIDE_INTERVAL_MS);
  }
}

function startShow() {
  if (!sponsors.value.length) return;
  activeIndex.value = 0;
  playing.value = true;
  showActive.value = true;
  nextTick(() => overlayEl.value?.focus());
}

function endShow() {
  showActive.value = false;
  clearTimer();
}

function togglePlay() {
  playing.value = !playing.value;
  if (playing.value) resumeTick.value++;
}

function goTo(index) {
  activeIndex.value = index;
}

function next() {
  goTo((activeIndex.value + 1) % sponsors.value.length);
}

function prev() {
  goTo((activeIndex.value - 1 + sponsors.value.length) % sponsors.value.length);
}

watch(activeIndex, scheduleAdvance);
watch(playing, scheduleAdvance);
watch(isReadOnly, (val) => {
  if (!val) endShow();
});
onUnmounted(clearTimer);

useKeyboardShortcuts([
  {
    keys: "p",
    description: "Sponsoren-Show starten",
    group: "Sponsoren",
    when: () => isReadOnly.value && !showActive.value && sponsors.value.length > 0,
    handler: startShow,
  },
]);
</script>

<style scoped>
.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.view-header h3 {
  margin: 0;
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

.name-field input {
  min-width: 12rem;
}

.logo-field input {
  padding: 0.5rem 0.6rem;
}

.error {
  color: #c0392b;
  font-weight: 500;
  margin: 0 0 1rem;
}

.card-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.sponsor-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.85rem 1.25rem;
}

.sponsor-logo {
  width: 3rem;
  height: 3rem;
  object-fit: contain;
  border-radius: var(--radius-sm);
  background: var(--color-primary-light);
  padding: 0.3rem;
  flex-shrink: 0;
}

.sponsor-name {
  font-weight: 500;
  flex: 1;
}

.sponsor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
  gap: 1rem;
}

.sponsor-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1rem;
  text-align: center;
}

.sponsor-tile-logo {
  width: 100%;
  height: 5rem;
  object-fit: contain;
}

.sponsor-tile-name {
  font-weight: 600;
}

/* ── Full-screen slideshow ───────────────────────────────────────────── */
.show-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: #0a1a0e;
  background-image: radial-gradient(
    circle at 1px 1px,
    rgba(255, 255, 255, 0.025) 1px,
    transparent 0
  );
  background-size: 36px 36px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  outline: none;
  overflow: hidden;
  font-family:
    "Segoe UI",
    system-ui,
    -apple-system,
    sans-serif;
}

.show-hdr {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9rem 1.6rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  flex-shrink: 0;
}

.show-logo {
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.38);
  flex-shrink: 0;
}

.show-dots {
  display: flex;
  gap: 7px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
}

.dot {
  width: 8px;
  height: 8px;
  padding: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  box-shadow: none;
  transition: all 0.3s ease;
}

.dot:hover:not(.dot--active) {
  background: rgba(255, 255, 255, 0.3);
  transform: none;
  box-shadow: none;
}

.dot--active {
  background: #d4a843;
  box-shadow: 0 0 10px #d4a84366;
  transform: scale(1.4);
}

.show-controls {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.btn-icon,
.btn-close {
  background: transparent;
  color: rgba(255, 255, 255, 0.38);
  border: 1px solid rgba(255, 255, 255, 0.14);
  padding: 0.28rem 0.65rem;
  font-size: 0.85rem;
  border-radius: var(--radius-sm);
  box-shadow: none;
  transition: all 0.15s;
}

.btn-icon:hover,
.btn-close:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.8);
  transform: none;
  box-shadow: none;
}

.show-stage {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.75rem;
  padding: 2rem 2.5rem;
}

.logo-card {
  width: min(520px, 80vw);
  height: min(320px, 46vh);
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.5rem;
}

.logo-card img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.show-name {
  margin: 0;
  font-family: "Georgia", serif;
  font-size: 1.9rem;
  font-weight: 700;
  color: #fff;
  text-align: center;
}

.show-progress {
  position: relative;
  z-index: 1;
  width: min(600px, 80%);
  height: 4px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  overflow: hidden;
  margin: 0 auto 2rem;
  flex-shrink: 0;
}

.show-progress-fill {
  height: 100%;
  width: 100%;
  background: #d4a843;
  transform: scaleX(0);
  transform-origin: left;
  animation: fillBar linear forwards;
}

.show-progress-fill.paused {
  animation-play-state: paused;
}

@keyframes fillBar {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}

.stg-enter-active {
  transition:
    opacity 0.4s ease,
    transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.stg-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}

.stg-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.stg-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}
</style>
