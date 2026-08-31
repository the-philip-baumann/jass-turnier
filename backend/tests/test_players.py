import io


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
        assert body["registered"] is True
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
            r = client.post(
                f"/tournaments/{tournament['id']}/players",
                json={"vorname": f"P{i}", "nachname": "X"},
            )
            client.patch(
                f"/tournaments/{tournament['id']}/players/{r.json()['id']}/registered",
                json={"registered": True},
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

    def test_update_player_registered(self, client):
        tournament = make_tournament(client)
        player = client.post(
            f"/tournaments/{tournament['id']}/players",
            json={"vorname": "Hans", "nachname": "Muster"},
        ).json()
        resp = client.patch(
            f"/tournaments/{tournament['id']}/players/{player['id']}/registered",
            json={"registered": False},
        )
        assert resp.status_code == 200
        assert resp.json()["registered"] is False


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


class TestImportPlayers:
    def _csv(self, rows):
        header = "Zeitstempel,Vorname,Nachname,E-Mail-Adresse\n"
        body = "\n".join(",".join(row) for row in rows)
        return header + body + "\n"

    def test_import_players_happy_path(self, client):
        tournament = make_tournament(client)
        csv_content = self._csv(
            [
                ("2026-01-01", "Hans", "Muster", "hans@example.com"),
                ("2026-01-02", "Erika", "Muster", "erika@example.com"),
            ]
        )
        resp = client.post(
            f"/tournaments/{tournament['id']}/players/import",
            files={"file": ("players.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["created"]) == 2
        assert body["skipped_duplicates"] == 0
        assert body["skipped_invalid"] == 0

    def test_import_players_missing_columns(self, client):
        tournament = make_tournament(client)
        bad_csv = "Vorname,Nachname\nHans,Muster\n"
        resp = client.post(
            f"/tournaments/{tournament['id']}/players/import",
            files={"file": ("players.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")},
        )
        assert resp.status_code == 400

    def test_import_players_duplicate_email_skipped(self, client):
        tournament = make_tournament(client)
        csv_content = self._csv(
            [
                ("2026-01-01", "Hans", "Muster", "hans@example.com"),
                ("2026-01-02", "Hans", "Zweitmal", "hans@example.com"),
            ]
        )
        resp = client.post(
            f"/tournaments/{tournament['id']}/players/import",
            files={"file": ("players.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["created"]) == 1
        assert body["skipped_duplicates"] == 1

    def test_import_players_invalid_row_skipped(self, client):
        tournament = make_tournament(client)
        csv_content = self._csv(
            [
                ("2026-01-01", "", "", ""),
            ]
        )
        resp = client.post(
            f"/tournaments/{tournament['id']}/players/import",
            files={"file": ("players.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["created"]) == 0
        assert body["skipped_invalid"] == 1

    def test_import_players_twice_rejected(self, client):
        tournament = make_tournament(client)
        csv_content = self._csv([("2026-01-01", "Hans", "Muster", "hans@example.com")])
        client.post(
            f"/tournaments/{tournament['id']}/players/import",
            files={"file": ("players.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        resp = client.post(
            f"/tournaments/{tournament['id']}/players/import",
            files={"file": ("players.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        assert resp.status_code == 400

    def test_import_players_tournament_not_found(self, client):
        csv_content = self._csv([("2026-01-01", "Hans", "Muster", "hans@example.com")])
        resp = client.post(
            "/tournaments/999/players/import",
            files={"file": ("players.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        assert resp.status_code == 404
