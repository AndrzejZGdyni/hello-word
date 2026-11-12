# Jev – decyzja KUP / SPRZEDAJ / CZEKAJ dla wykresów Renko

Ocena opisu wykresów Renko z trzech interwałów (D1, H1, M5) modelem Jev
(TypeSafe System One). Zbudowane na wzór `../jev-zima/`: Jev odpowiada na pojedyncze
pytania o opis wykresów w `state`, decyzję wyznacza tabela decyzyjna w kodzie
(`decide()` w `jev_renko.py`).

> **Narzędzie interpretuje zestaw wskaźników; nie jest rekomendacją inwestycyjną.**
> CFD to instrumenty z dźwignią; większość rachunków detalicznych traci na nich pieniądze.
> Skuteczność reguł nie została sprawdzona na danych historycznych.

## 1. Zasada działania

- **Kierunek z D1 i H1, wejście z M5.** Sprzedaż tylko przy trendzie spadkowym na D1
  i H1 oraz sygnale na M5; kupno symetrycznie. W pozostałych przypadkach CZEKAJ.
- **Trend tylko z zamkniętych cegieł.** Tymczasowe (żółte) cegły zmieniają się do końca
  interwału, dlatego służą wyłącznie jako ostrzeżenie (pytania `provisional_*`).
- **Bez wejścia po dużym ruchu.** Sygnał sprzedaży przy skrajnym wyprzedaniu H1
  (albo kupna przy skrajnym wykupieniu) daje CZEKAJ.
- **Jev ocenia opis, nie rynek.** Wynik 0,5 oznacza, że opis nie rozstrzyga pytania,
  a nie 50% szans na ruch ceny.

## 2. Jak przygotować `state`

Dla każdego interwału (D1, H1, M5) podaj fakty odczytane z wykresu:

| Element | Przykład | Uwagi |
|---|---|---|
| Data, godzina, instrument | „Stan na 12.11.2026 19:05. Instrument: GOLD.” | Zawsze na początku |
| Wielkość cegły | „cegła ok. 15 pkt (ATR 14)” | |
| Cegły zamknięte | „seria czerwonych od 10.11; ostatnia zamknięta 3 872,58 (czerwona)” | Kolor i kierunek serii |
| Cegły tymczasowe | „bieżąca tymczasowa cegła 3 877,90” | Wartość z żółtej etykiety |
| Średnia krocząca, Parabolic SAR | „Średnia 4 003,92. SAR 3 962,33.” | Liczby, bez oceny „nad / pod” |
| MACD, AO | „MACD poniżej sygnału, histogram -17,07; AO -125,82, czerwone” | |
| Williams %R, Fisher, BB %B | „%R -100. Fisher -7,23, sygnał -6,86. %B 0,06.” | Kierunek Fishera i przecięcia |

Nie dodawaj własnych wniosków („trend spadkowy”, „dobry moment”). Zrzuty rób tuż po
zamknięciu interwału; zakryj saldo i numer rachunku.

## 3. Pytania

Brzmienie pytań jest w **`renko_template.json`**. Przy każdej ocenie skopiuj plik
i zmień tylko `state`.

| Pytanie | Co sprawdza |
|---|---|
| `d1_bearish`, `d1_bullish` | trend D1: co najmniej 2 z 3 (seria cegieł, cena a średnia, SAR) |
| `h1_bearish`, `h1_bullish` | to samo dla H1 |
| `m5_sell_trigger`, `m5_buy_trigger` | zamknięta cegła w kierunku wejścia oraz przecięcie Fishera albo odwrócenie SAR |
| `h1_oversold_extreme` | %R ≤ -95 oraz Fisher < -4 albo %B < 0,10 |
| `h1_overbought_extreme` | %R ≥ -5 oraz Fisher > 4 albo %B > 0,90 |
| `provisional_up`, `provisional_down` | kierunek tymczasowych cegieł na H1 lub M5 |

## 4. Tabela decyzyjna

Progi noul: **≥ 0,7 = tak**, **≤ 0,3 = nie**, pomiędzy = nierozstrzygnięte.
Wiersze sprawdzane od góry; wygrywa pierwszy pasujący. Kupno działa symetrycznie
do sprzedaży (`*_bullish`, `m5_buy_trigger`, `h1_overbought_extreme`, `provisional_down`).

| # | Warunek | Wynik |
|---|---|---|
| 1 | trend jednocześnie spadkowy i wzrostowy na D1 i H1 | **SPRAWDŹ** |
| 2 | `d1_bearish` i `h1_bearish` = tak, `m5_sell_trigger` = nie | **CZEKAJ** – brak sygnału na M5 |
| 3 | jak 2, ale `m5_sell_trigger` nierozstrzygnięte | **SPRAWDŹ** |
| 4 | jak 2, `m5_sell_trigger` = tak, `h1_oversold_extreme` = tak | **CZEKAJ** – H1 skrajnie wyprzedany |
| 5 | jak 4, ale `provisional_up` = tak | **CZEKAJ** – tymczasowe cegły przeciw |
| 6 | jak 4, ale wyprzedanie lub cegły tymczasowe nierozstrzygnięte | **SPRAWDŹ** |
| 7 | trend spadkowy D1+H1, sygnał M5, brak przeszkód | **SPRZEDAJ** |
| 8 | wiersze 2–7 dla trendu wzrostowego | **CZEKAJ / SPRAWDŹ / KUP** |
| 9 | trend D1 lub H1 nierozstrzygnięty | **SPRAWDŹ** |
| 10 | pozostałe (D1 i H1 bez wspólnego kierunku) | **CZEKAJ** |

**Ocena analityka (`--override`).** Gdy rozstrzygasz pytanie inaczej niż model, podaj to
jawnie, np. `--override m5_sell_trigger=nie`. Dziennik zapisuje ocenę analityka obok
odpowiedzi modelu, a na ekranie widać też wynik bez tej oceny.

## 5. Uruchomienie

```bash
cd tools/jev-renko
python jev_renko.py renko_RRRR-MM-DD_GGMM.json --dry-run
TYPESAFE_API_KEY=<klucz> python jev_renko.py renko_RRRR-MM-DD_GGMM.json --log renko_log.jsonl
TYPESAFE_API_KEY=<klucz> python test_wariantow.py   # 5 wariantów × 2 przebiegi
```

Kody wyjścia: `0` CZEKAJ, `1` błąd, `2` SPRZEDAJ, `3` KUP, `4` SPRAWDŹ.
`TYPESAFE_API_KEY` jest potrzebny tylko poza sesją Claude Code w chmurze.
Pliki `renko_log.jsonl` i `renko_warianty.csv` są wykluczone z repozytorium.

## 6. Test wariantów (12.11.2026, `jev-1.14.0`)

| Wariant | Treść `state` | Oczekiwany | Otrzymany |
|---|---|---|---|
| R1 | rzeczywisty odczyt GOLD 19:05: D1 i H1 w dół, H1 skrajnie wyprzedany, odbicie na M5 | CZEKAJ | CZEKAJ ×2 |
| R2 | trend spadkowy D1+H1, nowa czerwona cegła M5 po odbiciu, H1 bez skrajności | SPRZEDAJ | SPRZEDAJ ×2 |
| R3 | lustrzane odbicie R2 dla trendu wzrostowego | KUP | KUP ×2 |
| R4 | jak R2, ale H1 skrajnie wyprzedany (%R -100, Fisher -6,2, %B 0,04) | CZEKAJ | CZEKAJ ×2 |
| R5 | D1 wzrostowy, H1 spadkowy | CZEKAJ | CZEKAJ ×2 |

Kluczowe odpowiedzi (zakres z dwóch przebiegów):

| Wariant | d1_bear | d1_bull | h1_bear | h1_bull | m5_sell | m5_buy | h1_oversold | prov_up | prov_down |
|---|---|---|---|---|---|---|---|---|---|
| R1 | **0,73–0,78** | 0,17–0,18 | **0,98** | 0,04 | 0,05–0,06 | **0,90** | **0,97** | **0,81–0,82** | 0,32–0,49 |
| R2 | **0,97** | 0,04 | **0,96** | 0,05 | **0,96** | 0,03 | 0,05 | 0,07 | 0,05–0,06 |
| R3 | 0,03 | **0,96–0,97** | 0,04 | **0,97** | 0,03 | **0,96** | 0,03 | 0,06 | 0,05 |
| R4 | **0,97–0,98** | 0,03–0,04 | **0,95–0,96** | 0,06–0,07 | **0,97** | 0,03 | **0,97** | 0,05 | 0,05–0,06 |
| R5 | 0,05–0,06 | **0,97** | **0,97** | 0,04 | **0,96** | 0,03–0,04 | 0,08–0,09 | 0,07–0,08 | 0,06–0,07 |

Wnioski:

- 10 z 10 przebiegów dało oczekiwaną decyzję; odpowiedzi różnią się między
  powtórzeniami najwyżej o 0,17 (`provisional_down` w R1), w pozostałych o ≤ 0,05.
- R1: `d1_bearish` 0,73–0,78 leży blisko progu. Ostatnie zamknięte cegły D1 są zielone
  (odbicie), więc trend wynika z ceny pod średnią i serii spadkowej sprzed odbicia.
  Po zamknięciu sesji z czerwonymi cegłami odpowiedź powinna wzrosnąć.
- R1: `provisional_down` nierozstrzygnięte, bo tymczasowe cegły biegną różnie na H1
  (w górę) i M5 (w dół). Nie zmienia to decyzji – brak sygnału na M5 ma pierwszeństwo.
- Pierwszy kandydat do poprawy: osobne pytania o cegły tymczasowe dla H1 i M5.
