#!/usr/bin/env python3
"""Test wariantów zestawu Renko: każdy wariant N razy, decyzje i odpowiedzi do CSV.

Uruchamiać w katalogu tools/jev-renko; klucz jak w jev_renko.py. Kolumna 'oczekiwany'
to wynik, jakiego wymaga tabela decyzyjna dla danego opisu; niezgodność wypisywana
jest jako NIEZGODNOŚĆ. R1 to rzeczywisty odczyt z 12.11.2026, R2–R5 są syntetyczne.
"""
import csv
import json
from collections import Counter

import jev_renko as r

ITERATIONS = 2
OUT = "renko_warianty.csv"

VARIANTS = {
    "R1": ("CZEKAJ", "Stan na 12.11.2026 19:05. Instrument: GOLD, wykresy Renko z wielkością cegły ATR(14). "
           "D1 (cegła ok. 49 pkt): po spadku od szczytu z września ok. 4 500 kilka zamkniętych zielonych cegieł odbicia; ostatnia zamknięta cegła 4 030,56 (zielona). W bieżącej sesji dwie tymczasowe żółte cegły w dół, bieżąca cegła 3 874,50. Średnia krocząca 4 167,40. Parabolic SAR 3 895,05. MACD -82,43, sygnał -77,73, histogram -4,69. AO -202,85, słupki zielone. Williams %R -66,67. Fisher -0,23, sygnał -0,88. BB %B 0,31. "
           "H1 (cegła ok. 15 pkt): od szczytu 10.11 ok. 4 100 nieprzerwana seria zamkniętych czerwonych cegieł; ostatnia zamknięta cegła 3 872,58, bieżąca tymczasowa cegła 3 877,90. Średnia krocząca 4 003,92. Parabolic SAR 3 962,33. MACD poniżej sygnału -24,25, histogram -17,07 i spada. AO -125,82, słupki czerwone. Williams %R -100. Fisher -7,23, sygnał -6,86, oba spadają. BB %B 0,06. "
           "M5 (cegła 8,35 pkt): seria czerwonych cegieł od 10.11, na końcu dwie zamknięte zielone cegły odbicia; ostatnia zamknięta cegła 3 882,75 (zielona), bieżąca tymczasowa cegła 3 877,19. Średnia krocząca 3 918,66. Parabolic SAR 3 883,60. MACD: histogram -0,47, sygnał -37,09, linie się zbiegają. AO -90,43, słupki zielone. Williams %R -72,73 i rośnie. Fisher -3,51 przeciął w górę sygnał -5,21. BB %B 0,27 i rośnie."),
    "R2": ("SPRZEDAJ", "Stan na 20.11.2026 10:00. Instrument: GOLD, wykresy Renko ATR(14). "
           "D1: seria zamkniętych czerwonych cegieł, ostatnia zamknięta 3 800. Średnia krocząca 3 950. Parabolic SAR 3 880. Williams %R -75, Fisher -1,8, BB %B 0,25. "
           "H1: seria zamkniętych czerwonych cegieł z krótką korektą; ostatnia zamknięta 3 805. Średnia krocząca 3 830. Parabolic SAR 3 845. Williams %R -70. Fisher -1,5. BB %B 0,30. Brak tymczasowych cegieł. "
           "M5: po odbiciu do średniej 3 812 pojawiła się nowa zamknięta czerwona cegła 3 805; Fisher przeciął sygnał w dół; Parabolic SAR przeskoczył nad cenę na 3 815. Brak tymczasowych cegieł."),
    "R3": ("KUP", "Stan na 20.11.2026 10:00. Instrument: GOLD, wykresy Renko ATR(14). "
           "D1: seria zamkniętych zielonych cegieł, ostatnia zamknięta 4 200. Średnia krocząca 4 050. Parabolic SAR 4 120. Williams %R -25, Fisher 1,8, BB %B 0,75. "
           "H1: seria zamkniętych zielonych cegieł z krótką korektą; ostatnia zamknięta 4 195. Średnia krocząca 4 170. Parabolic SAR 4 155. Williams %R -30. Fisher 1,5. BB %B 0,70. Brak tymczasowych cegieł. "
           "M5: po korekcie do średniej 4 188 pojawiła się nowa zamknięta zielona cegła 4 195; Fisher przeciął sygnał w górę; Parabolic SAR przeskoczył pod cenę na 4 185. Brak tymczasowych cegieł."),
    "R4": ("CZEKAJ", "Stan na 20.11.2026 10:00. Instrument: GOLD, wykresy Renko ATR(14). "
           "D1: seria zamkniętych czerwonych cegieł, ostatnia zamknięta 3 800. Średnia krocząca 3 950. Parabolic SAR 3 880. "
           "H1: nieprzerwana seria zamkniętych czerwonych cegieł; ostatnia zamknięta 3 790. Średnia krocząca 3 860. Parabolic SAR 3 840. Williams %R -100. Fisher -6,2. BB %B 0,04. Brak tymczasowych cegieł. "
           "M5: nowa zamknięta czerwona cegła 3 790; Fisher przeciął sygnał w dół; Parabolic SAR nad ceną na 3 800. Brak tymczasowych cegieł."),
    "R5": ("CZEKAJ", "Stan na 20.11.2026 10:00. Instrument: GOLD, wykresy Renko ATR(14). "
           "D1: seria zamkniętych zielonych cegieł, ostatnia zamknięta 4 100. Średnia krocząca 3 980. Parabolic SAR 4 010. "
           "H1: seria zamkniętych czerwonych cegieł; ostatnia zamknięta 4 060. Średnia krocząca 4 090. Parabolic SAR 4 110. Williams %R -80. Fisher -2,0. BB %B 0,15. Brak tymczasowych cegieł. "
           "M5: nowa zamknięta czerwona cegła 4 060; Fisher przeciął sygnał w dół; Parabolic SAR nad ceną. Brak tymczasowych cegieł."),
}


def main():
    base = json.load(open("renko_template.json", encoding="utf-8"))
    rows, decisions = [], {}
    for name, (expected, state) in VARIANTS.items():
        for i in range(1, ITERATIONS + 1):
            resp = r.jz.ask(dict(base, state=state))
            answers = r.jr.extract_answers(resp)
            result, reason, _ = r.decide(answers, 0.7, 0.3)
            row = {"variant": name, "iteration": i, "oczekiwany": expected,
                   "decision": result, "reason": reason}
            row.update({k: a.get("noul") for k, a in answers.items()})
            rows.append(row)
            print(f"[{name} #{i}] {result} – {reason}")
        decisions[name] = (expected, Counter(x["decision"] for x in rows if x["variant"] == name))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print()
    for name, (expected, cnt) in decisions.items():
        flag = "" if set(cnt) == {expected} else "  NIEZGODNOŚĆ"
        print(f"{name}: oczekiwany {expected}, otrzymany {dict(cnt)}{flag}")
    print(f"\nZapisano {OUT} ({len(rows)} przebiegów)")


if __name__ == "__main__":
    main()
