# context-bar

Mod do Claude Code: panel z paskiem wykorzystania kontekstu w bieżącej rozmowie.

Po każdej turze panel pokazuje pasek (20 znaków), procent oraz liczbę tokenów
względem okna kontekstu modelu. Kolor: zielony poniżej 60%, żółty od 60%,
czerwony od 85% (wtedy dodatkowo podpowiedź, by użyć `/compact`).

## Użycie

Panel otwiera się przy starcie sesji; komenda `/context-bar` (alias `/ctx`) otwiera go ponownie. Gdy klient nie rysuje paneli, komenda odpowiada tekstem z paskiem.
Do pierwszej odpowiedzi modelu (oraz po kompaktowaniu) panel pokazuje komunikat
o braku danych.

## Instalacja

```
/plugin install context-bar --marketplace AndrzejZGdyni/hello-word
```

Lub ręcznie: skopiuj folder do katalogu modów sesji albo użyj `--plugin-dir mods/context-bar`.
Wymaga włączenia modów w sesji Claude Code.
