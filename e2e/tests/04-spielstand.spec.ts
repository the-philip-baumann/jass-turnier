import { test, expect } from "@playwright/test";
import { setupTournamentWithPlayers, startTournamentViaApi, API_BASE } from "./helpers";

test("Spielstand: Rangliste summiert Punkte korrekt über mehrere Runden", async ({ page, request }) => {
  const { id } = await setupTournamentWithPlayers(request, {
    namePrefix: "Spielstand-Test",
    players: 4,
    rounds: 1,
    numGroups: 1,
    tablesPerRow: 1,
  });
  const started = await startTournamentViaApi(request, id);

  const gamesRes = await request.get(`${API_BASE}/tournaments/${id}/games`);
  const games = await gamesRes.json();
  expect(games).toHaveLength(1);
  const game = games[0];

  // Team 1 gewinnt klar: 100 : 57
  const scoreRes = await request.patch(`${API_BASE}/tournaments/${id}/games/${game.id}`, {
    data: { team1_score: 100, team2_score: 57 },
  });
  expect(scoreRes.ok()).toBeTruthy();

  await page.goto(`/tournaments/${id}/spielstand`);
  await expect(page.locator(".ranking-table tbody tr")).toHaveCount(4);

  const team1PlayerIds = game.results.filter((r: any) => r.team === 1).map((r: any) => r.player_id);
  const team1Numbers = started.players
    .filter((p: any) => team1PlayerIds.includes(p.id))
    .map((p: any) => p.player_number);

  // Die beiden Spieler von Team 1 stehen mit 100 Punkten oben (Rang 1 & 2, Reihenfolge egal)
  const firstTwoRows = await page.locator(".ranking-table tbody tr").locator(".points").allTextContents();
  expect(firstTwoRows.slice(0, 2)).toEqual(["100", "100"]);
  expect(firstTwoRows.slice(2, 4)).toEqual(["57", "57"]);

  const firstRowText = await page.locator(".ranking-table tbody tr").first().textContent();
  expect(team1Numbers.some((n: number) => firstRowText?.includes(`#${n}`))).toBeTruthy();
});
