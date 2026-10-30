# Checkpoint – stan na 30.10.2026 (utworzono 29.10.2026)

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
- Ormuz: czy deeskalacja z 30.10 się utrzymuje (przepływ, potwierdzenia min, stanowiska
  Iranu i CENTCOM) czy to chwilowe wyciszenie.

> Dzienniki i payloady z sesji 26–30.10 nie są w repozytorium (repozytorium jest
> publiczne); tabela wyników powyżej jest ich podsumowaniem.
