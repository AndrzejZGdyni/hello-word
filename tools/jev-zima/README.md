# Jev – gotowość domowego ogrzewania na zimę

Ocena raportu o pogodzie, rynku opału i sieci elektroenergetycznej modelem Jev
(TypeSafe System One). Zbudowane na wzór zestawu dla Cieśniny Ormuz
(`../jev-run/WZOR_PYTANIA.md`): Jev odpowiada na pojedyncze pytania o treść raportu,
a poziom zagrożenia wyznacza tabela decyzyjna w kodzie (`decide()` w `jev_zima.py`).

## 1. Zasada działania

- **Jev ocenia treść raportu, nie prognozuje pogody.** Wynik 0,35 nie oznacza 35% szans
  na mrozy, tylko że raport nie rozstrzyga pytania.
- **Jedno pytanie – jedna obserwacja.** Pogoda, opał i sieć są pytane osobno. Poprzednia
  wersja z jedną skalą łączącą trzy wymiary (`winter_infrastructure_stress`) dawałaby
  rozkład z kilkoma maksimami, gdy tylko jeden wymiar się pogarsza (np. braki węgla przy
  łagodnej zimie).
- **Pytania o teraźniejszość i o dalszą perspektywę są rozdzielone.** „Ryzyko rozbicia
  wiru polarnego w styczniu” i „mróz w najbliższym tygodniu” to dwa różne pytania;
  połączone dawały wynik nierozstrzygnięty (0,35 w pierwszym teście z 28.10.2026).

## 2. Jak przygotować `state`

| Element | Przykład | Uwagi |
|---|---|---|
| Data stanu | „Stan na 05.12.2026.” | Zawsze na początku |
| Pogoda na najbliższy tydzień | temperatury wg IMGW, ostrzeżenia | **Podawaj normę** dla porównania; samo „1–5°C” jest dwuznaczne |
| Prognoza sezonowa | ECMWF/NOAA, wir polarny | Pisz, którego okresu dotyczy |
| Dostępność węgla | e-sklep PGG, składy, limity | Odróżniaj dostępność w sprzedaży od terminów dostaw |
| Dostawy | czas realizacji zamówień | Podawaj liczbę dni lub tygodni opóźnienia |
| Sieć | komunikaty PSE, rezerwa mocy, stopnie zasilania | Odróżniaj ogłoszone ograniczenia od możliwych w przyszłości |

Nie dodawaj własnych ocen („sytuacja jest groźna”) ani gotowych wniosków.

## 3. Pytania

Brzmienie pytań jest w **`zima_template.json`**. Przy każdej ocenie skopiuj plik
i zmień tylko `state`.

| Pytanie | Co sprawdza |
|---|---|
| `vortex_disruption_risk` | ryzyko rozbicia wiru polarnego w nadchodzącej zimie |
| `cold_wave_imminent` | silna fala mrozów teraz lub w ciągu 7 dni |
| `coal_unavailable` | braki węgla w sprzedaży lub limity zakupu |
| `coal_delivery_delays` | opóźnienia dostaw zamówionego opału |
| `grid_emergency_measures` | ogłoszone stopnie zasilania lub apel o ograniczenie poboru |
| `grid_reserve_low` | niska rezerwa mocy według operatora |

## 4. Tabela decyzyjna

Progi noul: **≥ 0,7 = tak**, **≤ 0,3 = nie**, pomiędzy = nierozstrzygnięte.
Wiersze sprawdzane od góry; wygrywa pierwszy pasujący.

| # | Warunek | Wynik |
|---|---|---|
| 1 | `cold_wave_imminent` = tak oraz (`coal_unavailable` = tak lub `grid_emergency_measures` = tak) | **KRYTYCZNE** |
| 2 | `coal_unavailable` = tak | **ALERT** – braki węgla w sprzedaży |
| 3 | `grid_emergency_measures` = tak | **ALERT** – stopnie zasilania lub apel |
| 4 | `cold_wave_imminent` = tak | **ALERT** – fala mrozów teraz lub w ciągu 7 dni |
| 5 | `coal_delivery_delays` = tak lub `grid_reserve_low` = tak | **UWAGA** |
| 6 | `vortex_disruption_risk` = tak | **UWAGA** – ryzyko w dalszej perspektywie |
| 7 | którakolwiek odpowiedź nierozstrzygnięta | **SPRAWDŹ** – uzupełnij `state` |
| 8 | pozostałe | **OK** |

**Ocena analityka (`--override`).** Gdy rozstrzygasz pytanie decyzyjne inaczej niż model,
podaj to jawnie, np. `--override coal_unavailable=nie` (węgiel wyprzedaje się, ale jest
uzupełniany codziennie). Odpowiedź modelu i progi pozostają bez zmian; dziennik zapisuje
w `decision.overrides` ocenę analityka, klasyfikację modelu i wartość noul, a na ekranie
widać też wynik bez ocen analityka.

## 5. Uruchomienie

```bash
cd tools/jev-zima
python jev_zima.py zima_RRRR-MM-DD.json --dry-run
TYPESAFE_API_KEY=<klucz> python jev_zima.py zima_RRRR-MM-DD.json --log zima_log.jsonl
TYPESAFE_API_KEY=<klucz> python jev_zima.py zima_RRRR-MM-DD.json --override coal_unavailable=nie
TYPESAFE_API_KEY=<klucz> python test_wariantow.py   # 5 wariantów × 3 przebiegi
```

Kody wyjścia: `0` OK, `1` błąd, `2` KRYTYCZNE, `3` ALERT, `4` SPRAWDŹ, `5` UWAGA.
`TYPESAFE_API_KEY` jest potrzebny tylko poza sesją Claude Code w chmurze.
Pliki `zima_log.jsonl` i `zima_warianty.csv` są wykluczone z repozytorium.

## 6. Test wariantów (28.10.2026, `jev-1.14.0`)

| Wariant | Treść `state` | Oczekiwany | Otrzymany |
|---|---|---|---|
| Z0 | raport z 28.10: grudzień w normie, ryzyko rozbicia wiru w styczniu–lutym, opał i sieć stabilne | UWAGA | UWAGA ×3 |
| Z1 | ciepło, brak sygnałów wiru, opał dostępny, sieć stabilna | OK | OK ×3 |
| Z2 | węgiel niedostępny w e-sklepie, limity na składach, zima łagodna | ALERT | ALERT ×3 |
| Z3 | mróz do −22°C, 11. stopień zasilania i apel PSE | KRYTYCZNE | KRYTYCZNE ×3 |
| Z4 | węgiel dostępny, dostawy opóźnione o 2–3 tygodnie | UWAGA | UWAGA ×3 |

Kluczowe odpowiedzi (zakres z trzech przebiegów):

| Wariant | vortex | cold_wave | coal_unavailable | delays | grid_emergency | grid_reserve |
|---|---|---|---|---|---|---|
| Z0 | **0,96** | 0,06–0,07 | 0,03 | 0,04 | 0,05–0,06 | 0,05 |
| Z1 | 0,05–0,06 | 0,04 | 0,04 | 0,04 | 0,04–0,05 | 0,04 |
| Z2 | 0,06 | 0,25–0,30 | **0,91–0,94** | 0,15–0,20 | 0,04 | 0,04–0,05 |
| Z3 | 0,09–0,10 | **0,96–0,97** | 0,13–0,14 | **0,94–0,95** | **0,99** | **0,79–0,81** |
| Z4 | 0,05 | 0,05 | 0,23–0,24 | **0,85–0,87** | 0,04 | 0,04 |

Wnioski:

- 15 z 15 przebiegów dało oczekiwaną decyzję; odpowiedzi różnią się między
  powtórzeniami najwyżej o 0,05.
- Rozdzielenie pytania o wir polarny od pytania o bieżące mrozy rozstrzygnęło raport
  z 28.10: ryzyko w dalszej perspektywie 0,96, mróz w najbliższym tygodniu 0,06–0,07.
- Z2: `cold_wave_imminent` 0,25–0,30 leży tuż przy progu „nie”. Raport podawał
  „1–5°C” bez normy; podanie normy (sekcja 2) powinno to rozstrzygnąć.
- Z3: `grid_reserve_low` 0,79–0,81, choć raport nie podaje wielkości rezerwy – model
  wnioskuje ją ze stopni zasilania. Nie zmienia to decyzji (reguła 1 ma pierwszeństwo).

> Narzędzie ma charakter edukacyjny. Nie zastępuje komunikatów IMGW, PSE ani
> lokalnych służb.
