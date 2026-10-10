# Jev + EKG (jednokanałowy zapis) – ćwiczenie edukacyjne

**To nie jest narzędzie medyczne ani wytyczna kliniczna.** Katalog służy do nauki: jak z zapisu EKG
wyciągnąć dane pochodne i jak Jev (TypeSafe System One) ocenia je w typowanych pytaniach.

## Pliki

| Plik | Rola |
|---|---|
| `ecg_z_obrazu.py` | lokalnie odtwarza załamki R i odstępy RR ze zrzutu EKG (obraz rastrowy, 3 paski po 10 s) |
| `ocena_ekg.mjs` | liczy wskaźniki w kodzie i zadaje Jevowi 5 pytań (regularność, odstępy, jakość, błąd detekcji, kolejka przeglądu) |
| `pomiar.przyklad.json` | **dane syntetyczne** (wygenerowane) w formacie wejściowym skryptu |

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

## Wniosek edukacyjny z uruchomień

Gdy kryteria w pytaniu są opisane słownie („bardzo podobne”), Jev bywa niepewny, mimo niskiej zmienności
odstępów RR. Progi liczbowe w opisie kryteriów mogłyby to zmienić – do przetestowania na danych
syntetycznych.
