import { test, expect } from "@playwright/test";
import { setupTournamentWithPlayers, startTournamentViaApi } from "./helpers";

test("Sitzplan: nach Start ist jeder Spieler genau einem Tisch pro Runde zugeordnet", async ({ page, request }) => {
  // 16 Spieler / 2 Runden: bestätigt lösbarer Fall (siehe bekannter Scheduling-Bug bei 8/12 Spielern).
  const { id } = await setupTournamentWithPlayers(request, {
    namePrefix: "Sitzplan-Test",
    players: 16,
    rounds: 2,
    numGroups: 1,
    tablesPerRow: 4,
  });
  await startTournamentViaApi(request, id);

  await page.goto(`/tournaments/${id}/sitzplan`);
  await expect(page.locator(".round-tabs .round-tab")).toHaveCount(2);

  const expectedNumbers = Array.from({ length: 16 }, (_, i) => String(i + 1)).sort();

  // Runde 1: 16 Spieler / 4 pro Tisch = 4 Tische, jede Spielernummer genau einmal sichtbar
  await expect(page.locator(".table-card")).toHaveCount(4);
  const numbersRound1 = await page.locator(".table-svg text").allTextContents();
  expect(numbersRound1.sort()).toEqual(expectedNumbers);

  // Runde 2 wechseln, gleiche Prüfung (kein Spieler fehlt, keiner doppelt an einem Tisch)
  await page.locator(".round-tab", { hasText: "Runde 2" }).click();
  await expect(page.locator(".table-card")).toHaveCount(4);
  const numbersRound2 = await page.locator(".table-svg text").allTextContents();
  expect(numbersRound2.sort()).toEqual(expectedNumbers);
});
