import { test, expect } from "@playwright/test";
import { addPlayerViaUi, fieldInput } from "./helpers";

test("Turnier anlegen, Konfiguration setzen, Spieler erfassen, in der Liste sehen", async ({ page }) => {
  await page.goto("/");

  const name = `E2E Turnier ${Date.now()}`;
  await page.getByPlaceholder("z.B. Schwingerfest Jass").fill(name);
  await page.locator('input[type="date"]').fill("2026-09-05");
  await page.getByRole("button", { name: "+ Turnier erstellen" }).click();

  const card = page.locator(".tournament-card", { hasText: name });
  await expect(card).toBeVisible();
  await card.getByRole("link").click();

  await expect(page).toHaveURL(/\/spielplan$/);

  // Konfiguration
  await page.getByRole("link", { name: "Konfiguration" }).click();
  await fieldInput(page, "Anzahl Runden").fill("3");
  await fieldInput(page, "Anzahl Gruppen").fill("1");
  await fieldInput(page, "Tische pro Reihe").fill("2");
  await page.getByRole("button", { name: "Speichern" }).click();
  await expect(page.getByText("✓ Gespeichert")).toBeVisible();

  // Spielerverwaltung
  await page.getByRole("link", { name: "Spielerverwaltung" }).click();
  await addPlayerViaUi(page, "Anna", "Muster");
  await addPlayerViaUi(page, "Beat", "Meier");
  await addPlayerViaUi(page, "Clara", "Suter");
  await addPlayerViaUi(page, "David", "Frei");

  await expect(page.locator(".player-card")).toHaveCount(4);

  // Zurück zur Liste: Turnier erscheint dort
  await page.goto("/");
  await expect(page.locator(".tournament-card", { hasText: name })).toBeVisible();
});
