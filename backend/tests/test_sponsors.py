import io

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)


def make_tournament(client, name="Herbstturnier", date="2026-09-15"):
    resp = client.post("/tournaments", json={"name": name, "date": date})
    assert resp.status_code == 200
    return resp.json()


def upload_logo(client, tournament_id, name="Bäckerei Muster", filename="logo.png", content=None):
    return client.post(
        f"/tournaments/{tournament_id}/sponsors",
        data={"name": name},
        files={"logo": (filename, io.BytesIO(content or PNG_BYTES), "image/png")},
    )


def start_tournament(client, tournament_id):
    for i in range(4):
        client.post(
            f"/tournaments/{tournament_id}/players",
            json={"vorname": f"P{i}", "nachname": "Spieler"},
        )
    client.patch(
        f"/tournaments/{tournament_id}",
        json={"rounds": 1, "num_groups": 1, "tables_per_row": 4, "anzahl_ansagen": 1},
    )
    resp = client.post(f"/tournaments/{tournament_id}/start")
    assert resp.status_code == 200


class TestAddSponsor:
    def test_add_sponsor_happy_path(self, client):
        tournament = make_tournament(client)
        resp = upload_logo(client, tournament["id"])
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Bäckerei Muster"
        assert body["tournament_id"] == tournament["id"]
        assert "logo_data" not in body

    def test_add_sponsor_tournament_not_found(self, client):
        resp = upload_logo(client, 999)
        assert resp.status_code == 404

    def test_add_sponsor_blank_name_rejected(self, client):
        tournament = make_tournament(client)
        resp = upload_logo(client, tournament["id"], name="   ")
        assert resp.status_code == 400

    def test_add_sponsor_rejects_non_image_content_type(self, client):
        tournament = make_tournament(client)
        resp = client.post(
            f"/tournaments/{tournament['id']}/sponsors",
            data={"name": "Sponsor"},
            files={"logo": ("logo.txt", io.BytesIO(b"not an image"), "text/plain")},
        )
        assert resp.status_code == 400

    def test_add_sponsor_rejects_empty_file(self, client):
        tournament = make_tournament(client)
        resp = client.post(
            f"/tournaments/{tournament['id']}/sponsors",
            data={"name": "Sponsor"},
            files={"logo": ("logo.png", io.BytesIO(b""), "image/png")},
        )
        assert resp.status_code == 400

    def test_add_sponsor_rejects_oversized_file(self, client):
        tournament = make_tournament(client)
        oversized = b"\x00" * (5 * 1024 * 1024 + 1)
        resp = upload_logo(client, tournament["id"], content=oversized)
        assert resp.status_code == 400

    def test_add_sponsor_after_start_rejected(self, client):
        tournament = make_tournament(client)
        start_tournament(client, tournament["id"])
        resp = upload_logo(client, tournament["id"])
        assert resp.status_code == 400


class TestListSponsors:
    def test_list_sponsors(self, client):
        tournament = make_tournament(client)
        upload_logo(client, tournament["id"], name="Sponsor A")
        upload_logo(client, tournament["id"], name="Sponsor B")
        resp = client.get(f"/tournaments/{tournament['id']}/sponsors")
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()]
        assert names == ["Sponsor A", "Sponsor B"]

    def test_list_sponsors_scoped_to_tournament(self, client):
        t1 = make_tournament(client, name="T1")
        t2 = make_tournament(client, name="T2")
        upload_logo(client, t1["id"], name="Sponsor A")
        resp = client.get(f"/tournaments/{t2['id']}/sponsors")
        assert resp.status_code == 200
        assert resp.json() == []


class TestSponsorLogo:
    def test_get_logo_returns_image_bytes(self, client):
        tournament = make_tournament(client)
        sponsor = upload_logo(client, tournament["id"]).json()
        resp = client.get(f"/tournaments/{tournament['id']}/sponsors/{sponsor['id']}/logo")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content == PNG_BYTES

    def test_get_logo_not_found(self, client):
        tournament = make_tournament(client)
        resp = client.get(f"/tournaments/{tournament['id']}/sponsors/999/logo")
        assert resp.status_code == 404

    def test_get_logo_wrong_tournament(self, client):
        t1 = make_tournament(client, name="T1")
        t2 = make_tournament(client, name="T2")
        sponsor = upload_logo(client, t1["id"]).json()
        resp = client.get(f"/tournaments/{t2['id']}/sponsors/{sponsor['id']}/logo")
        assert resp.status_code == 404


class TestRemoveSponsor:
    def test_remove_sponsor_happy_path(self, client):
        tournament = make_tournament(client)
        sponsor = upload_logo(client, tournament["id"]).json()
        resp = client.delete(f"/tournaments/{tournament['id']}/sponsors/{sponsor['id']}")
        assert resp.status_code == 204
        assert client.get(f"/tournaments/{tournament['id']}/sponsors").json() == []

    def test_remove_sponsor_not_found(self, client):
        tournament = make_tournament(client)
        resp = client.delete(f"/tournaments/{tournament['id']}/sponsors/999")
        assert resp.status_code == 404

    def test_remove_sponsor_after_start_rejected(self, client):
        tournament = make_tournament(client)
        sponsor = upload_logo(client, tournament["id"]).json()
        start_tournament(client, tournament["id"])
        resp = client.delete(f"/tournaments/{tournament['id']}/sponsors/{sponsor['id']}")
        assert resp.status_code == 400
