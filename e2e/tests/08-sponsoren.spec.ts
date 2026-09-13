import { test, expect } from "@playwright/test";
import { createTournament, addSponsorViaUi, addPlayerViaUi, API_BASE } from "./helpers";

test("Sponsoren erfassen und wieder entfernen, solange das Turnier nicht gestartet ist", async ({
  page,
  request,
}) => {
  const { id } = await createTournament(request, "Sponsoren-Verwaltung");
  await page.goto(`/tournaments/${id}/sponsoren`);

  await expect(page.getByText("Noch keine Sponsoren für dieses Turnier erfasst.")).toBeVisible();

  await addSponsorViaUi(page, "Bäckerei Muster");
  await addSponsorViaUi(page, "Garage Meier");
  await expect(page.locator(".sponsor-card")).toHaveCount(2);

  // Vor dem Start bleibt es eine Verwaltungsansicht: keine Show, dafür Entfernen möglich.
  await expect(page.getByRole("button", { name: "▶ Sponsoren-Show" })).toHaveCount(0);

  await page
    .locator(".sponsor-card", { hasText: "Garage Meier" })
    .getByRole("button", { name: "Entfernen" })
    .click();
  await expect(page.locator(".sponsor-card")).toHaveCount(1);
  await expect(page.getByText("Bäckerei Muster")).toBeVisible();
});

test("Nach Turnierstart wird die Sponsoren-Ansicht read-only", async ({ page, request }) => {
  const { id } = await createTournament(request, "Sponsoren-ReadOnly");
  await page.goto(`/tournaments/${id}/sponsoren`);
  await addSponsorViaUi(page, "Bäckerei Muster");

  await page.getByRole("link", { name: "Spielerverwaltung" }).click();
  await addPlayerViaUi(page, "Anna", "Muster");
  await addPlayerViaUi(page, "Beat", "Meier");
  await request.patch(`${API_BASE}/tournaments/${id}`, {
    data: { rounds: 1, num_groups: 1, tables_per_row: 2, anzahl_ansagen: 1 },
  });
  await page.getByRole("button", { name: "▶ Turnier starten" }).click();
  await expect(page.getByText("🟢 Turnier gestartet")).toBeVisible();

  await page.getByRole("link", { name: "Sponsoren" }).click();

  // Formular und "Entfernen"-Aktion sind weg, dafür gibt es die Vorschau + den Show-Knopf.
  await expect(page.getByPlaceholder("Sponsorname")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Entfernen" })).toHaveCount(0);
  await expect(page.locator(".sponsor-tile", { hasText: "Bäckerei Muster" })).toBeVisible();
  await expect(page.getByRole("button", { name: "▶ Sponsoren-Show" })).toBeVisible();
});

test("Sponsoren-Show: Vollbild-Slideshow lässt sich öffnen, durchblättern und schliessen", async ({
  page,
  request,
}) => {
  const { id } = await createTournament(request, "Sponsoren-Show");
  await page.goto(`/tournaments/${id}/sponsoren`);
  await addSponsorViaUi(page, "Bäckerei Muster");
  await addSponsorViaUi(page, "Garage Meier");

  await page.getByRole("link", { name: "Spielerverwaltung" }).click();
  await addPlayerViaUi(page, "Anna", "Muster");
  await addPlayerViaUi(page, "Beat", "Meier");
  await request.patch(`${API_BASE}/tournaments/${id}`, {
    data: { rounds: 1, num_groups: 1, tables_per_row: 2, anzahl_ansagen: 1 },
  });
  await page.getByRole("button", { name: "▶ Turnier starten" }).click();
  await expect(page.getByText("🟢 Turnier gestartet")).toBeVisible();

  await page.getByRole("link", { name: "Sponsoren" }).click();
  await page.getByRole("button", { name: "▶ Sponsoren-Show" }).click();

  const overlay = page.locator(".show-overlay");
  await expect(overlay).toBeVisible();
  await expect(overlay.locator(".show-name")).toHaveText("Bäckerei Muster");
  await expect(overlay.locator(".dot")).toHaveCount(2);

  // Per Klick auf den zweiten Punkt zum zweiten Sponsor springen.
  await overlay.locator(".dot").nth(1).click();
  await expect(overlay.locator(".show-name")).toHaveText("Garage Meier");

  // Mit der Pfeiltaste zurück zum ersten Sponsor.
  await overlay.press("ArrowLeft");
  await expect(overlay.locator(".show-name")).toHaveText("Bäckerei Muster");

  // Escape schliesst die Vollbild-Show wieder, die Vorschau bleibt sichtbar.
  await overlay.press("Escape");
  await expect(overlay).toHaveCount(0);
  await expect(page.locator(".sponsor-tile", { hasText: "Bäckerei Muster" })).toBeVisible();
});
