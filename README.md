# hello-word

Repozytorium eksperymentalne i edukacyjne. Zawiera dwie niezależne części.

## 1. `tools/` – diagnostyka wibroakustyczna z modelem Jev

Skrypty Node.js, w których kod oblicza wskaźniki z pomiarów, a model **Jev** (TypeSafe, „System One”) wydaje typowany osąd z prawdopodobieństwami. Wynik jest porównywany z regułą w kodzie i oznaczany do weryfikacji przez diagnostę.

| Katalog | Zagadnienie |
|---|---|
| `jev-centrowka` | niewspółosiowość (równoległa / kątowa) |
| `jev-lozysko` | uszkodzenia łożysk tocznych (BPFO, BPFI, BSF, FTF) |
| `jev-niewywazenie` | niewyważenie, rozkład składowych statycznej i momentowej, liczba płaszczyzn korekcji |
| `jev-luzy` | luzy mechaniczne (typy A/B/C), lokalizacja i pilność |
| `jev-ekg` | ćwiczenie na zapisie EKG, **nie jest narzędziem medycznym** |
| `jev-run` | (Python) ocena raportów o sytuacji w rejonie Cieśniny Ormuz, tabela decyzyjna OK/ALERT/SPRAWDŹ/TRIP |
| `jev-zima` | (Python) gotowość domowego ogrzewania na zimę: pogoda, opał, sieć elektroenergetyczna |

Zbiorcze wyniki z danych przykładowych: [`tools/raport-zbiorczy.md`](tools/raport-zbiorczy.md).

### Uruchomienie

```bash
cd tools/jev-luzy
npm install
TYPESAFE_API_KEY=<klucz> node ocena_luzow.mjs pomiar.json
```

Wymagany jest własny klucz API TypeSafe. Klucza nie wolno umieszczać w repozytorium.

## 2. `app/` – aplikacja Android (Shelly Monitor)

Wcześniejszy projekt Android (Kotlin, Jetpack Compose) do monitorowania urządzeń Shelly przez chmurę.

## Ważne zastrzeżenia

- **Charakter edukacyjny.** Narzędzia nie zostały zwalidowane na rzeczywistych maszynach ani pacjentach. Wyniki nie zastępują oceny diagnosty, inżyniera ani lekarza.
- **Dane syntetyczne.** Wszystkie pliki z pomiarami są przykładowe lub wygenerowane. Repozytorium jest publiczne, więc **nie umieszczaj w nim rzeczywistych danych zakładowych, osobowych ani zdrowotnych**.
- **Niedokładność modelu.** Producent i niezależne przeglądy wskazują, że model należy traktować jako wsparcie decyzji, nie jako wyrocznię.

## Licencja

[MIT](LICENSE)
