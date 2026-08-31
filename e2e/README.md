# Jass-Turnier – End-to-End-Tests

Playwright-Testsuite, die den kompletten Turnierablauf über die echte UI
durchspielt (Turnier anlegen → konfigurieren → Spieler erfassen → starten →
Sitzplan/Spielplan → Resultate eintragen → Rangliste) plus ein paar
Fehlerfälle. Jeder Testlauf zeichnet ein Video und einen interaktiven Trace
pro Test auf.

Läuft komplett isoliert gegen einen eigenen, temporären Postgres-Testcontainer
plus das Backend als Docker-Container, gebaut aus dem echten `backend/Dockerfile`
(Python 3.12, wie in Produktion) — die echte Turnier-Datenbank und dein lokales
`backend/venv` werden nie angefasst.

> Hinweis: `backend/venv` läuft aktuell mit Python 3.9, der Code nutzt aber
> `str | None`-Syntax (Python 3.10+) — das lokale venv kann das Backend
> deshalb derzeit nicht direkt starten. Für Docker (und damit auch für diese
> Tests) ist das kein Problem, da dort Python 3.12 verwendet wird.

## Einmaliges Setup

```bash
npm install
npx playwright install --with-deps chromium
```

Docker Desktop muss laufen.

## Tests ausführen

```bash
npm test          # baut/startet Test-DB + Backend-Container, startet Frontend, führt alle Tests aus
npm run db:down   # stoppt die Testcontainer wieder (Daten sind eh flüchtig, tmpfs)
```

## Ergebnis ansehen

```bash
npm run report
```

Öffnet den HTML-Report im Browser: pro Test ein Video, ein Trace (Zeitleiste,
Netzwerk, DOM-Snapshots) und Screenshots. Bei Fehlschlägen zeigt der Trace
genau den Zustand der Seite im Moment des Fehlers.

## Testdateien

- `01-tournament-lifecycle.spec.ts` – Turnier anlegen, konfigurieren, Spieler erfassen
- `02-sitzplan.spec.ts` – Sitzplan-Generierung nach Turnierstart
- `03-spielplan.spec.ts` – Spielplan-Struktur, Score-Eintragung, Validierung der Summe
- `04-spielstand.spec.ts` – Ranglisten-Berechnung
- `05-full-e2e.spec.ts` – kompletter Durchlauf über die UI (die "Generalprobe")
- `06-edge-cases.spec.ts` – zu wenige Spieler, zu viele Gruppen, doppelte Nummer, Löschen, Reload
- `07-grossturnier-64-spieler.spec.ts` – Grossturnier-Stresstest: 64 Spieler, 6 Runden, 16 Tische/Runde, alle 96 Spiele bewertet, finale Rangliste rechnerisch verifiziert (Laufzeit ~35–40s)
