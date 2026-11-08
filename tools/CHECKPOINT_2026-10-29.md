# Checkpoint – stan na 07.11.2026 (utworzono 29.10.2026)

Podsumowanie pracy z modelem Jev (TypeSafe System One) do wklejenia na początek nowego
wątku. Instrukcja uruchamiania: [`CLAUDE.md`](../CLAUDE.md).

## Stan repozytorium

- Gałąź domyślna `claude/android-collaboration-JSWfh`; PR #3, #4, #7, #8 scalone.
- Brak otwartych prac.

## Narzędzia

| Katalog | Zakres | Pytania | Tabela decyzyjna (kody wyjścia) | Opis |
|---|---|---|---|---|
| `tools/jev-run/` | sytuacja w rejonie Cieśniny Ormuz | `jev_hormuz_template.json`: 5 pytań decyzyjnych tak/nie, skale `shipping_disruption_level` i `production_loss_level` | OK 0 / TRIP 2 / ALERT 3 / SPRAWDŹ 4 | `WZOR_PYTANIA.md`; test: `jev_variance_test.py` |
| `tools/jev-zima/` | gotowość domowego ogrzewania na zimę | `zima_template.json`: 6 pytań tak/nie | OK 0 / KRYTYCZNE 2 / ALERT 3 / SPRAWDŹ 4 / UWAGA 5 | `README.md`; test: `test_wariantow.py` |

- Oba skrypty mają `--override KLUCZ=tak|nie`: jawna ocena analityka zapisywana
  w dzienniku obok odpowiedzi modelu.
- Klucz API dodaje środowisko chmurowe z podłączonym TypeSafe. Payload z innymi pytaniami
  niż w szablonach wysyła się bezpośrednio do API (`CLAUDE.md`).

## Inne narzędzia Jev w repozytorium (osobny wątek)

- `tools/jev-centrowka/`, `tools/jev-lozysko/`, `tools/jev-luzy/`, `tools/jev-niewywazenie/`:
  diagnostyka wibroakustyczna maszyn na danych syntetycznych (ćwiczenie edukacyjne);
  zbiorcze podsumowanie w `tools/raport-zbiorczy.md`.
- `tools/jev-ekg/`: ćwiczenie edukacyjne – ocena EKG z obrazu, opis we własnym `README.md`.
- Niezwiązane z analizą Ormuzu/zimy; nie wymagają działania przy kontynuacji tego checkpointu.

## Ostatnie wyniki (`jev-1.14.0`)

| Data | Analiza | Wynik |
|---|---|---|
| 29.10 | Ormuz | model: **ALERT** – Iran ogłosił zamknięcie cieśniny (0,91), przepływ ok. 82% przedwojennego (0,97), miny 0,65–0,69. Z oceną analityka (komunikat IMO = potwierdzenie min): **TRIP** |
| 29.10 | Zima (szablon) | model: **ALERT** (węgiel 0,83). Z oceną analityka `coal_unavailable=nie`: **UWAGA** – ryzyko rozbicia wiru polarnego (0,95) |
| 29.10 | Zima, tylko meteorologia | listopad powyżej normy; grudzień–luty w normie (IMGW; C3S przewiduje cieplej); możliwe mrozy w listopadzie (ok. 10–11.11 lub ostatnia dekada); luty z opadami i śniegiem; wysoka niepewność prognoz |
| 30.10 | Ormuz | model: **OK** – wyraźna deeskalacja względem 29.10: wszystkie pytania decyzyjne „nie" z wysoką pewnością (0,04–0,06), `shipping_disruption_level` 2/4 (pewność 1,0: ataki trwają, przepływy utrzymane, rosną koszty), `production_loss_level` 0/4 (pewność 1,0: brak zgłoszonej utraty mocy wg Saudi Aramco). Dwa przebiegi tego dnia (własny `state` i `state` od Gemini, identyczny zestaw 8 pytań) dały ten sam wynik OK, różnice w `noul` ≤ 0,02 |
| 04.11 | Ormuz | model: **OK** – dalsza deeskalacja: tylko 1 atak w listopadzie (wobec 32 w październiku), brak nowych incydentów ostatniej nocy; wszystkie pytania decyzyjne „nie" (0,03–0,04), `shipping_disruption_level` spadł do 0,99/4 (pewność 0,79: rozkład 75% poz. 1 / 13% poz. 0 / 12% poz. 2), `production_loss_level` 0/4. Rynek (War Risk Premium, frachty) pozostawał podwyższony mimo spadku liczby incydentów – rozbieżność uznana za normalne opóźnienie rynku, nie za sprzeczność |
| 07.11 | Ormuz | model: **ALERT** (kod wyjścia 3) – pierwszy alert od 29.10, przerywa serię trzech OK. Nowy incydent UKMTO 196-26 (6.11), a dane Kpler pokazują drastyczny spadek ruchu w cieśninie (kilka–kilkanaście tranzytów dziennie zamiast normalnego wolumenu). `flow_drop_significant` 0,94 → **tak** (bez potrzeby override'u – jednoznaczne), `shipping_disruption_level` skoczył do 3,01/4 (pewność 0,99: „przepływy wyraźnie spadły względem okresu przedwojennego"). Pozostałe pytania decyzyjne nadal „nie", ale `hormuz_transit_halted` wzrosło do **0,26** (z 0,03–0,05 w poprzednich przebiegach) – zbliża się do pasma nierozstrzygniętego 0,3–0,7, wymaga uwagi przy kolejnym pomiarze. `production_loss_level` bez zmian: 0/4 |

Liczby i fakty w raportach pochodzą głównie z mediów streszczających komunikaty IMGW, C3S,
NOAA, PGG, PSE, Kpler, IMO, CENTCOM, UKMTO i Saudi Aramco; nie były weryfikowane u źródła.

## Ustalenia metodyczne

- `state` zawiera wyłącznie fakty ze źródłami; deklaracje stron oddzielone od potwierdzeń;
  bez danych z innego okresu i bez gotowych wniosków.
- Brzmienia pytań w szablonach się nie zmienia – zmiana zrywa porównywalność dzienników
  (`questions_sha256`).
- Odpowiedź tuż przy progu rozstrzyga analityk przez `--override`, nie przez obniżenie progów
  ani przeredagowanie `state`.
- Skale ocenia się po rozkładzie `probabilities`, nie po średniej `score`.
- Przed uruchomieniem payloadu z innego źródła (np. innego modelu) porównać zestaw pytań
  z kanonicznym szablonem programowo (nie "na oko") – 30.10 payload od Gemini początkowo
  używał wycofanej skali `supply_stress_level` zamiast `shipping_disruption_level` +
  `production_loss_level`; drugi przebieg po poprawce dał identyczny `questions_sha256`
  i wynik zgodny z własnym `state`.

## Do powtórzenia po 10.11.2026

- Nowe prognozy C3S i IMGW; rozwój sytuacji z wirem polarnym.
- Ormuz: czy eskalacja z 07.11 (spadek przepływu) się pogłębia czy to chwilowy spadek
  ruchu armatorów po pojedynczym incydencie; pilnie śledzić `hormuz_transit_halted`
  (0,26 na 07.11, blisko pasma nierozstrzygniętego) i czy pojawi się potwierdzenie min
  lub formalne kroki Iranu.

> Dzienniki i payloady z sesji 26.10–07.11 nie są w repozytorium (repozytorium jest
> publiczne); tabela wyników powyżej jest ich podsumowaniem.
