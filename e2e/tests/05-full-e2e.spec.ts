import { test, expect } from "@playwright/test";
import { addPlayerViaUi, fieldInput } from "./helpers";

/**
 * Die "Generalprobe": kompletter Turnierablauf ausschliesslich über die UI,
 * wie ein Organisator ihn am Turniertag durchspielen würde.
 * Turnier anlegen → konfigurieren → Spieler erfassen → starten →
 * Sitzplan/Spielplan prüfen → alle Resultate eintragen → Rangliste verifizieren.
 */
test("Voller Turnierdurchlauf von der Anlage bis zur finalen Rangliste", async ({ page }) => {
  await page.goto("/");

  const name = `Generalprobe ${Date.now()}`;
  await page.getByPlaceholder("z.B. Schwingerfest Jass").fill(name);
  await page.locator('input[type="date"]').fill("2026-09-05");
  await page.getByRole("button", { name: "+ Turnier erstellen" }).click();
  await page.locator(".tournament-card", { hasText: name }).getByRole("link").click();

  // Konfiguration: 16 Spieler, 1 Gruppe, 2 Runden, 4 Tische pro Reihe
  // (16 Spieler/2 Runden ist ein bestätigt lösbarer Fall — bei 8 oder 12
  // Spielern lehnt das Backend 2 Runden aktuell wegen eines Scheduling-Bugs
  // immer ab, siehe separat gemeldeter Findung.)
  await page.getByRole("link", { name: "Konfiguration" }).click();
  await fieldInput(page, "Anzahl Runden").fill("2");
  await fieldInput(page, "Anzahl Gruppen").fill("1");
  await fieldInput(page, "Tische pro Reihe").fill("4");
  await page.getByRole("button", { name: "Speichern" }).click();
  await expect(page.getByText("✓ Gespeichert")).toBeVisible();

  // Spieler erfassen
  await page.getByRole("link", { name: "Spielerverwaltung" }).click();
  const players = [
    "Anna Muster", "Beat Meier", "Clara Suter", "David Frei",
    "Eva Roth", "Franz Keller", "Gina Huber", "Hans Baumann",
    "Ida Wyss", "Jon Steiner", "Kim Vogel", "Lisa Egger",
    "Marco Widmer", "Nina Graf", "Otto Brunner", "Petra Zimmermann",
  ];
  for (const full of players) {
    const [vorname, nachname] = full.split(" ");
    await addPlayerViaUi(page, vorname, nachname);
  }
  await expect(page.locator(".player-card")).toHaveCount(16);

  // Turnier starten
  await page.getByRole("button", { name: "▶ Turnier starten" }).click();
  await expect(page.getByText("🟢 Turnier gestartet")).toBeVisible();

  // Sitzplan hat 4 Tische pro Runde
  await page.getByRole("link", { name: "🪑 Sitzplan" }).click();
  await expect(page.locator(".round-tabs .round-tab")).toHaveCount(2);
  await expect(page.locator(".table-card")).toHaveCount(4);

  // Spielplan: für jede Runde alle Scores eintragen
  await page.getByRole("link", { name: "📋 Spielplan" }).click();
  for (const roundName of ["Runde 1", "Runde 2"]) {
    await page.locator(".round-tab", { hasText: roundName }).click();
    const cards = page.locator(".game-card");
    const count = await cards.count();
    for (let i = 0; i < count; i++) {
      await cards.nth(i).click();
      await page.locator(".modal-team").first().locator(".score-input").fill("90");
      await page.locator(".modal-team").nth(1).locator(".score-input").fill("67");
      await expect(page.locator(".modal-sum")).toContainText("157 / 157");
      await page.getByRole("button", { name: "Speichern" }).click();
      await expect(page.locator(".modal-box")).toBeHidden();
    }
    await expect(page.locator(".game-card--scored")).toHaveCount(count);
  }

  // Spielstand: Rangliste mit allen 16 Spielern, jeder hat 2 Runden gespielt
  await page.getByRole("link", { name: "🏆 Spielstand" }).click();
  await expect(page.locator(".ranking-table tbody tr")).toHaveCount(16);
  const roundsPlayed = await page.locator(".ranking-table tbody tr td.num-col").allTextContents();
  // jede zweite num-col Zelle ist "Runden" (Punkte, Runden, Punkte, Runden, ...)
  const roundsCells = roundsPlayed.filter((_, i) => i % 2 === 1);
  for (const cell of roundsCells) {
    expect(cell).toBe("2");
  }
});
