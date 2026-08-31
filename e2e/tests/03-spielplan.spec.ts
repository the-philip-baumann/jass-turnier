import { test, expect } from "@playwright/test";
import { setupTournamentWithPlayers, startTournamentViaApi } from "./helpers";

test("Spielplan: Struktur stimmt und Score kann eingetragen werden", async ({ page, request }) => {
  const { id } = await setupTournamentWithPlayers(request, {
    namePrefix: "Spielplan-Test",
    players: 16,
    rounds: 2,
    numGroups: 1,
    tablesPerRow: 4,
  });
  await startTournamentViaApi(request, id);

  await page.goto(`/tournaments/${id}/spielplan`);
  await expect(page.locator(".round-tabs .round-tab")).toHaveCount(2);
  await expect(page.locator(".game-card")).toHaveCount(4); // 16 Spieler / 4 pro Tisch

  // Jede Karte ist zunächst offen (kein Score)
  await expect(page.locator(".game-card--open")).toHaveCount(4);

  // Score für den ersten Tisch eintragen
  await page.locator(".game-card").first().click();
  await expect(page.locator(".modal-box")).toBeVisible();
  await page.locator(".modal-team").first().locator(".score-input").fill("87");
  await page.locator(".modal-team").nth(1).locator(".score-input").fill("70");
  await expect(page.locator(".modal-sum")).toContainText("157 / 157");
  await page.getByRole("button", { name: "Speichern" }).click();
  await expect(page.locator(".modal-box")).toBeHidden();

  // Karte zeigt jetzt den Score
  await expect(page.locator(".game-card--scored")).toHaveCount(1);
  await expect(page.locator(".game-card--scored .score-display")).toContainText("87");
  await expect(page.locator(".game-card--scored .score-display")).toContainText("70");
});

test("Spielplan: falsche Score-Summe wird abgelehnt", async ({ page, request }) => {
  const { id } = await setupTournamentWithPlayers(request, {
    namePrefix: "Spielplan-Validierung",
    players: 8,
    rounds: 1,
    numGroups: 1,
    tablesPerRow: 2,
  });
  await startTournamentViaApi(request, id);

  await page.goto(`/tournaments/${id}/spielplan`);
  await page.locator(".game-card").first().click();
  await page.locator(".modal-team").first().locator(".score-input").fill("100");
  await page.locator(".modal-team").nth(1).locator(".score-input").fill("100");
  await expect(page.locator(".modal-sum")).toContainText("200 / 157");
  await expect(page.getByRole("button", { name: "Speichern" })).toBeDisabled();
});
