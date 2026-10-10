# Raport zbiorczy – narzędzia Jev do diagnostyki wibroakustycznej

**Charakter dokumentu:** ćwiczenie edukacyjne. Wszystkie pomiary są **syntetycznymi danymi przykładowymi** (pliki `pomiar.json` w katalogach narzędzi). Wyniki nie stanowią diagnozy rzeczywistej maszyny; każdą ocenę Jeva weryfikuje diagnosta.

**Data uruchomienia:** 2026-10-10 · **Model:** jev-1.13.0 · **Uruchomienie:** `TYPESAFE_API_KEY=placeholder NODE_USE_ENV_PROXY=1 node <skrypt>.mjs pomiar.json`

## 1. Zestawienie

| Narzędzie | Główny wynik Jeva | Rodzaj / lokalizacja | Pilność / stadium | Zalecenie Jeva | Zgodność z regułą | Status skryptu |
|---|---|---|---|---|---|---|
| `jev-centrowka` | niewspółosiowość p = 0,87 | równoległa (0,79; pewność 0,72) | 2,04 / 3 | sprawdzić miękką stopę przed centrowaniem (0,80) | brak reguły porównawczej | wynik jednoznaczny |
| `jev-lozysko` | uszkodzenie bieżni zewnętrznej (1,00) | outer_race, 5 harmonicznych BPFO | stadium 2,04 / 4 | zaplanować wymianę (0,82) | brak reguły porównawczej | wynik jednoznaczny |
| `jev-niewywazenie` | niewyważenie p = 0,87 | dynamiczne (0,98) | strefa C wg ISO 20816-3 | oczyścić wirnik i sprawdzić ponownie (0,69) | rozkład S/C: 2 płaszczyzny; Jev: two_planes (1,00) | wynik jednoznaczny |
| `jev-luzy` | luz mechaniczny p = 0,76 | rotating_fit; fan_DE (0,99) | 3 / 4 | sprawdzić gniazdo łożyska i luz (0,66) | lokalizacja zgodna z regułą (typ C) | **do weryfikacji przez diagnostę** |

## 2. Uwagi do poszczególnych wyników

**Niewspółosiowość.** Przesunięcie równoległe, silny udział 2x (stosunek 2x/1x w kierunku promieniowym ok. 1,6 na obu łożyskach) i przesunięcie fazy 1x o 175° w poprzek sprzęgła. Jev zaleca przed centrowaniem wykluczyć miękką stopę.

**Łożysko.** Jednoznaczna sygnatura bieżni zewnętrznej (BPFO 75,16 Hz, pięć harmonicznych w widmie obwiedni). Problem ze smarowaniem mało prawdopodobny (p = 0,12). Zalecenie: zaplanować wymianę, nie wymieniać awaryjnie.

**Niewyważenie.** Rozkład na składową statyczną i momentową (C/S ok. 0,4–0,45, powyżej progu 0,2) wskazuje na korekcję w dwóch płaszczyznach. **Rozbieżność do zbadania:** Jev jako zalecenie wskazuje „oczyścić wirnik, potem sprawdzić” (0,69) przed wyważaniem w dwóch płaszczyznach (0,30). Reguła i klasyfikacja płaszczyzn są natomiast jednoznaczne co do dwóch płaszczyzn. Oba zalecenia nie wykluczają się (czyszczenie poprzedza wyważanie), ale w raporcie dla człowieka należy podać obie.

**Luzy.** Jedyny przypadek oznaczony jako „do weryfikacji”. Pomiar ma długą serię harmonicznych (8x), trzy połówkowe rzędy, niestabilność fazy 34° oraz strefę C, wyłącznie przy wentylatorze (DE). Jev wskazuje dwie możliwe przyczyny alternatywne o prawdopodobieństwie ≥ 0,5: niewspółosiowość lub zużycie sprzęgła (ok. 0,65) i tarcie wirnika o stojan (ok. 0,6). Ponieważ takie objawy częściowo pokrywają się z innymi przyczynami, ocenę luzu należy potwierdzić badaniem uzupełniającym.

## 3. Ograniczenia i powtarzalność

- **Powtarzalność:** dwa uruchomienia `jev-luzy` dały te same wnioski, ale niewielkie różnice w wartościach (alternatywne przyczyny 0,65 / 0,59 oraz 0,67 / 0,60; zalecenie 0,65 / 0,66). Progi decyzyjne warto ustalać z marginesem.
- **Dane syntetyczne:** zgodność wyniku z oczekiwaniem na jednym zestawie przykładowym nie dowodzi skuteczności na rzeczywistych maszynach. Do oceny skuteczności potrzebny jest zbiór pomiarów z potwierdzonymi przyczynami.
- **Zakres:** narzędzia oceniają jedną przyczynę na raz. Nakładanie się przyczyn (np. niewspółosiowość z luzem) wymaga zestawienia wyników, jak w tabeli powyżej.
- **Dane rzeczywiste:** repozytorium jest publiczne. Nie umieszczać w nim pomiarów z prawdziwych zakładów ani żadnych danych zdrowotnych.

## 4. Koszt wywołań (ta sesja)

| Narzędzie | Tokeny wejściowe | Tokeny wyjściowe |
|---|---|---|
| `jev-centrowka` | 1780 | 159 |
| `jev-lozysko` | 1825 | 152 |
| `jev-niewywazenie` | 2812 | 249 |
| `jev-luzy` | 6404 | 335 |
