import { test, expect } from "@playwright/test";
import { createTournament, addPlayerViaUi, API_BASE } from "./helpers";

test("Start scheitert bei zu wenigen angemeldeten Spielern", async ({ page, request }) => {
  const { id } = await createTournament(request, "ZuWenigSpieler");
  await page.goto(`/tournaments/${id}/spielerverwaltung`);
  await addPlayerViaUi(page, "Solo", "Spieler");

  await page.getByRole("button", { name: "▶ Turnier starten" }).click();
  await expect(page.getByText("mindestens 2 angemeldete Spieler")).toBeVisible();
});

test("Start scheitert bei mehr Gruppen als angemeldeten Spielern", async ({ page, request }) => {
  const { id } = await createTournament(request, "ZuVieleGruppen");
  await request.patch(`${API_BASE}/tournaments/${id}`, {
    data: { rounds: 1, num_groups: 5, tables_per_row: 2, anzahl_ansagen: 1 },
  });
  await page.goto(`/tournaments/${id}/spielerverwaltung`);
  await addPlayerViaUi(page, "Anna", "Muster");
  await addPlayerViaUi(page, "Beat", "Meier");

  await page.getByRole("button", { name: "▶ Turnier starten" }).click();
  await expect(page.getByText("Mehr Gruppen als angemeldete Spieler")).toBeVisible();
});

test("Doppelte Spielernummer wird abgelehnt", async ({ page, request }) => {
  const { id } = await createTournament(request, "DoppelteNummer");
  await page.goto(`/tournaments/${id}/spielerverwaltung`);
  await addPlayerViaUi(page, "Anna", "Muster");

  // Zweiten Spieler mit derselben Nummer wie der erste anlegen
  await page.locator(".number-field input").fill("1");
  await page.getByPlaceholder("Vorname").fill("Beat");
  await page.getByPlaceholder("Nachname").fill("Meier");
  await page.getByRole("button", { name: "+ Hinzufügen" }).click();

  await expect(page.getByText("Spielernummer ist bereits vergeben")).toBeVisible();
  await expect(page.locator(".player-card")).toHaveCount(1);
});

test("Turnier löschen entfernt es aus der Liste", async ({ page, request }) => {
  const { id, name } = await createTournament(request, "ZumLoeschen");
  await page.goto("/");
  const card = page.locator(".tournament-card", { hasText: name });
  await expect(card).toBeVisible();

  await card.getByRole("button", { name: "Löschen" }).click();

  await expect(page.locator(".tournament-card", { hasText: name })).toHaveCount(0);
});

test("Seiten-Reload mitten im laufenden Turnier behält den Zustand", async ({ page, request }) => {
  const { id } = await createTournament(request, "ReloadTest");
  // Default ist num_groups=2 — mit nur 4 Spielern bräuchte das 2 Gruppen à 2,
  // was keine vollen Vierertische ergibt. Auf 1 Gruppe umstellen.
  await request.patch(`${API_BASE}/tournaments/${id}`, {
    data: { rounds: 1, num_groups: 1, tables_per_row: 2, anzahl_ansagen: 1 },
  });
  await page.goto(`/tournaments/${id}/spielerverwaltung`);
  await addPlayerViaUi(page, "Anna", "Muster");
  await addPlayerViaUi(page, "Beat", "Meier");
  await addPlayerViaUi(page, "Clara", "Suter");
  await addPlayerViaUi(page, "David", "Frei");
  await page.getByRole("button", { name: "▶ Turnier starten" }).click();
  await expect(page.getByText("🟢 Turnier gestartet")).toBeVisible();

  await page.reload();

  await expect(page.getByText("🟢 Turnier gestartet")).toBeVisible();
  await page.getByRole("link", { name: "🪑 Sitzplan" }).click();
  await expect(page.locator(".table-card")).toHaveCount(1);
});
