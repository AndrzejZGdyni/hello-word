#!/usr/bin/env python3
"""Test wariantów zestawu Renko: każdy wariant N razy, statusy i odpowiedzi do CSV.

Uruchamiać w katalogu tools/jev-renko; klucz jak w jev_renko.py. Kolumna 'oczekiwany'
to status, jakiego wymaga tabela decyzyjna dla danego opisu; niezgodność wypisywana
jest jako NIEZGODNOŚĆ. R1 i R8 to rzeczywiste odczyty GOLD z 12.11.2026 (bez danych
rachunku), R2–R7 i R9 są syntetyczne; kapitał i wartość punktu są fikcyjne.
"""
import csv
import json
from collections import Counter

import jev_renko as r

ITERATIONS = 2
OUT = "renko_warianty.csv"
LICZNIK = {"straty_z_rzedu": 0, "wynik_proc": 0.0, "sesja_zakonczona": False}
RACHUNEK = {"instrument": "GOLD", "czas": "2026-11-20 10:00", "m5_pctB": 0.30, "spread": 0.35,
            "wartosc_punktu": 370.0, "kapital": 5000.0, "ryzyko_proc": 1.3, "makro": []}
SELL_LVL = dict(RACHUNEK, entry=3805.0, sl=3815.0, tp=3780.0, m5_pctR=-45.0, m5_sar=3815.0,
                m5_cena=3805.0)
D1_H1_SELL = ("Stan na 20.11.2026 10:00. Instrument: GOLD, wykresy Renko ATR(14). "
              "D1: seria zamkniętych czerwonych cegieł, ostatnia zamknięta 3 800. Średnia krocząca 3 950. Parabolic SAR 3 880. Williams %R -75, Fisher -1,8, BB %B 0,25. "
              "H1 (cegła 12 pkt): seria zamkniętych czerwonych cegieł z krótką korektą; ostatnia zamknięta 3 805. Średnia krocząca 3 830. Parabolic SAR 3 845. Williams %R -70. Fisher -1,5. BB %B 0,30. ")
M5_SELL = ("M5 (cegła 4 pkt): po odbiciu do średniej 3 812 pojawiła się nowa zamknięta czerwona cegła 3 805,00; cena poniżej średniej; Williams %R -45; Fisher przeciął sygnał w dół; Parabolic SAR przeskoczył nad cenę na 3 815. ")

VARIANTS = {
    "R1": ("ARM", "Stan na 12.11.2026 19:05. Instrument: GOLD, wykresy Renko z wielkością cegły ATR(14). "
           "D1 (cegła ok. 49 pkt): po spadku od szczytu z września ok. 4 500 kilka zamkniętych zielonych cegieł odbicia, a po nich jedna zamknięta czerwona; ostatnia zamknięta cegła 4 030,56 (czerwona). W bieżącej sesji dwie tymczasowe żółte cegły w dół, bieżąca cegła 3 874,50. Średnia krocząca 4 167,40. Parabolic SAR 3 895,05. MACD -82,43, sygnał -77,73, histogram -4,69. AO -202,85, słupki zielone. Williams %R -66,67. Fisher -0,23, sygnał -0,88. BB %B 0,31. "
           "H1 (cegła ok. 15 pkt): od szczytu 10.11 ok. 4 100 nieprzerwana seria zamkniętych czerwonych cegieł; ostatnia zamknięta cegła 3 872,58, bieżąca tymczasowa cegła 3 877,90 (różnica +5,32 pkt, czyli 0,35 cegły). Średnia krocząca 4 003,92. Parabolic SAR 3 962,33. MACD poniżej sygnału -24,25, histogram -17,07 i spada. AO -125,82, słupki czerwone. Williams %R -100. Fisher -7,23, sygnał -6,86, oba spadają. BB %B 0,06. "
           "M5 (cegła 8,35 pkt): seria czerwonych cegieł od 10.11, na końcu dwie zamknięte zielone cegły odbicia; ostatnia zamknięta cegła 3 882,75 (zielona), bieżąca tymczasowa cegła 3 877,19 (różnica -5,56 pkt, czyli 0,67 cegły). Średnia krocząca 3 918,66. Parabolic SAR 3 883,60. MACD: histogram -0,47, sygnał -37,09, linie się zbiegają. AO -90,43, słupki zielone. Williams %R -72,73 i rośnie. Fisher -3,51 przeciął w górę sygnał -5,21. BB %B 0,27 i rośnie.",
           {"instrument": "GOLD", "czas": "2026-11-12 19:05", "m5_pctB": 0.27, "m5_pctR": -72.73,
            "m5_sar": 3883.60, "m5_cena": 3877.19}),
    "R2": ("FIRE SELL", D1_H1_SELL + "Brak tymczasowych cegieł. " + M5_SELL + "Brak tymczasowych cegieł.", SELL_LVL),
    "R3": ("FIRE BUY", "Stan na 20.11.2026 10:00. Instrument: GOLD, wykresy Renko ATR(14). "
           "D1: seria zamkniętych zielonych cegieł, ostatnia zamknięta 4 200. Średnia krocząca 4 050. Parabolic SAR 4 120. Williams %R -25, Fisher 1,8, BB %B 0,75. "
           "H1 (cegła 12 pkt): seria zamkniętych zielonych cegieł z krótką korektą; ostatnia zamknięta 4 195. Średnia krocząca 4 170. Parabolic SAR 4 155. Williams %R -30. Fisher 1,5. BB %B 0,70. Brak tymczasowych cegieł. "
           "M5 (cegła 4 pkt): po korekcie do średniej 4 188 pojawiła się nowa zamknięta zielona cegła 4 195; cena powyżej średniej; Williams %R -55; Fisher przeciął sygnał w górę; Parabolic SAR przeskoczył pod cenę na 4 185. Brak tymczasowych cegieł.",
           dict(RACHUNEK, entry=4195.0, sl=4185.0, tp=4220.0, m5_pctB=0.60, m5_pctR=-55.0,
                m5_sar=4185.0, m5_cena=4195.0)),
    "R4": ("FIRE SELL", "Stan na 20.11.2026 10:00. Instrument: GOLD, wykresy Renko ATR(14). "
           "D1: seria zamkniętych czerwonych cegieł, ostatnia zamknięta 3 800. Średnia krocząca 3 950. Parabolic SAR 3 880. "
           "H1 (cegła 12 pkt): nieprzerwana seria zamkniętych czerwonych cegieł; ostatnia zamknięta 3 790. Średnia krocząca 3 860. Parabolic SAR 3 840. Williams %R -100. Fisher -6,2. BB %B 0,04. Brak tymczasowych cegieł. "
           "M5 (cegła 4 pkt): nowa zamknięta czerwona cegła 3 790; cena poniżej średniej 3 796; Williams %R -40; Fisher przeciął sygnał w dół; Parabolic SAR nad ceną na 3 800. Brak tymczasowych cegieł.",
           dict(RACHUNEK, entry=3790.0, sl=3800.0, tp=3765.0, m5_pctR=-40.0, m5_sar=3800.0,
                m5_cena=3790.0)),
    "R5": ("CZEKAĆ", "Stan na 20.11.2026 10:00. Instrument: GOLD, wykresy Renko ATR(14). "
           "D1: seria zamkniętych zielonych cegieł, ostatnia zamknięta 4 100. Średnia krocząca 3 980. Parabolic SAR 4 010. "
           "H1 (cegła 12 pkt): seria zamkniętych czerwonych cegieł; ostatnia zamknięta 4 060. Średnia krocząca 4 090. Parabolic SAR 4 110. Williams %R -80. Fisher -2,0. BB %B 0,15. Brak tymczasowych cegieł. "
           "M5 (cegła 4 pkt): seria zamkniętych czerwonych cegieł, nowa czerwona cegła 4 060; cena poniżej średniej 4 070; Williams %R -60; Fisher przeciął sygnał w dół; Parabolic SAR nad ceną. Brak tymczasowych cegieł.",
           RACHUNEK),
    "R6": ("FIRE SELL", D1_H1_SELL.replace("ostatnia zamknięta 3 805. Średnia", "ostatnia zamknięta cegła 3 805,00, bieżąca tymczasowa cegła 3 805,40 (różnica +0,40 pkt, czyli 0,03 cegły). Średnia")
           + M5_SELL + "Brak tymczasowych cegieł.", SELL_LVL),
    "R7": ("FIRE SELL", D1_H1_SELL + "Brak tymczasowych cegieł. " + M5_SELL
           + "Bieżąca tymczasowa cegła 3 808,50 (różnica +3,50 pkt, czyli 0,88 cegły).", SELL_LVL),
    "R8": ("ARM", "Stan na 12.11.2026 21:50. Instrument: GOLD, wykresy Renko z wielkością cegły ATR(14). "
           "D1 (cegła ok. 49 pkt): po spadku od szczytu z września kilka zamkniętych zielonych cegieł odbicia, a po nich jedna zamknięta czerwona; ostatnia zamknięta cegła 4 030,56 (czerwona). W bieżącej sesji trzy tymczasowe żółte cegły w dół, bieżąca wartość 3 877,99 (różnica -152,57 pkt, czyli 3,1 cegły). Średnia krocząca 4 167,40. Parabolic SAR 3 895,05. MACD -82,43, sygnał -77,73, histogram -4,69. AO -202,85, słupki zielone. Williams %R -66,67. Fisher -0,23, sygnał -0,88. BB %B 0,31. "
           "H1 (cegła 12,6 pkt): od szczytu 10.11 nieprzerwana seria zamkniętych czerwonych cegieł, od 19:05 bez nowych cegieł; ostatnia zamknięta cegła 3 880,80, bieżąca wartość 3 878,19 (różnica -2,61 pkt, czyli 0,21 cegły). Średnia krocząca 3 987,90. Parabolic SAR 3 947,06. MACD poniżej sygnału -32,11, histogram -12,14. AO -120,44, słupki czerwone. Williams %R -100. Fisher -7,41, sygnał -7,21. BB %B 0,04. "
           "M5 (cegła 3,09 pkt): po dołku ok. 3 855 seria zamkniętych zielonych cegieł z pojedynczymi czerwonymi, cena powyżej średniej; ostatnia zamknięta cegła 3 884,13 (zielona), bieżąca wartość 3 878,21 (różnica -5,92 pkt, czyli 1,9 cegły). Średnia krocząca 3 872,08. Parabolic SAR 3 872,84. MACD -1,27 powyżej sygnału -3,98, histogram +2,71. AO +1,80, słupki zielone. Williams %R 0,00. Fisher 1,73, sygnał 1,55, Fisher powyżej sygnału, linie się spłaszczają. BB %B 0,88.",
           {"instrument": "GOLD", "czas": "2026-11-12 21:50", "m5_pctB": 0.88, "m5_pctR": 0.0,
            "m5_sar": 3872.84, "m5_cena": 3878.21}),
    "R9": ("ARM", D1_H1_SELL + "Brak tymczasowych cegieł. "
           + M5_SELL.replace("Williams %R -45", "Williams %R -20") + "Brak tymczasowych cegieł.",
           dict(SELL_LVL, m5_pctR=-20.0)),
}


def main():
    base = json.load(open("renko_template.json", encoding="utf-8"))
    jev = {k: base[k] for k in r.JEV_FIELDS if k in base}
    rows, decisions = [], {}
    for name, (expected, state, dane) in VARIANTS.items():
        for i in range(1, ITERATIONS + 1):
            resp = r.jz.ask(dict(jev, state=state))
            answers = r.jr.extract_answers(resp)
            status, reason, _, info = r.decide(answers, 0.7, 0.3, None, dane, LICZNIK)
            row = {"variant": name, "iteration": i, "oczekiwany": expected,
                   "decision": status, "reason": reason,
                   "ostrzezenia": " | ".join(info["ostrzezenia"])}
            row.update({k: a.get("noul") for k, a in answers.items()})
            rows.append(row)
            print(f"[{name} #{i}] {status} – {reason}")
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
