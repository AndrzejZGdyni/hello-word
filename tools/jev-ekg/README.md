# Jev + EKG (jednokanałowy zapis) – ćwiczenie edukacyjne

**To nie jest narzędzie medyczne ani wytyczna kliniczna.** Katalog służy do nauki: jak z zapisu EKG
wyciągnąć dane pochodne i jak Jev (TypeSafe System One) ocenia je w typowanych pytaniach.

## Pliki

| Plik | Rola |
|---|---|
| `ecg_z_obrazu.py` | lokalnie odtwarza załamki R i odstępy RR ze zrzutu EKG (obraz rastrowy, 3 paski po 10 s) |
| `ocena_ekg.mjs` | liczy wskaźniki w kodzie i zadaje Jevowi 5 pytań (regularność, odstępy, jakość, błąd detekcji, kolejka przeglądu) |
| `pomiar.przyklad.json` | **dane syntetyczne** (wygenerowane) w formacie wejściowym skryptu |
| `eksperyment_syntetyczny.mjs` | eksperyment: 28 syntetycznych serii RR, opis kryteriów słowny vs liczbowy vs reguła w kodzie |
| `eksperyment_synt_wyniki.json` | wyniki eksperymentu (dane syntetyczne) |

Dane pochodne z prawdziwych zapisów (`pomiar.json`, `zapytanie.json`) zostają lokalnie – patrz `.gitignore`.

## Uruchomienie

```sh
npm install
node ocena_ekg.mjs pomiar.przyklad.json --dry-run          # tylko podgląd zapytania
TYPESAFE_API_KEY=... node ocena_ekg.mjs pomiar.przyklad.json

# własny zapis (obraz i wyniki zostają poza repozytorium):
pdftoppm -png -r 72 raport.pdf strona
python3 -I ecg_z_obrazu.py strona-1.png wynik.json --hr-raport 64 --kontrola kontrola
# z wynik.json przepisz zalamki_R_s do własnego pomiar.json (format jak pomiar.przyklad.json)
```

## Prywatność

Repozytorium jest **publiczne**. Nie dodawaj do niego zapisów EKG, raportów (zawierają daty, kody QR),
obrazów ani danych pochodnych z prawdziwych zapisów. `.gitignore` blokuje `*.pdf`, `*.png`, `*.jpg`,
`wynik*.json`, `pomiar.json` i `zapytanie.json`. Wysyłanie danych zdrowotnych do zewnętrznego API
wymaga podstawy prawnej i zgody osoby, której dotyczą.

## Ograniczenia

- Rozdzielczość czasowa ok. 10 ms (ok. 98 px/s) – **QRS, PR i QT nie są mierzone z obrazu**; używane są
  wartości z nagłówka raportu (zakładane w ms).
- Brak skali amplitudy (mV), jedno odprowadzenie, 30 s zapisu.
- Uderzenia na początku i końcu zapisu bywają artefaktami (oznaczone jako niepewne).
- Detekcję sprawdzono względem tętna z nagłówka raportu i wzrokowo na nakładce (`--kontrola`).
  Parametry (`REFRAKCJA_S`, `PROG_REL`) są robocze.
- Kategoria tętna w kodzie jest orientacyjna (podręcznikowa), nie pochodzi z wytycznych.

## Eksperyment na danych syntetycznych (`eksperyment_syntetyczny.mjs`)

Pytanie: czy progi liczbowe w opisie kryteriów poprawiają ocenę regularności rytmu przez Jev?
28 wygenerowanych serii RR ze znaną klasą (regularny 8, łagodnie nieregularny 8, wyraźnie nieregularny
12: przedwczesne uderzenia z przerwą oraz losowe RR). Ta sama treść pytania, dwa warianty opisu kryteriów.

| Metoda | Dokładność | Średnia pewność (poprawne / błędne) |
|---|---|---|
| reguła w kodzie (progi liczbowe) | 28/28 | – |
| Jev, kryteria **słowne** | 27/28 (96 %) | 0,78 / 0,35 |
| Jev, kryteria **liczbowe** | 28/28 (100 %) | 1,00 / – |

Wnioski (edukacyjne, nie kliniczne):
- Opis liczbowy usunął niepewność: 28/28 odpowiedzi z pewnością ≥ 0,9, wobec 13/28 przy opisie słownym.
- W wariancie słownym jedyny błąd to seria o CV 5,0 % uznana za „regular” przy rozkładzie 0,51 / 0,49 –
  niska pewność **sygnalizowała** niejednoznaczność (przy pewności < 0,6: trafność 8/9).
- **Ograniczenie:** prawda „z konstrukcji” i progi w opisie liczbowym są tym samym kryterium, więc wynik
  mierzy wykonywanie opisanej reguły, a nie trafność kliniczną. Reguła w kodzie osiągnęła to samo za darmo
  – tam, gdzie próg da się zapisać liczbą, powinien być w kodzie, a Jev ma sens przy ocenie kontekstu.
- Zbiór jest łatwy: brak błędów detekcji (pominięte lub fałszywe uderzenia), przypadków granicznych
  (CV ≈ 3 % i ≈ 10 %) i krótkich zapisów. Kolejny krok to dodanie takich przypadków.

Powtórzenie: `node eksperyment_syntetyczny.mjs [--seed 42]`; wyniki w `eksperyment_synt_wyniki.json`
(dane syntetyczne). Eksperyment zużywa ok. 27 tys. tokenów wejściowych.
