# Jev – status CZEKAĆ / ARM / FIRE dla wykresów Renko (D1, H1, M5)

Ocena wykresów Renko z trzech interwałów według profilu handlowego **R11 2.4-trading-r3**
(reguły `dyscyplina_wykonania`). Podział pracy:

- **Jev** (TypeSafe System One) odpowiada na pytania **opisowe** o wykresy w `state`:
  trend D1 / H1 / M5, kolor ostatniej zamkniętej cegły M5, ostrzeżenia.
- **Kod** (`decide()` w `jev_renko.py`) liczy reguły **liczbowe** profilu z pola `dane`:
  limit dnia, bramka konfluencji, wyzwalacz (%R, SAR), okno płynności, %B, filtr makro,
  ryzyko i RR po kosztach, lot.
- **Rejestr** (`rejestr.py`) prowadzi rejestr transakcji i liczy licznik dnia;
  `jev_renko.py` dopisuje rejestr blokad.

> **Analiza edukacyjna; nie stanowi porady inwestycyjnej.** CFD to instrumenty lewarowane
> wysokiego ryzyka; znaczna większość rachunków detalicznych traci kapitał. Skuteczność
> reguł nie została sprawdzona na danych historycznych – służy temu rejestr.

## 1. Kolejność reguł

| # | Reguła profilu | Źródło | Skutek |
|---|---|---|---|
| 0 | Limit dnia: 2 zamknięte straty z rzędu lub wynik ≤ −2,6% (breakeven < 0,1% neutralny) | rejestr | **SESJA ZAKOŃCZONA** |
| 1 | Kierunek nadrzędny z D1 (zakaz BUY przy SELL D1 i odwrotnie) | Jev | brak kierunku → **CZEKAĆ** |
| 2 | Bramka konfluencji: ≥ 2/3 interwałów zgodnych z D1 | Jev | < 2/3 → **CZEKAĆ** |
| 3 | Wyzwalacz M5: nowy blok w kierunku D1 [Jev] + SELL %R < −30 i SAR nad ceną / BUY %R > −70 i SAR pod ceną [kod] | Jev + kod | brak → **ARM** |
| 4 | Checklista FIRE: [1] wyzwalacz, [2] okno 08:00–23:00 Europe/Warsaw, [3] ryzyko ≤ 1,3% po kosztach, [4] RR ≥ 1,8 po kosztach, [5] %B M5 (SHORT zakazany < 0,05, LONG > 0,95) | kod | NIE → **ARM** + wpis BLOKADA; brak danych → **ARM** |
| 4a | Filtr makro ±15 min od zdarzenia o wysokim wpływie | kod (`dane.makro`) | blokada → **ARM**; brak listy → status „nieznany [E]” |
| 5 | Wszystko TAK | – | **FIRE SELL / FIRE BUY** |

**Ostrzeżenia (nie blokują):** H1 skrajnie wyprzedany / wykupiony oraz cegły tymczasowe
przeciw kierunkowi. Profil ich nie zawiera, a meta-reguła `przeglad_okresowy` dopuszcza
nową regułę blokującą tylko z incydentem lub danymi z rejestru – dlatego są wyłącznie
wyświetlane i zapisywane w dzienniku.

**Ryzyko i RR po kosztach** (bramka 4, filtr 6): realny dystans ryzyka = |SL − entry| + spread;
RR = |TP − entry| / realny dystans; lot = budżet (kapitał × min(ryzyko %, 1,3%)) ÷
(dystans × wartość punktu), zaokrąglony w dół do kroku, nie mniej niż lot minimalny.
Gdy lot minimalny przekracza 1,3% – blokada „ryzyko”. „Świadomie poza oknem”
(`swiadomie_poza_oknem: true`) dopuszcza wejście poza oknem z lotem minimalnym.

## 2. Jak przygotować payload

Skopiuj `renko_template.json`, wypełnij `state` (dla Jev) i `dane` (dla kodu; **nie są
wysyłane do Jev**).

**`state` – fakty z wykresów, dla każdego interwału.** Etykiety przy osi cen: **biała** –
poziom zamknięcia ostatniej zatwierdzonej cegły, **żółta** – bieżąca wartość cegły
tymczasowej (bieżąca cena), **„+N”** – liczba cegieł tymczasowych.

| Element | Przykład | Uwagi |
|---|---|---|
| Data, godzina, instrument | „Stan na 12.11.2026 21:50. Instrument: GOLD.” | Zawsze na początku |
| Wielkość cegły | „cegła 12,6 pkt (ATR 14)” | Platforma przelicza ATR – wielkość się zmienia |
| Cegły zamknięte | „seria czerwonych od 10.11; ostatnia zamknięta 3 880,80 (czerwona)” | Kolor ostatniej cegły |
| Cegły tymczasowe | „bieżąca wartość 3 878,19 (różnica -2,61 pkt, czyli 0,21 cegły)” | **Zawsze podawaj różnicę w punktach i ułamku cegły** |
| Średnia, SAR, MACD, AO, %R, Fisher, %B | „Średnia 3 987,90. SAR 3 947,06. %R -100.” | Liczby, bez ocen |

Nie dodawaj własnych wniosków („trend spadkowy”, „dobry moment”).

**`dane` – liczby dla reguł kodu:**

| Pole | Znaczenie | Potrzebne do |
|---|---|---|
| `instrument`, `czas` | „GOLD”, „RRRR-MM-DD GG:MM” Europe/Warsaw | okno płynności, makro, licznik dnia |
| `m5_pctB`, `m5_pctR`, `m5_sar`, `m5_cena` | odczyty M5; `m5_cena` = żółta etykieta | filtr %B, wyzwalacz |
| `entry`, `sl`, `tp`, `spread` | planowane poziomy i spread [U] | ryzyko, RR |
| `kapital`, `ryzyko_proc`, `wartosc_punktu`, `lot_min`, `lot_krok` | kapitał wolny (PLN), ryzyko % (1,0–1,3), PLN za 1 pkt przy 1 locie | lot, ryzyko |
| `makro` | lista `{"czas": "RRRR-MM-DD GG:MM", "nazwa": "CPI USA"}` lub `null` | filtr makro |
| `swiadomie_poza_oknem` | `true` tylko przy jawnej deklaracji tradera | wyjątek od okna płynności |

Brak pól nie przerywa analizy: status pozostaje ARM z informacją, czego brakuje
(kalkulacja lota bez kapitału i ryzyka jest niedopuszczalna).

## 3. Pytania do Jev

Brzmienie pytań jest w **`renko_template.json`**.

| Pytanie | Co sprawdza |
|---|---|
| `d1_/h1_/m5_bearish`, `d1_/h1_/m5_bullish` | trend: co najmniej 2 z 3 (seria cegieł, cena a średnia, SAR) |
| `m5_sell_trigger`, `m5_buy_trigger` | czy ostatnia zamknięta cegła M5 jest nowym blokiem SELL / BUY |
| `h1_oversold_extreme`, `h1_overbought_extreme` | ostrzeżenie: skrajne oscylatory H1 |
| `h1_/m5_provisional_up`, `h1_/m5_provisional_down` | ostrzeżenie: cegła tymczasowa odbiega od zamkniętej o ≥ pół cegły |

**Ocena analityka (`--override`).** Gdy rozstrzygasz pytanie inaczej niż model, np.
`--override m5_sell_trigger=nie`. Dziennik zapisuje obie oceny, ekran pokazuje też status
bez oceny analityka.

## 4. Uruchomienie

```bash
cd tools/jev-renko
python jev_renko.py renko_RRRR-MM-DD_GGMM.json --dry-run
python jev_renko.py renko_RRRR-MM-DD_GGMM.json --log renko_log.jsonl \
    --rejestr renko_rejestr.jsonl --blokady renko_blokady.jsonl
python rejestr.py dodaj --plik renko_rejestr.jsonl --czas "2026-11-12 22:40" --instr GOLD \
    --kier S --wejscie FIRE --kapital <PLN> --wynik-pln <±PLN> [--rr-plan --rr-real ...]
python rejestr.py licznik --plik renko_rejestr.jsonl --dzien 2026-11-12
python test_offline.py      # 27 testów reguł i rejestru, bez Jev
python test_wariantow.py    # 9 wariantów × 2 przebiegi z Jev
```

Kody wyjścia `jev_renko.py`: `0` CZEKAĆ, `1` błąd, `2` FIRE SELL, `3` FIRE BUY,
`4` SPRAWDŹ, `5` ARM, `6` SESJA ZAKOŃCZONA. `TYPESAFE_API_KEY` jest potrzebny tylko poza
sesją Claude Code w chmurze.

Wpisy BLOKADA i REJESTR są drukowane w formacie wklejki profilu. **Pliki
`renko_log.jsonl`, `renko_rejestr.jsonl`, `renko_blokady.jsonl` i `renko_warianty.csv`
zawierają dane rachunku i są wykluczone z repozytorium** (repozytorium jest publiczne).
Filtr makro nie pobiera kalendarza sam – listę zdarzeń trzeba podać w `dane.makro`.

## 5. Test wariantów (12.11.2026, `jev-1.14.0`)

R1 i R8 to rzeczywiste odczyty GOLD z 12.11.2026 (bez danych rachunku); pozostałe są
syntetyczne, z fikcyjnym kapitałem i wartością punktu.

| Wariant | Treść | Oczekiwany | Otrzymany |
|---|---|---|---|
| R1 | GOLD 19:05: D1, H1, M5 w dół, ostatnia cegła M5 zielona (odbicie) | ARM | ARM ×2 |
| R2 | trend spadkowy 3/3, nowy blok SELL M5, %R -45, SAR nad ceną, RR 2,4 | FIRE SELL | FIRE SELL ×2 |
| R3 | lustrzane odbicie R2 dla BUY | FIRE BUY | FIRE BUY ×2 |
| R4 | jak R2, H1 skrajnie wyprzedany | FIRE SELL (z ostrzeżeniem) | FIRE SELL ×2 |
| R5 | D1 wzrostowy, H1 i M5 spadkowe (konfluencja BUY 1/3) | CZEKAĆ | CZEKAĆ ×2 |
| R6 | jak R2, cegła tymczasowa H1 +0,03 cegły | FIRE SELL | FIRE SELL ×2 |
| R7 | jak R2, cegła tymczasowa M5 +0,88 cegły | FIRE SELL (z ostrzeżeniem) | FIRE SELL ×2 |
| R8 | GOLD 21:50: D1, H1 w dół, M5 w odbiciu (konfluencja 2/3) | ARM | ARM ×2 |
| R9 | jak R2, ale %R -20 (wyzwalacz niepełny) | ARM | ARM ×2 |

Kluczowe odpowiedzi (zakres z dwóch przebiegów):

| Wariant | d1_bear | h1_bear | m5_bear | m5_bull | m5_sell | h1_oversold | m5_prov_up | m5_prov_down |
|---|---|---|---|---|---|---|---|---|
| R1 | **0,82–0,87** | **0,98** | **0,91** | 0,14–0,17 | 0,03–0,04 | **0,97** | 0,06–0,07 | **0,93–0,94** |
| R2 | **0,97** | **0,96** | **0,92–0,93** | 0,04 | **0,97** | 0,06 | 0,05–0,06 | 0,05–0,06 |
| R4 | **0,97** | **0,92–0,93** | **0,97** | 0,03–0,04 | **0,98** | **0,97** | 0,05 | 0,05–0,06 |
| R5 | 0,04–0,05 | **0,95–0,96** | **0,98** | 0,03 | **0,98** | 0,08–0,09 | 0,05 | 0,06 |
| R7 | **0,97** | **0,96** | **0,93–0,94** | 0,04 | **0,96** | 0,06 | **0,76–0,78** | 0,06 |
| R8 | **0,79–0,81** | **0,97** | 0,14–0,20 | **0,89–0,90** | 0,04 | **0,97** | 0,07 | **0,88–0,90** |
| R9 | **0,97** | **0,95–0,96** | **0,91** | 0,04 | **0,97** | 0,05 | 0,06 | 0,05 |

W R3 odpowiedzi `*_bullish` i `m5_buy_trigger` wynoszą 0,94–0,97.

Wnioski:

- 18 z 18 przebiegów dało oczekiwany status; odpowiedzi różnią się między powtórzeniami
  najwyżej o 0,06.
- **Liczby liczy kod, nie Jev.** W pierwszej wersji wyzwalacza Jev oceniał też warunek
  „%R poniżej -30” i odwracał porównanie liczb ujemnych: %R -45 → „nie” (0,12–0,16),
  %R -20 → „tak” (0,71–0,82). Podobnie wcześniej ułamki cegły bez podanej różnicy dawały
  odpowiedzi na granicy (0,61–0,72). Dlatego progi %R, SAR, %B, ryzyko i RR liczy kod,
  a różnicę cegieł tymczasowych trzeba podawać w `state` wprost.
- R1 / R8: zdejmując blokadę H1 (której nie ma w profilu), oba rzeczywiste odczyty dają ARM
  z ostrzeżeniem „H1 skrajnie wyprzedany” zamiast CZEKAJ.
