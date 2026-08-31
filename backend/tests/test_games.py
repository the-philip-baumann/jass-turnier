def make_tournament(client, name="Herbstturnier", date="2026-09-15"):
    resp = client.post("/tournaments", json={"name": name, "date": date})
    assert resp.status_code == 200
    return resp.json()


def make_registered_players(client, tournament_id, count):
    players = []
    for i in range(count):
        resp = client.post(
            f"/tournaments/{tournament_id}/players",
            json={"vorname": f"P{i}", "nachname": "Spieler"},
        )
        player = resp.json()
        client.patch(
            f"/tournaments/{tournament_id}/players/{player['id']}/registered",
            json={"registered": True},
        )
        players.append(player)
    return players


class TestStartTournament:
    def test_start_tournament_happy_path(self, client):
        tournament = make_tournament(client)
        make_registered_players(client, tournament["id"], 4)
        client.patch(
            f"/tournaments/{tournament['id']}",
            json={"rounds": 1, "num_groups": 1, "tables_per_row": 4, "anzahl_ansagen": 1},
        )
        resp = client.post(f"/tournaments/{tournament['id']}/start")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "started"

        games_resp = client.get(f"/tournaments/{tournament['id']}/games")
        assert games_resp.status_code == 200
        assert len(games_resp.json()) == 1

    def test_start_tournament_not_found(self, client):
        resp = client.post("/tournaments/999/start")
        assert resp.status_code == 404

    def test_start_tournament_too_few_players(self, client):
        tournament = make_tournament(client)
        make_registered_players(client, tournament["id"], 1)
        resp = client.post(f"/tournaments/{tournament['id']}/start")
        assert resp.status_code == 400

    def test_start_tournament_twice_rejected(self, client):
        tournament = make_tournament(client)
        make_registered_players(client, tournament["id"], 4)
        client.patch(
            f"/tournaments/{tournament['id']}",
            json={"rounds": 1, "num_groups": 1, "tables_per_row": 4, "anzahl_ansagen": 1},
        )
        client.post(f"/tournaments/{tournament['id']}/start")
        resp = client.post(f"/tournaments/{tournament['id']}/start")
        assert resp.status_code == 400

    def test_start_tournament_more_groups_than_players(self, client):
        tournament = make_tournament(client)
        make_registered_players(client, tournament["id"], 2)
        client.patch(
            f"/tournaments/{tournament['id']}",
            json={"rounds": 1, "num_groups": 5, "tables_per_row": 4, "anzahl_ansagen": 1},
        )
        resp = client.post(f"/tournaments/{tournament['id']}/start")
        assert resp.status_code == 400


class TestResetTournament:
    def test_reset_tournament_happy_path(self, client):
        tournament = make_tournament(client)
        make_registered_players(client, tournament["id"], 4)
        client.patch(
            f"/tournaments/{tournament['id']}",
            json={"rounds": 1, "num_groups": 1, "tables_per_row": 4, "anzahl_ansagen": 1},
        )
        client.post(f"/tournaments/{tournament['id']}/start")

        resp = client.post(f"/tournaments/{tournament['id']}/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "setup"

        games_resp = client.get(f"/tournaments/{tournament['id']}/games")
        assert games_resp.json() == []

    def test_reset_tournament_not_started(self, client):
        tournament = make_tournament(client)
        resp = client.post(f"/tournaments/{tournament['id']}/reset")
        assert resp.status_code == 400

    def test_reset_tournament_not_found(self, client):
        resp = client.post("/tournaments/999/reset")
        assert resp.status_code == 404


class TestCreateAndListGames:
    def test_create_game_happy_path(self, client):
        tournament = make_tournament(client)
        resp = client.post(
            f"/tournaments/{tournament['id']}/games",
            json={"round_number": 1, "table_number": 1},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["round_number"] == 1
        assert body["table_number"] == 1
        assert body["results"] == []

    def test_create_game_tournament_not_found(self, client):
        resp = client.post(
            "/tournaments/999/games",
            json={"round_number": 1, "table_number": 1},
        )
        assert resp.status_code == 404

    def test_list_games_empty(self, client):
        tournament = make_tournament(client)
        resp = client.get(f"/tournaments/{tournament['id']}/games")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGameResults:
    def _setup_started_tournament_with_game(self, client):
        tournament = make_tournament(client)
        make_registered_players(client, tournament["id"], 4)
        client.patch(
            f"/tournaments/{tournament['id']}",
            json={"rounds": 1, "num_groups": 1, "tables_per_row": 4, "anzahl_ansagen": 1},
        )
        client.post(f"/tournaments/{tournament['id']}/start")
        games = client.get(f"/tournaments/{tournament['id']}/games").json()
        return tournament, games[0]

    def test_update_game_score_happy_path(self, client):
        tournament, game = self._setup_started_tournament_with_game(client)
        resp = client.patch(
            f"/tournaments/{tournament['id']}/games/{game['id']}",
            json={"team1_score": 100, "team2_score": 57},
        )
        assert resp.status_code == 200
        body = resp.json()
        for result in body["results"]:
            assert result["points"] in (100, 57)

    def test_update_game_score_invalid_sum(self, client):
        tournament, game = self._setup_started_tournament_with_game(client)
        resp = client.patch(
            f"/tournaments/{tournament['id']}/games/{game['id']}",
            json={"team1_score": 100, "team2_score": 100},
        )
        assert resp.status_code == 422

    def test_update_game_score_game_not_found(self, client):
        tournament = make_tournament(client)
        resp = client.patch(
            f"/tournaments/{tournament['id']}/games/999",
            json={"team1_score": 100, "team2_score": 57},
        )
        assert resp.status_code == 404

    def test_add_result_happy_path(self, client):
        tournament = make_tournament(client)
        player = client.post(
            f"/tournaments/{tournament['id']}/players",
            json={"vorname": "Hans", "nachname": "Muster"},
        ).json()
        game = client.post(
            f"/tournaments/{tournament['id']}/games",
            json={"round_number": 1, "table_number": 1},
        ).json()
        resp = client.post(
            f"/tournaments/{tournament['id']}/games/{game['id']}/results",
            json={"player_id": player["id"], "team": 1, "points": 100},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["player_id"] == player["id"]
        assert body["team"] == 1
        assert body["points"] == 100

    def test_add_result_game_not_found(self, client):
        tournament = make_tournament(client)
        player = client.post(
            f"/tournaments/{tournament['id']}/players",
            json={"vorname": "Hans", "nachname": "Muster"},
        ).json()
        resp = client.post(
            f"/tournaments/{tournament['id']}/games/999/results",
            json={"player_id": player["id"], "team": 1, "points": 100},
        )
        assert resp.status_code == 404
