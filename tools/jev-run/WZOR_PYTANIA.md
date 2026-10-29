# Wzór zapytania do Jev – sytuacja w rejonie Cieśniny Ormuz

Szablon do cyklicznej oceny raportów sytuacyjnych narzędziem `jev_run.py`.
Opracowany na podstawie przebiegów z 26–27.10.2026 (`jev-1.14.0`): wersje v1–v4
oraz test wariancji W1–W4 (sekcja 8).

## 1. Zasada działania

- **Jev ocenia treść raportu, nie prognozuje zdarzeń.** `noul` to prawdopodobieństwo,
  że stwierdzenie jest prawdziwe w świetle danych przesłanych w `state`. Wynik
  „OK” znaczy „raport nie opisuje zamknięcia cieśniny”, a nie „zamknięcia nie będzie”.
- **Jev dostarcza obserwacje, decyzję podejmuje kod.** Każde pytanie dotyczy jednego
  faktu, który da się wskazać w tekście. Reguła TRIP jest zapisana w tabeli prawdy
  (sekcja 4).
- **Pytania są oceniane niezależnie.** Żadne nie widzi odpowiedzi na pozostałe;
  wspólny kontekst musi się znaleźć w `state`.

## 2. Jak przygotować `state`

Jeden akapit, maks. kilkanaście zdań, z datą i porą stanu. Zawiera wyłącznie fakty
potrzebne do odpowiedzi na pytania:

| Element | Przykład | Uwagi |
|---|---|---|
| Data i pora stanu | „Stan na 26.10.2026 rano.” | Zawsze na początku |
| Ataki na żeglugę | liczba ataków w miesiącu i od początku wojny, uszkodzone VLCC | **Wymagane** dla `shipping_disruption_level`; podawaj liczby, nie oceny |
| Koszty frachtu i ubezpieczeń | War Risk Premium, stawki frachtu | **Wymagane** dla `shipping_disruption_level` (sekcja 7) |
| Miny | „doniesienia o minach” / „miny potwierdzone przez …” | **Odróżniaj doniesienia od potwierdzeń** |
| Przepływy ropy | przepływ przez cieśninę w mln bbl/d i punkt odniesienia sprzed wojny | **Wymagane** dla `flow_drop_significant`; bez punktu odniesienia pytanie jest nierozstrzygalne |
| Utrata mocy wydobywczych i przetwórczych | wielkość w mln bbl/d i przewidywany czas | Dla `production_loss_level`; podawaj, kto potwierdza |
| Infrastruktura lądowa | deklaracje stron i to, czy je potwierdzono | Zawsze pisz, kto deklaruje, a kto potwierdza |
| Dyplomacja | mediacje, ultimata, oficjalne zapowiedzi | Cytuj oficjalne komunikaty, jeśli są |
| Rynek | Brent/WTI, fracht, ubezpieczenia | Opcjonalnie; nie jest wejściem do reguły TRIP |

Przy każdej liczbie podawaj źródło („według IMO”, „według danych Kpler”). Fakty oddzielaj
od deklaracji stron: kto deklaruje, kto potwierdza, kto zaprzecza.

Czego nie dodawać: komentarzy publicystycznych, własnych ocen („sytuacja jest groźna”),
gotowych wniosków odpowiadających wprost na pytania („tranzyt nie został wstrzymany”),
pól bez związku z pytaniami, pustych sekcji. Mogą przesunąć odpowiedzi.

Przykładowy `state` (wersja v4 z 26.10.2026, wzorcowa):

> Stan na 26.10.2026 rano. Według danych Washington Institute w październiku odnotowano
> 28 ataków na statki handlowe (113 od 28 lutego), a według IMO w październiku uszkodzono
> 11 supertankowców VLCC (ponad 30 od początku wojny). Według danych Kpler średni eksport
> ropy z Bliskiego Wschodu wynosi ponad 24 mln bbl/d wobec przedwojennego poziomu
> 23,3 mln bbl/d. Ruch Huti zadeklarował uderzenia na saudyjski obiekt Aramco w Yanbu,
> rafinerię Rabigh oraz rurociąg East-West; Arabia Saudyjska nie potwierdziła tych
> doniesień. W oficjalnych komunikatach wojskowych brak potwierdzenia postawienia min
> morskich oraz brak oficjalnych zapowiedzi Iranu o zamknięciu Cieśniny Ormuz. Stawki
> ubezpieczeń od ryzyka wojennego (War Risk Premium) oraz koszty frachtu wzrosły,
> natomiast w Teheranie rozpoczęły się rozmowy z mediatorami z Kataru, a notowania WTI
> na otwarciu sesji spadły z 103,27 USD do 101,65 USD.

## 3. Pytania

Brzmienie pytań jest przechowywane w jednym miejscu: **`jev_hormuz_template.json`**.
Przy każdej analizie skopiuj ten plik i zmień wyłącznie `state`. Brzmienia pytań nie
zmieniaj, żeby wyniki w dzienniku dały się porównywać (`questions_sha256` musi być stały;
obecny zestaw: `1780910a27e1a438`).

| Pytanie | Typ | Rola | Co sprawdza |
|---|---|---|---|
| `hormuz_transit_halted` | noul | decyzyjne | czy tranzyt ropy jest faktycznie wstrzymany |
| `immediate_closure_probability` | noul | decyzyjne | czy Iran ogłosił zamknięcie albo przystąpił do blokowania |
| `mines_confirmed` | noul | decyzyjne | czy postawienie min jest potwierdzone, a nie tylko zgłaszane |
| `flow_drop_significant` | noul | decyzyjne | czy przepływ przez cieśninę jest co najmniej o 10% niższy niż przed wojną |
| `formal_closure_steps` | noul | decyzyjne | czy organy Iranu podjęły formalne kroki ku zamknięciu bez wiążącej decyzji |
| `saudi_infrastructure_hit_confirmed` | noul | pomocnicze | czy uszkodzenie lądowej infrastruktury saudyjskiej jest potwierdzone |
| `shipping_disruption_level` | score 0–4 | pomocnicze | zakłócenie żeglugi i przepływu przez cieśninę |
| `production_loss_level` | score 0–4 | decyzyjne (poziom dominujący) | utrata mocy wydobywczych lub przetwórczych w państwach Zatoki |

Wcześniejsza skala `supply_stress_level` łączyła na poziomie 4 wstrzymanie tranzytu
z utratą wydobycia i dawała rozkład z dwoma maksimami, gdy tylko jedno z nich zachodziło
(sekcja 8, W3). Zastąpiły ją dwie osobne skale.

## 4. Interpretacja i reguła decyzyjna

Progi dla `noul`: **≥ 0,7 = tak**, **≤ 0,3 = nie**, **0,3–0,7 = nierozstrzygnięte**
(raport nie wystarcza do oceny; uzupełnij `state` o źródło, zamiast przeformułowywać pytanie).

Wiersze są sprawdzane od góry; wygrywa pierwszy pasujący.

| # | Warunek | Wynik |
|---|---|---|
| 1 | `hormuz_transit_halted` = tak | **TRIP** – tranzyt wstrzymany |
| 2 | halted = nie, `immediate_closure_probability` = tak, `mines_confirmed` = tak | **TRIP** – zamknięcie zapowiedziane i wsparte minami |
| 3 | halted = nie, closure = tak | **ALERT** – zapowiedź bez potwierdzenia min |
| 4 | halted = nie, closure = nie, mines = tak | **ALERT** – miny potwierdzone, brak zapowiedzi |
| 5 | halted = nie, `flow_drop_significant` = tak | **ALERT** – wyraźny spadek przepływów bez wstrzymania |
| 6 | halted = nie, closure = nie, `formal_closure_steps` = tak | **ALERT** – formalne kroki ku zamknięciu bez decyzji |
| 7 | dominujący poziom `production_loss_level` ≥ 3 (utrata ≥ ok. 1 mln bbl/d) | **ALERT** – duża utrata mocy wydobywczych lub przetwórczych |
| 8 | którakolwiek odpowiedź noul decyzyjna nierozstrzygnięta lub brakująca | **SPRAWDŹ** – uzupełnij źródła i powtórz |
| 9 | pozostałe | **OK** |

Reguła 7 rozszerza zakres narzędzia poza samą cieśninę: duża utrata mocy w państwach
Zatoki zagraża dostawom także przy normalnym tranzycie. Poziom dominujący to poziom
o najwyższym prawdopodobieństwie w `probabilities`, nie średnia `score`. Próg ustawia
stała `PRODUCTION_ALERT_LEVEL` w `jev_run.py`.

Dziennik zapisuje tylko pierwszy pasujący powód. Gdy ALERT ma kilka przyczyn (np. W4:
spadek przepływów i formalne kroki), pozostałe widać w polu `decision.inputs`.

Wskaźniki pomocnicze (nie wchodzą do tabeli, pokazują tło i trend):

- `saudi_infrastructure_hit_confirmed` – sygnał rozszerzenia konfliktu na lądzie,
- `shipping_disruption_level` (oraz `production_loss_level` poza regułą 7) – odczytuj **rozkład
  `probabilities`**, nie średnią `score`. Dwa maksima oznaczają raport niespójny lub
  dwuznaczny; średnia leży wtedy między nimi i nie odpowiada żadnemu opisowi.

Tabelę realizuje funkcja `decide()` w `jev_run.py`. Wynik, uzasadnienie i sklasyfikowane
wejścia trafiają do dziennika w polu `decision`. Progi zmienia się opcjami `--yes` i `--no`.

**Ocena analityka (`--override`).** Gdy analityk rozstrzyga pytanie decyzyjne inaczej niż
model, np. uznaje komunikat IMO za potwierdzenie min, podaje to jawnie:
`--override mines_confirmed=tak`. Odpowiedź modelu i progi pozostają bez zmian; dziennik
zapisuje w `decision.overrides` ocenę analityka, klasyfikację modelu i wartość noul,
a na ekranie widać też wynik bez ocen analityka. Nie zastępuj tej opcji obniżaniem progów
ani przeredagowaniem `state` pod oczekiwaną odpowiedź.

## 5. Uruchomienie

```bash
cd tools/jev-run
python jev_run.py jev_hormuz_RRRR-MM-DD.json --dry-run   # walidacja
TYPESAFE_API_KEY=<klucz> python jev_run.py jev_hormuz_RRRR-MM-DD.json --log jev_log.jsonl
# progi inne niż domyślne 0,7 / 0,3:
TYPESAFE_API_KEY=<klucz> python jev_run.py jev_hormuz_RRRR-MM-DD.json --yes 0.8 --no 0.2
# ocena analityka dla pytania decyzyjnego (można podać kilka razy):
TYPESAFE_API_KEY=<klucz> python jev_run.py jev_hormuz_RRRR-MM-DD.json --override mines_confirmed=tak
```

Kody wyjścia: `0` – OK, `1` – błąd (walidacja, sieć, HTTP), `2` – TRIP, `3` – ALERT,
`4` – SPRAWDŹ. Walidacja odrzuca payload bez któregoś z pięciu pytań decyzyjnych noul
lub bez skali `production_loss_level`.
Dziennik `jev_log.jsonl` jest wykluczony z repozytorium (`.gitignore`).

Test wariancji (warianty V4 i W1–W4, po 5 przebiegów, ok. 25 zapytań):

```bash
TYPESAFE_API_KEY=<klucz> python jev_variance_test.py
```

Wyniki trafiają do `jev_variance_raw.csv` i `jev_variance_summary.csv` (rozkłady
zamiast średnich); oba pliki są wykluczone z repozytorium.

## 6. Lista kontrolna przed wysłaniem

- [ ] `state` ma datę i porę stanu.
- [ ] Podana liczba ataków oraz informacja o kosztach frachtu i ubezpieczeń.
- [ ] Przy każdej liczbie podane źródło.
- [ ] Przepływy podane razem z punktem odniesienia sprzed wojny.
- [ ] Przy każdym incydencie widać, czy to doniesienie, deklaracja czy potwierdzenie.
- [ ] Brak własnych ocen i komentarzy w `state`.
- [ ] Brzmienie pytań niezmienione (porównywalność w dzienniku).
- [ ] `--dry-run` zwraca „Walidacja OK.”.

## 7. Wyniki odniesienia i test stabilności (26.10.2026, `jev-1.14.0`)

Cztery wersje `state` opisujące ten sam stan faktyczny, przy **poprzednim** zestawie
pytań (`questions_sha256 = 71917c473bbd246d`, ze skalą `supply_stress_level`):

| Wersja | Charakterystyka `state` |
|---|---|
| v1 | Pierwotny raport: 28 ataków, „doniesienia o minach”, ceny Brent i WTI |
| v2 | Gotowe wnioski („tranzyt nie został wstrzymany”); **brak** liczby ataków i kosztów ubezpieczeń |
| v3 | Przywrócone: 28 ataków (rekord), wzrost War Risk Premium, szczyty Brent |
| v4 | Jak v3, plus źródło przy każdej liczbie i sumy od początku wojny (**wzorcowa**, sekcja 2) |

| Pytanie | v1 | v2 | v3 | v4 |
|---|---|---|---|---|
| `immediate_closure_probability` | 0,07 | 0,04 | 0,05 | 0,04 |
| `hormuz_transit_halted` | 0,06 | 0,04 | 0,07 | 0,05 |
| `mines_confirmed` | 0,07 | 0,04 | 0,05 | 0,05 |
| `saudi_infrastructure_hit_confirmed` | 0,05 | 0,05 | 0,07 | 0,05 |
| `supply_stress_level` | 2,0 (p₂ = 0,99) | **1,58** (p₁ = 0,42, p₂ = 0,58) | 2,0 (p₂ = 1,00) | 2,0 (p₂ = 1,00) |

Wnioski:

- Pytania tak/nie są stabilne: różne wersje tekstu dają wyniki 0,04–0,07, daleko poniżej
  progu 0,3. Różnice rzędu ±0,03 to zwykłe wahania, nie zmiana oceny.
- W v2 `supply_stress_level` ma dwa maksima, bo poziom 2 wymaga regularnych ataków
  i rosnących kosztów, a `state` tego nie podawał. Po uzupełnieniu danych (v3, v4) rozkład
  wraca do jednego maksimum. **Brakujące dane uzupełnia się w `state`, nie w pytaniu.**
- Wszystkie wersje: reguła z sekcji 4 daje **OK**. Raport opisywał nasilone ataki przy
  utrzymanych przepływach (ok. 24 mln bbl/d wobec przedwojennych 23,3).
- Liczby i przypisane im źródła pochodzą z raportu wejściowego; nie były weryfikowane.

## 8. Test wariancji W1–W4 (27.10.2026, `jev-1.14.0`)

Cztery hipotetyczne raporty z 28.10.2026, każdy uruchomiony 5 razy, oraz V4 (sekcja 2)
jako kontrola regresji. Skrypt: `jev_variance_test.py`.

| Wariant | Treść `state` | Oczekiwany wynik |
|---|---|---|
| V4 | stan wzorcowy z 26.10 | OK |
| W1 | wybuch miny potwierdzony przez US 5th Fleet, przepływ 17 / 20,5 mln bbl/d | ALERT |
| W2 | przepływ 12,3 / 20,5 mln bbl/d, część armatorów wstrzymała rejsy | ALERT |
| W3 | Aramco potwierdza uszkodzenie Abqaiq (−5 mln bbl/d), tranzyt w normie | ALERT (reguła 7) |
| W4 | rezolucja parlamentu Iranu bez decyzji Rady, obiekt na torze niepotwierdzony, przepływ −15% | ALERT |

**Przebieg 1 – poprzedni zestaw pytań** (`71917c473bbd246d`, 20 przebiegów):

| Wariant | Decyzja | Wada |
|---|---|---|
| W1 | ALERT ×5 | – |
| W2 | **OK** ×5 | tabela nie uwzględniała spadku przepływów (stress = 3 był tylko pomocniczy) |
| W3 | OK ×5 | `saudi_infrastructure_hit_confirmed` = 0,60–0,62 (pytanie wymieniało z nazwy tylko Yanbu, Rabigh i East-West); `supply_stress_level` rozdzielony między poziomy 0 (p ≈ 0,46) i 4 (p ≈ 0,30), średnia 1,65–2,04 |
| W4 | **OK** ×5 | tabela nie uwzględniała spadku przepływów ani formalnych kroków |

**Przebieg 2 – obecny zestaw pytań** (`1780910a27e1a438`, 25 przebiegów):

| Wariant | halted | closure | mines | flow_drop | steps | saudi | shipping | production | Decyzja |
|---|---|---|---|---|---|---|---|---|---|
| V4 | 0,05 | 0,04 | 0,05 | 0,05 | 0,06–0,07 | 0,05 | 2 (p = 1,00) | 0 (p ≥ 0,99) | OK ×5 |
| W1 | 0,06 | 0,10–0,11 | **0,94–0,95** | **0,94–0,97** | 0,05 | 0,04 | 3 (p = 1,00) | 0 (p ≈ 0,77) | ALERT ×5 |
| W2 | 0,06–0,07 | 0,04 | 0,05 | **0,96–0,97** | 0,06 | 0,05 | 3 (p = 1,00) | 0 (p ≈ 0,94) | ALERT ×5 |
| W3 | 0,03 | 0,03 | 0,03 | 0,07 | 0,04 | **0,94** | 0 (p = 1,00) | **4 (p = 1,00)** | OK ×5 → **ALERT** ×5 z regułą 7 |
| W4 | 0,08–0,09 | 0,08–0,09 | 0,06–0,07 | **0,96** | **0,92–0,93** | 0,03–0,04 | 3 (p ≈ 0,98) | 0 (p = 1,00) | ALERT ×5 |

Wnioski:

- Decyzje są powtarzalne: 45 z 45 przebiegów dało w obrębie wariantu tę samą decyzję.
  Odpowiedzi noul różnią się między powtórzeniami najwyżej o 0,03.
- Rozdzielenie skali usunęło rozkład z dwoma maksimami w W3: żegluga 0, utrata mocy 4.
  Ogólna kategoria obiektów w kryterium podniosła `saudi_infrastructure_hit_confirmed`
  w W3 z 0,61 do 0,94.
- V4 nadal daje OK, więc zmiany nie wprowadziły fałszywych alarmów dla stanu z 26.10.
- W1: `production_loss_level` ma niewielką domieszkę poziomu 4 (p ≈ 0,16), bo spadek
  przepływu przez cieśninę bywa odczytywany jako utrata mocy. Dominujący poziom 0 jest
  poprawny; to kolejny powód, by czytać rozkład, a nie średnią (0,74–0,89).
- W3 (potwierdzona utrata 5 mln bbl/d mocy przetwórczych przy normalnym tranzycie)
  dawał OK, bo tabela obejmowała tylko cieśninę. Po dodaniu reguły 7 (sekcja 4) daje
  **ALERT** ×5. Wynik ustalono, przeliczając zapisane 25 odpowiedzi przebiegu 2 nową
  funkcją `decide()`, bez ponownych zapytań do API; decyzje V4, W1, W2 i W4 bez zmian.

> Narzędzie ma charakter analityczny i edukacyjny. Wynik wspiera ocenę sytuacji,
> nie zastępuje analizy eksperckiej ani oficjalnych komunikatów.
