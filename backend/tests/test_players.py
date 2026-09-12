def make_tournament(client, name="Herbstturnier", date="2026-09-15"):
    resp = client.post("/tournaments", json={"name": name, "date": date})
    assert resp.status_code == 200
    return resp.json()


class TestAddPlayer:
    def test_add_player_happy_path(self, client):
        tournament = make_tournament(client)
        resp = client.post(
            f"/tournaments/{tournament['id']}/players",
            json={"vorname": "Hans", "nachname": "Muster"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Hans Muster"
        assert body["player_number"] == 1

    def test_add_player_auto_increments_number(self, client):
        tournament = make_tournament(client)
        url = f"/tournaments/{tournament['id']}/players"
        client.post(url, json={"vorname": "A", "nachname": "B"})
        resp = client.post(url, json={"vorname": "C", "nachname": "D"})
        assert resp.json()["player_number"] == 2

    def test_add_player_explicit_number_conflict(self, client):
        tournament = make_tournament(client)
        client.post(
            f"/tournaments/{tournament['id']}/players",
            json={"vorname": "A", "nachname": "B", "player_number": 5},
        )
        resp = client.post(
            f"/tournaments/{tournament['id']}/players",
            json={"vorname": "C", "nachname": "D", "player_number": 5},
        )
        assert resp.status_code == 400

    def test_add_player_tournament_not_found(self, client):
        resp = client.post(
            "/tournaments/999/players",
            json={"vorname": "Hans", "nachname": "Muster"},
        )
        assert resp.status_code == 404

    def test_add_player_after_start_rejected(self, client):
        tournament = make_tournament(client)
        for i in range(4):
            client.post(
                f"/tournaments/{tournament['id']}/players",
                json={"vorname": f"P{i}", "nachname": "X"},
            )
        client.patch(
            f"/tournaments/{tournament['id']}",
            json={"rounds": 1, "num_groups": 1, "tables_per_row": 4, "anzahl_ansagen": 1},
        )
        start_resp = client.post(f"/tournaments/{tournament['id']}/start")
        assert start_resp.status_code == 200

        resp = client.post(
            f"/tournaments/{tournament['id']}/players",
            json={"vorname": "Late", "nachname": "Comer"},
        )
        assert resp.status_code == 400


class TestUpdatePlayer:
    def test_update_player_name(self, client):
        tournament = make_tournament(client)
        player = client.post(
            f"/tournaments/{tournament['id']}/players",
            json={"vorname": "Hans", "nachname": "Muster"},
        ).json()
        resp = client.patch(
            f"/tournaments/{tournament['id']}/players/{player['id']}",
            json={"name": "Neuer Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Neuer Name"

    def test_update_player_not_found(self, client):
        tournament = make_tournament(client)
        resp = client.patch(
            f"/tournaments/{tournament['id']}/players/999",
            json={"name": "Neuer Name"},
        )
        assert resp.status_code == 404

    def test_update_player_wrong_tournament(self, client):
        t1 = make_tournament(client, name="T1")
        t2 = make_tournament(client, name="T2")
        player = client.post(
            f"/tournaments/{t1['id']}/players",
            json={"vorname": "Hans", "nachname": "Muster"},
        ).json()
        resp = client.patch(
            f"/tournaments/{t2['id']}/players/{player['id']}",
            json={"name": "Neuer Name"},
        )
        assert resp.status_code == 404


class TestRemovePlayer:
    def test_remove_player_happy_path(self, client):
        tournament = make_tournament(client)
        player = client.post(
            f"/tournaments/{tournament['id']}/players",
            json={"vorname": "Hans", "nachname": "Muster"},
        ).json()
        resp = client.delete(f"/tournaments/{tournament['id']}/players/{player['id']}")
        assert resp.status_code == 204

    def test_remove_player_not_found(self, client):
        tournament = make_tournament(client)
        resp = client.delete(f"/tournaments/{tournament['id']}/players/999")
        assert resp.status_code == 404
