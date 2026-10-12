# Jev + ISO 20816-3 – klasyfikacja maszyny i strefy A/B/C/D

**Ćwiczenie edukacyjne na danych syntetycznych.** Nie zastępuje oceny diagnosty ani tekstu normy.

Skrypt ustala grupę maszyny i rodzaj fundamentu, a następnie ocenia strefę drgań A–D dla podanych pomiarów prędkości drgań (mm/s RMS).

## Podział pracy

- **Kod:** reguły liczbowe i tabela granic stref (grupa wg mocy lub wysokości osi, kryterium fundamentu z częstości własnej, ocena strefy).
- **Jev (TypeSafe):** interpretacja opisów tekstowych, czyli którą część serii ISO 20816 stosować oraz czy fundament jest sztywny czy podatny. Przy pewności poniżej 0,8 skrypt podaje wyniki dla obu wariantów zamiast zgadywać.

Jev nie podaje wartości granicznych. Pochodzą one z tabeli w kodzie.

## Dane wejściowe (`wejscie.przyklad.json`)

| Pole | Zastosowanie |
|---|---|
| `moc_kW` | grupa 1 (> 300 kW) lub 2 (15–300 kW) |
| `wysokosc_osi_silnika_mm` | grupa 1 (≥ 315 mm) lub 2 (160–315 mm) |
| `obroty_rpm` | zakres normy, kryterium fundamentu |
| `czestosc_wlasna_ukladu_Hz` | jeśli podana: fundament sztywny, gdy ≥ 1,25 × częstość obrotowa |
| `opis_tekstowy`, `opis_fundamentu` | interpretuje Jev (opis dotyczy jednej maszyny: silnika, wentylatora itd.; pompa zostanie wskazana jako ISO 10816-7) |
| `punkty` | prędkość drgań v_RMS [mm/s] w punktach pomiarowych |

## Uruchomienie

```bash
cd tools/jev-iso20816
npm install
TYPESAFE_API_KEY=<klucz> node klasyfikacja_iso20816.mjs wejscie.przyklad.json
```

## Ograniczenia

1. Granice stref pochodzą ze źródeł wtórnych i **wymagają potwierdzenia w tekście normy** przed użyciem do ustalania alarmów.
2. Pompy wirnikowe nie podlegają ISO 20816-3, lecz ISO 10816-7. Turbiny parowe i generatory o mocy > 40 MW przy 1500/1800/3000/3600 obr/min podlegają ISO 20816-2, a pozostałe (≤ 40 MW lub inne prędkości) ISO 20816-3 (wg źródeł wtórnych, do potwierdzenia w tekście norm; liczba 50 MW pochodzi ze starszych wydań). Skrypt rozpoznaje takie przypadki (także turbiny gazowe i zespoły wodne wg części 4 i 5, bez weryfikacji ich zakresu) i informuje o właściwej normie, ale nie zawiera ich tabel granic. Silnik napędowy opisuje się osobno.
3. Oceniana jest wyłącznie wartość ogólna drgań, bez analizy widma i przyczyn.
4. Dane w repozytorium są syntetyczne. Nie umieszczaj tu rzeczywistych pomiarów zakładowych.
