import { test, expect } from "@playwright/test";
import { setupTournamentWithPlayers, startTournamentViaApi, API_BASE } from "./helpers";

/**
 * Grossturnier-Stresstest: 64 Spieler, 6 Runden, 16 Tische pro Runde.
 * Fixture-Setup (Turnier/Konfiguration/64 Spieler) läuft über die API, weil
 * das reines Vorbereiten von Testdaten ist — die eigentliche Prüfung
 * (Spielplan-Generierung, Score-Eintragung, finale Rangliste) läuft über die
 * echte UI, wie ein Organisator es am Turniertag erleben würde.
 */
test("Grossturnier: 64 Spieler, 6 Runden, Rangliste am Schluss korrekt", async ({ page, request }) => {
  test.setTimeout(180_000);

  const { id } = await setupTournamentWithPlayers(request, {
    namePrefix: "Grossturnier-64",
    players: 64,
    rounds: 6,
    numGroups: 1,
    tablesPerRow: 8,
  });
  const started = await startTournamentViaApi(request, id);
  expect(started.players).toHaveLength(64);

  // Sitzplan: 6 Runden à 16 Tische (64 / 4), jede Runde vollständig besetzt
  await page.goto(`/tournaments/${id}/sitzplan`);
  await expect(page.locator(".round-tabs .round-tab")).toHaveCount(6);
  const expectedNumbers = Array.from({ length: 64 }, (_, i) => String(i + 1)).sort();
  for (let r = 1; r <= 6; r++) {
    await page.locator(".round-tab", { hasText: `Runde ${r}` }).click();
    await expect(page.locator(".table-card")).toHaveCount(16);
    const numbers = await page.locator(".table-svg text").allTextContents();
    expect(numbers.sort()).toEqual(expectedNumbers);
  }

  // Spielplan: für jede der 6 Runden alle 16 Tische mit Score eintragen.
  // Team 1 gewinnt jeweils 90:67 (Summe 157), damit die Rangliste danach
  // eindeutig prüfbar ist: jeder Team-1-Sitz sammelt über alle Runden mehr
  // Punkte als jeder Team-2-Sitz.
  await page.goto(`/tournaments/${id}/spielplan`);
  let totalScored = 0;
  for (let r = 1; r <= 6; r++) {
    await page.locator(".round-tab", { hasText: `Runde ${r}` }).click();
    const cards = page.locator(".game-card");
    const count = await cards.count();
    expect(count).toBe(16);
    for (let i = 0; i < count; i++) {
      await cards.nth(i).click();
      await expect(page.locator(".modal-box")).toBeVisible();
      await page.locator(".modal-team").first().locator(".score-input").fill("90");
      await page.locator(".modal-team").nth(1).locator(".score-input").fill("67");
      await expect(page.locator(".modal-sum")).toContainText("157 / 157");
      await page.getByRole("button", { name: "Speichern" }).click();
      await expect(page.locator(".modal-box")).toBeHidden();
    }
    await expect(page.locator(".game-card--scored")).toHaveCount(count);
    totalScored += count;
  }
  expect(totalScored).toBe(96); // 16 Tische × 6 Runden

  // Cross-check über die API: jedes Spiel hat einen Score, keines wurde übersprungen.
  const gamesRes = await request.get(`${API_BASE}/tournaments/${id}/games`);
  const games = await gamesRes.json();
  expect(games).toHaveLength(96);
  for (const game of games) {
    expect(game.results).toHaveLength(4);
    const team1 = game.results.filter((r: any) => r.team === 1);
    const team2 = game.results.filter((r: any) => r.team === 2);
    expect(team1.every((r: any) => r.points === 90)).toBeTruthy();
    expect(team2.every((r: any) => r.points === 67)).toBeTruthy();
  }

  // Finale Rangliste: alle 64 Spieler gelistet, jeder hat 6 Runden gespielt,
  // und weil jedes Spiel identisch 90:67 ausging, hat jeder Spieler entweder
  // exakt 540 (6×90, immer Team 1) oder 402 (6×67, immer Team 2) Punkte —
  // das Round-Robin-Scheduling garantiert aber i.d.R. eine Mischung, daher
  // prüfen wir nur, dass die Summe je Spieler ein Vielfaches ist, das zur
  // Anzahl gespielter Runden passt.
  await page.goto(`/tournaments/${id}/spielstand`);
  await expect(page.locator(".ranking-table tbody tr")).toHaveCount(64);

  const rows = page.locator(".ranking-table tbody tr");
  const rowCount = await rows.count();
  const seenPlayerNumbers = new Set<string>();
  for (let i = 0; i < rowCount; i++) {
    const row = rows.nth(i);
    const points = Number(await row.locator("td.points").textContent());
    const rounds = Number(await row.locator("td.num-col").nth(1).textContent());
    const playerNum = (await row.locator(".player-num").textContent())?.trim() ?? "";
    seenPlayerNumbers.add(playerNum);

    expect(rounds).toBe(6);
    // Punkte pro gespielter Runde sind entweder 90 (Team 1) oder 67 (Team 2),
    // Gesamtsumme muss exakt auf eine Mischung dieser beiden Werte über 6 Runden aufgehen.
    let valid = false;
    for (let wins = 0; wins <= 6; wins++) {
      if (wins * 90 + (6 - wins) * 67 === points) {
        valid = true;
        break;
      }
    }
    expect(valid).toBeTruthy();
  }
  expect(seenPlayerNumbers.size).toBe(64);

  // Rangliste ist absteigend nach Punkten sortiert
  const allPoints = await page.locator(".ranking-table tbody tr td.points").allTextContents();
  const numericPoints = allPoints.map(Number);
  const sortedDesc = [...numericPoints].sort((a, b) => b - a);
  expect(numericPoints).toEqual(sortedDesc);
});
