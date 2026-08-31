import type { APIRequestContext, Page } from "@playwright/test";

export const API_BASE = "http://localhost:8001";

/** Creates a fresh tournament directly via the API and returns its id + name. */
export async function createTournament(request: APIRequestContext, namePrefix: string) {
  const name = `${namePrefix} ${Date.now()}`;
  const res = await request.post(`${API_BASE}/tournaments`, {
    data: { name, date: "2026-09-05" },
  });
  if (!res.ok()) throw new Error(`create_tournament failed: ${res.status()} ${await res.text()}`);
  const body = await res.json();
  return { id: body.id as number, name };
}

/** Adds a manually-entered (auto-registered) player via the UI form on the Spielerverwaltung tab. */
export async function addPlayerViaUi(page: Page, vorname: string, nachname: string) {
  await page.getByPlaceholder("Vorname").fill(vorname);
  await page.getByPlaceholder("Nachname").fill(nachname);
  await page.getByRole("button", { name: "+ Hinzufügen" }).click();
  await page.getByText(`${vorname} ${nachname}`).waitFor();
}

export async function gotoTournament(page: Page, id: number, tab: string) {
  await page.goto(`/tournaments/${id}/${tab}`);
}

/**
 * Locates the <input> inside a `.field` block whose <label> text matches.
 * The app's labels aren't wired via for/id, so getByLabel() can't see them.
 */
export function fieldInput(page: Page, labelText: string) {
  return page.locator(".field", { has: page.locator("label", { hasText: labelText }) }).locator("input");
}

/**
 * Full setup for tests that need a ready-to-start tournament: creates the
 * tournament via API, configures rounds/groups via API (faster + more
 * reliable than the UI for a pure fixture step), and adds `count` players
 * via the UI (so the player-add flow itself stays exercised at least once
 * per suite in 01-tournament-lifecycle.spec.ts; here we go through the API
 * for speed since these specs focus on later stages).
 */
export async function setupTournamentWithPlayers(
  request: APIRequestContext,
  opts: { namePrefix: string; players: number; rounds: number; numGroups: number; tablesPerRow?: number }
) {
  const { id, name } = await createTournament(request, opts.namePrefix);
  await request.patch(`${API_BASE}/tournaments/${id}`, {
    data: {
      rounds: opts.rounds,
      num_groups: opts.numGroups,
      tables_per_row: opts.tablesPerRow ?? 4,
      anzahl_ansagen: 1,
    },
  });
  for (let i = 1; i <= opts.players; i++) {
    const res = await request.post(`${API_BASE}/tournaments/${id}/players`, {
      data: { vorname: `Spieler${i}`, nachname: "Test", player_number: i },
    });
    if (!res.ok()) throw new Error(`add_player failed: ${res.status()} ${await res.text()}`);
  }
  return { id, name };
}

export async function startTournamentViaApi(request: APIRequestContext, id: number) {
  const res = await request.post(`${API_BASE}/tournaments/${id}/start`);
  if (!res.ok()) throw new Error(`start_tournament failed: ${res.status()} ${await res.text()}`);
  return res.json();
}
