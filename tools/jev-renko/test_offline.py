#!/usr/bin/env python3
"""Testy offline tabeli decyzyjnej i rejestru (bez wywołań Jev). Uruchamiać w tools/jev-renko:
    python test_offline.py
Odpowiedzi Jev są syntetyczne; dane rachunku (kapitał, wartość punktu) są fikcyjne."""
import sys

import jev_renko as r

rj = r.rj
BASE = {k: 0.05 for k in r.DECISION_KEYS}
SELL3 = {**BASE, "d1_bearish": .9, "h1_bearish": .9, "m5_bearish": .9}
DANE = {"instrument": "GOLD", "czas": "2026-11-20 10:00", "m5_pctB": 0.30, "m5_pctR": -45.0,
        "m5_sar": 3815.0, "m5_cena": 3805.0, "spread": 0.35,
        "wartosc_punktu": 370.0, "kapital": 5000.0, "ryzyko_proc": 1.3,
        "entry": 3805.0, "sl": 3815.0, "tp": 3780.0, "makro": []}
DANE_BUY = dict(DANE, entry=4195.0, sl=4185.0, tp=4220.0, m5_pctR=-55.0, m5_sar=4185.0, m5_cena=4195.0)
OK_DNIA = {"straty_z_rzedu": 0, "wynik_proc": 0.0, "sesja_zakonczona": False}


def a(d):
    return {k: {"noul": x} for k, x in d.items()}


CASES = [
    ("sesja zakończona", SELL3, DANE, {"straty_z_rzedu": 2, "wynik_proc": -1.4,
                                       "sesja_zakonczona": True}, "SESJA ZAKOŃCZONA"),
    ("D1 bez kierunku", {**BASE, "h1_bearish": .9, "m5_bearish": .9}, DANE, OK_DNIA, "CZEKAĆ"),
    ("D1 nierozstrzygnięty", {**BASE, "d1_bearish": .5}, DANE, OK_DNIA, "SPRAWDŹ"),
    ("konfluencja 1/3", {**BASE, "d1_bearish": .9, "h1_bullish": .9, "m5_bullish": .9},
     DANE, OK_DNIA, "CZEKAĆ"),
    ("konfluencja 2/3 bez wyzwalacza", {**BASE, "d1_bearish": .9, "h1_bearish": .9,
                                        "m5_bullish": .9}, DANE, OK_DNIA, "ARM"),
    ("FIRE SELL", {**SELL3, "m5_sell_trigger": .9}, DANE, OK_DNIA, "FIRE SELL"),
    ("FIRE BUY", {**BASE, "d1_bullish": .9, "h1_bullish": .9, "m5_buy_trigger": .9},
     DANE_BUY, OK_DNIA, "FIRE BUY"),
    ("wyzwalacz nierozstrzygnięty", {**SELL3, "m5_sell_trigger": .5}, DANE, OK_DNIA, "SPRAWDŹ"),
    ("H1 wyprzedany = tylko ostrzeżenie", {**SELL3, "m5_sell_trigger": .9,
                                          "h1_oversold_extreme": .9}, DANE, OK_DNIA, "FIRE SELL"),
    ("%B < 0,05 blokuje SHORT", {**SELL3, "m5_sell_trigger": .9}, dict(DANE, m5_pctB=0.03),
     OK_DNIA, "ARM"),
    ("%B > 0,95 nie blokuje SHORT", {**SELL3, "m5_sell_trigger": .9}, dict(DANE, m5_pctB=0.97),
     OK_DNIA, "FIRE SELL"),
    ("poza oknem 23:30", {**SELL3, "m5_sell_trigger": .9}, dict(DANE, czas="2026-11-20 23:30"),
     OK_DNIA, "ARM"),
    ("świadomie poza oknem", {**SELL3, "m5_sell_trigger": .9},
     dict(DANE, czas="2026-11-20 23:30", swiadomie_poza_oknem=True), OK_DNIA, "FIRE SELL"),
    ("makro ±15 min", {**SELL3, "m5_sell_trigger": .9},
     dict(DANE, makro=[{"czas": "2026-11-20 10:10", "nazwa": "CPI USA"}]), OK_DNIA, "ARM"),
    ("RR < 1,8", {**SELL3, "m5_sell_trigger": .9}, dict(DANE, tp=3790.0), OK_DNIA, "ARM"),
    ("ryzyko > 1,3% przy lot_min", {**SELL3, "m5_sell_trigger": .9},
     dict(DANE, kapital=1000.0, sl=3840.0, tp=3700.0), OK_DNIA, "ARM"),
    ("brak danych ryzyka", {**SELL3, "m5_sell_trigger": .9}, dict(DANE, entry=None),
     OK_DNIA, "ARM"),
    ("wyzwalacz: %R -20 (SELL wymaga < -30)", {**SELL3, "m5_sell_trigger": .9},
     dict(DANE, m5_pctR=-20.0), OK_DNIA, "ARM"),
    ("wyzwalacz: SAR pod ceną", {**SELL3, "m5_sell_trigger": .9}, dict(DANE, m5_sar=3800.0),
     OK_DNIA, "ARM"),
    ("wyzwalacz: brak %R", {**SELL3, "m5_sell_trigger": .9}, dict(DANE, m5_pctR=None),
     OK_DNIA, "ARM"),
    ("wyzwalacz BUY: %R -75 (wymaga > -70)", {**BASE, "d1_bullish": .9, "h1_bullish": .9,
     "m5_buy_trigger": .9}, dict(DANE_BUY, m5_pctR=-75.0), OK_DNIA, "ARM"),
    ("niespójne poziomy", {**SELL3, "m5_sell_trigger": .9}, dict(DANE, sl=3795.0),
     OK_DNIA, "ARM"),
]


def main():
    bad = 0
    for name, ans, dane, lk, exp in CASES:
        st, why, _, info = r.decide(a(ans), .7, .3, None, dane, lk)
        ok = st == exp
        bad += not ok
        print(f"{'OK ' if ok else 'ZLE'} {name:34} {st:17} {why}")
    # ostrzeżenie H1 obecne, blokady zapisane
    info = r.decide(a({**SELL3, "m5_sell_trigger": .9, "h1_oversold_extreme": .9}),
                    .7, .3, None, DANE, OK_DNIA)[3]
    bad += not any("H1 skrajnie" in w for w in info["ostrzezenia"])
    info = r.decide(a({**SELL3, "m5_sell_trigger": .9}), .7, .3, None,
                    dict(DANE, m5_pctB=0.03), OK_DNIA)[3]
    bad += info["blokady"] != ["%B"]
    s = r.decide(a({**SELL3, "m5_sell_trigger": .9}), .7, .3, None, DANE, OK_DNIA)[3]["setup"]
    # dystans 10 + 0,35 = 10,35; budżet 65 PLN; 65 / (10,35 × 370) = 0,0169 → lot 0,01
    exp_setup = {"lot": 0.01, "rr": round(25 / 10.35, 3), "ryzyko_pln": round(0.01 * 10.35 * 370, 2)}
    got = {k: s[k] for k in exp_setup}
    print(f"{'OK ' if got == exp_setup else 'ZLE'} kalkulacja setupu {got}")
    bad += got != exp_setup

    # licznik dnia: strata, breakeven, strata → 2 z rzędu; zysk zeruje
    wpisy = [
        {"czas": "2026-11-20 09:30", "wynik_proc": -0.8},
        {"czas": "2026-11-20 10:30", "wynik_proc": 0.05},   # breakeven – nie zeruje
        {"czas": "2026-11-20 11:30", "wynik_proc": -0.7},
    ]
    lk = rj.licznik_dnia(wpisy, "2026-11-20")
    ok1 = lk["straty_z_rzedu"] == 2 and lk["sesja_zakonczona"]
    lk2 = rj.licznik_dnia(wpisy + [{"czas": "2026-11-20 12:00", "wynik_proc": 0.4}],
                          "2026-11-20")
    ok2 = lk2["straty_z_rzedu"] == 0 and not lk2["sesja_zakonczona"]
    lk3 = rj.licznik_dnia([{"czas": "2026-11-20 09:30", "wynik_proc": -2.7}], "2026-11-20")
    ok3 = lk3["sesja_zakonczona"]
    lk4 = rj.licznik_dnia(wpisy, "2026-11-20", rj.parse_czas("2026-11-20 10:45"))
    ok4 = lk4["straty_z_rzedu"] == 1
    for n, ok in (("2 straty z breakevenem pomiędzy", ok1), ("zysk zeruje licznik", ok2),
                  ("wynik ≤ −2,6%", ok3), ("licznik do godziny analizy", ok4)):
        print(f"{'OK ' if ok else 'ZLE'} licznik: {n}")
        bad += not ok
    print(f"\nBŁĘDY: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
