# Wzór zapytania do Jev – sytuacja w rejonie Cieśniny Ormuz

Szablon do cyklicznej oceny raportów sytuacyjnych narzędziem `jev_run.py`.
Opracowany na podstawie przebiegu z 26.10.2026 (`jev-1.14.0`).

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
| Ataki na żeglugę | liczba ataków w miesiącu, uszkodzone VLCC | Podawaj liczby, nie oceny |
| Miny | „doniesienia o minach” / „miny potwierdzone przez …” | **Odróżniaj doniesienia od potwierdzeń** |
| Przepływy ropy | eksport w mln bbl/d i punkt odniesienia sprzed wojny | Bez punktu odniesienia pytanie o spadek przepływów jest nierozstrzygalne |
| Infrastruktura lądowa | deklaracje stron i to, czy je potwierdzono | Zawsze pisz, kto deklaruje, a kto potwierdza |
| Dyplomacja | mediacje, ultimata, oficjalne zapowiedzi | Cytuj oficjalne komunikaty, jeśli są |
| Rynek | Brent/WTI, fracht, ubezpieczenia | Opcjonalnie; nie jest wejściem do reguły TRIP |

Czego nie dodawać: komentarzy publicystycznych, własnych ocen („sytuacja jest groźna”),
pól bez związku z pytaniami, pustych sekcji. Mogą przesunąć odpowiedzi.

## 3. Pytania (JSON do skopiowania)

Zmieniaj wyłącznie `state`. Brzmienie pytań zostaw bez zmian, żeby wyniki w dzienniku
dały się porównywać (`questions_sha256` musi być stały).

```json
{
  "model": "jev-latest",
  "state": "Stan na DD.MM.RRRR <pora>. <fakty według sekcji 2>",
  "questions": {
    "immediate_closure_probability": {
      "type": "noul",
      "instructions": "Czy według raportu Iran ogłosił zamknięcie Cieśniny Ormuz dla żeglugi handlowej albo przystąpił do jej blokowania?",
      "criteria": {
        "true": "Raport podaje oficjalną zapowiedź zamknięcia cieśniny lub działania, które ją blokują, np. potwierdzone postawienie zapór minowych na torach wodnych.",
        "false": "Raport opisuje ataki na pojedyncze statki i niepotwierdzone doniesienia, a statki nadal przepływają przez cieśninę."
      }
    },
    "hormuz_transit_halted": {
      "type": "noul",
      "instructions": "Czy według raportu tranzyt ropy przez Cieśninę Ormuz jest obecnie faktycznie wstrzymany?",
      "criteria": {
        "true": "Przepływy ropy przez cieśninę spadły niemal do zera.",
        "false": "Tankowce nadal przepływają, a wolumen eksportu utrzymuje się, mimo ataków na statki."
      }
    },
    "mines_confirmed": {
      "type": "noul",
      "instructions": "Czy raport podaje potwierdzone postawienie min morskich w Cieśninie Ormuz?",
      "criteria": {
        "true": "Miny zostały potwierdzone, np. przez marynarkę wojenną lub wskutek wybuchu miny na statku.",
        "false": "Raport wspomina jedynie o doniesieniach lub podejrzeniach dotyczących min."
      }
    },
    "saudi_infrastructure_hit_confirmed": {
      "type": "noul",
      "instructions": "Czy raport podaje potwierdzone uszkodzenie saudyjskiej infrastruktury naftowej na lądzie, np. terminali Yanbu i Rabigh lub rurociągu East-West?",
      "criteria": {
        "true": "Uszkodzenie potwierdziła Arabia Saudyjska lub niezależne źródło.",
        "false": "Raport zawiera tylko deklaracje atakującego, których Arabia Saudyjska nie potwierdza."
      }
    },
    "supply_stress_level": {
      "type": "score",
      "instructions": "Jaki jest obecny poziom zagrożenia dla dostaw ropy z Zatoki Perskiej według raportu?",
      "criteria": [
        "Ataki na statki ustały, a przepływy ropy są w normie.",
        "Zdarzają się sporadyczne incydenty, a przepływy ropy są w normie.",
        "Statki są regularnie atakowane, przepływy utrzymane, rosną koszty frachtu i ubezpieczeń.",
        "Przepływy ropy wyraźnie spadły względem okresu przedwojennego.",
        "Tranzyt jest faktycznie wstrzymany lub trwale utracono duże moce wydobywcze."
      ]
    }
  }
}
```

## 4. Interpretacja i reguła decyzyjna

Progi dla `noul`: **≥ 0,7 = tak**, **≤ 0,3 = nie**, **0,3–0,7 = nierozstrzygnięte**
(raport nie wystarcza do oceny; uzupełnij `state` o źródło, zamiast przeformułowywać pytanie).

| `hormuz_transit_halted` | `immediate_closure_probability` | `mines_confirmed` | Wynik |
|---|---|---|---|
| tak | dowolne | dowolne | **TRIP** – tranzyt wstrzymany |
| nie | tak | tak | **TRIP** – zamknięcie zapowiedziane i wsparte minami |
| nie | tak | nie / nierozstrzygnięte | **ALERT** – zapowiedź bez potwierdzenia; ponów ocenę przy następnym raporcie |
| nie | nie | tak | **ALERT** – miny potwierdzone, brak zapowiedzi zamknięcia |
| nierozstrzygnięte w którejkolwiek kolumnie | | | **SPRAWDŹ** – uzupełnij źródła i powtórz |
| nie | nie | nie | **OK** |

Wskaźniki pomocnicze (nie wchodzą do reguły TRIP, pokazują trend):

- `saudi_infrastructure_hit_confirmed` – sygnał rozszerzenia konfliktu na lądzie,
- `supply_stress_level` – odczytuj **rozkład `probabilities`**, nie tylko średnią `score`;
  dwa maksima (np. na poziomach 2 i 4) oznaczają raport niespójny lub dwuznaczny.

Uwaga: obecna wersja `jev_run.py` sprawdza tylko `immediate_closure_probability ≥ --threshold`.
Pełna tabela powyżej wymaga rozbudowy skryptu albo ręcznego odczytu wyników.

## 5. Uruchomienie

```bash
cd tools/jev-run
python jev_run.py jev_hormuz_RRRR-MM-DD.json --dry-run   # walidacja
TYPESAFE_API_KEY=<klucz> python jev_run.py jev_hormuz_RRRR-MM-DD.json --log jev_log.jsonl
```

Kody wyjścia: `0` – OK, `1` – błąd (walidacja, sieć, HTTP), `2` – TRIP.
Dziennik `jev_log.jsonl` jest wykluczony z repozytorium (`.gitignore`).

## 6. Lista kontrolna przed wysłaniem

- [ ] `state` ma datę i porę stanu.
- [ ] Przepływy podane razem z punktem odniesienia sprzed wojny.
- [ ] Przy każdym incydencie widać, czy to doniesienie, deklaracja czy potwierdzenie.
- [ ] Brak własnych ocen i komentarzy w `state`.
- [ ] Brzmienie pytań niezmienione (porównywalność w dzienniku).
- [ ] `--dry-run` zwraca „Walidacja OK.”.

## 7. Wynik odniesienia (26.10.2026 rano, `jev-1.14.0`)

| Pytanie | Wynik |
|---|---|
| `immediate_closure_probability` | 0,07 |
| `hormuz_transit_halted` | 0,06 |
| `mines_confirmed` | 0,07 |
| `saudi_infrastructure_hit_confirmed` | 0,05 |
| `supply_stress_level` | 2,0 (p = 0,99 dla poziomu 2) |

Reguła z sekcji 4: **OK**. Raport opisywał nasilone ataki przy utrzymanych przepływach
(ok. 24 mln bbl/d wobec przedwojennych 23,3).

> Narzędzie ma charakter analityczny i edukacyjny. Wynik wspiera ocenę sytuacji,
> nie zastępuje analizy eksperckiej ani oficjalnych komunikatów.
