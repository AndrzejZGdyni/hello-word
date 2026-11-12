# CLAUDE.md

## Jev (TypeSafe System One) – jak uruchamiać

- Narzędzia: `tools/jev-run/` (Cieśnina Ormuz), `tools/jev-zima/` (gotowość na zimę)
  i `tools/jev-renko/` (CZEKAĆ / ARM / FIRE z wykresów Renko D1, H1, M5 według profilu
  R11 2.4-trading-r3; `dane` liczy kod, `state` ocenia Jev; rejestr: `rejestr.py`).
  Opis pytań, tabel decyzyjnych i wyników: `tools/jev-run/WZOR_PYTANIA.md`,
  `tools/jev-zima/README.md`, `tools/jev-renko/README.md`.
- **Klucz API:** w sesji Claude Code w chmurze, w środowisku z podłączonym TypeSafe, klucz
  do `api.typesafe.ai` wstrzykuje proxy. Nie ustawiaj `TYPESAFE_API_KEY` i nie proś
  o klucz w czacie. Szybki test dostępu: `curl -sS https://api.typesafe.ai/v1/models`
  (200 = działa; 401/403 = środowisko bez TypeSafe – powiedz o tym użytkownikowi).
- **Nowa analiza:** skopiuj szablon (`tools/jev-run/jev_hormuz_template.json`,
  `tools/jev-zima/zima_template.json` lub `tools/jev-renko/renko_template.json`)
  do katalogu roboczego (scratchpad), zmień tylko
  `state` i uruchom:
  ```bash
  python3 tools/jev-run/jev_run.py <payload.json> --log <scratchpad>/jev_log.jsonl
  python3 tools/jev-zima/jev_zima.py <payload.json> --log <scratchpad>/zima_log.jsonl
  python3 tools/jev-renko/jev_renko.py <payload.json> --log <scratchpad>/renko_log.jsonl
  ```
  Najpierw `--dry-run`. Kody wyjścia różne od 0 i 1 to poprawne wyniki tabeli
  decyzyjnej (np. 3 = ALERT), nie błędy.
- **Payload spoza tych zestawów** (inne pytania): `jev_run.py`/`jev_zima.py`/`jev_renko.py` go odrzucą,
  bo wymagają swoich pytań decyzyjnych. Wyślij go bezpośrednio:
  ```bash
  curl -sS https://api.typesafe.ai/v1/systemone -H "Content-Type: application/json" -d @payload.json
  ```
- **Gdy użytkownik rozstrzyga pytanie inaczej niż model** (np. „uznaj X za potwierdzenie
  min”), użyj `--override KLUCZ=tak|nie` (`jev_run.py`, `jev_zima.py`, `jev_renko.py`). Nie obniżaj progów i nie przeredagowuj
  `state`, żeby model przekroczył próg.
- **Nie zmieniaj brzmienia pytań w szablonach** bez prośby użytkownika – zmienia to
  `questions_sha256` i zrywa porównywalność wyników w dziennikach.
- Dzienniki (`*_log.jsonl`), rejestry (`renko_rejestr.jsonl`, `renko_blokady.jsonl`) i wyniki
  CSV nie trafiają do repozytorium (repozytorium jest publiczne). Pełnego profilu R11
  (historia incydentów, wyniki w PLN) nie zapisuj w repozytorium – w kodzie są tylko progi.

## Styl odpowiedzi

- Każdą odpowiedź kończ sekcją **Sugestie:** z ponumerowaną listą (2–4 pozycje)
  następnych kroków, tak aby użytkownik mógł odpowiedzieć samym numerem (np. „1”).
  Odpowiedź samym numerem traktuj jako wybór odpowiedniej sugestii z poprzedniej wiadomości.
