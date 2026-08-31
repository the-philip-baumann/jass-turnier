def make_tournament(client, name="Herbstturnier", date="2026-09-15"):
    resp = client.post("/tournaments", json={"name": name, "date": date})
    assert resp.status_code == 200
    return resp.json()


class TestCreateTournament:
    def test_create_tournament_happy_path(self, client):
        resp = client.post("/tournaments", json={"name": "Herbstturnier", "date": "2026-09-15"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Herbstturnier"
        assert body["date"] == "2026-09-15"
        assert body["status"] == "setup"
        assert body["rounds"] == 4
        assert body["num_groups"] == 2
        assert body["anzahl_ansagen"] == 1
        assert body["players_imported"] is False

    def test_create_tournament_missing_fields(self, client):
        resp = client.post("/tournaments", json={"name": "Ohne Datum"})
        assert resp.status_code == 422


class TestListAndGetTournament:
    def test_list_tournaments_empty(self, client):
        resp = client.get("/tournaments")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_tournaments_returns_created(self, client):
        make_tournament(client, name="A")
        make_tournament(client, name="B")
        resp = client.get("/tournaments")
        assert resp.status_code == 200
        names = {t["name"] for t in resp.json()}
        assert names == {"A", "B"}

    def test_get_tournament_happy_path(self, client):
        created = make_tournament(client)
        resp = client.get(f"/tournaments/{created['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == created["id"]
        assert body["players"] == []

    def test_get_tournament_not_found(self, client):
        resp = client.get("/tournaments/999")
        assert resp.status_code == 404


class TestUpdateTournament:
    def test_update_tournament_happy_path(self, client):
        created = make_tournament(client)
        resp = client.patch(
            f"/tournaments/{created['id']}",
            json={"rounds": 6, "num_groups": 3, "tables_per_row": 5, "anzahl_ansagen": 2},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["rounds"] == 6
        assert body["num_groups"] == 3
        assert body["tables_per_row"] == 5
        assert body["anzahl_ansagen"] == 2

    def test_update_tournament_not_found(self, client):
        resp = client.patch(
            "/tournaments/999",
            json={"rounds": 6, "num_groups": 3, "tables_per_row": 5, "anzahl_ansagen": 2},
        )
        assert resp.status_code == 404


class TestDeleteTournament:
    def test_delete_tournament_happy_path(self, client):
        created = make_tournament(client)
        resp = client.delete(f"/tournaments/{created['id']}")
        assert resp.status_code == 204
        resp = client.get(f"/tournaments/{created['id']}")
        assert resp.status_code == 404

    def test_delete_tournament_not_found(self, client):
        resp = client.delete("/tournaments/999")
        assert resp.status_code == 404
