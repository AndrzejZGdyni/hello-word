# context-bar

Mod do Claude Code: panel z paskiem wykorzystania kontekstu w bieżącej rozmowie.

Po każdej turze panel pokazuje pasek (20 znaków), procent oraz liczbę tokenów
względem okna kontekstu modelu. Kolor: zielony poniżej 60%, żółty od 60%,
czerwony od 85% (wtedy dodatkowo podpowiedź, by użyć `/compact`).

## Użycie

Panel otwiera się przy starcie sesji; komenda `/context-bar` otwiera go ponownie.
Do pierwszej odpowiedzi modelu (oraz po kompaktowaniu) panel pokazuje komunikat
o braku danych.

## Instalacja

Skopiuj folder do katalogu modów sesji albo użyj `--plugin-dir mods/context-bar`.
Wymaga włączenia modów w sesji Claude Code.
