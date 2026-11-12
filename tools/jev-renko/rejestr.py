#!/usr/bin/env python3
"""
rejestr.py — rejestr zamkniętych transakcji i licznik dnia (profil R11 2.4-trading-r3,
rejestr_transakcji.rejestr_glowny i dyscyplina_wykonania.8_limit_strat_dziennych).

Użycie:
    python rejestr.py dodaj --plik renko_rejestr.jsonl --czas "2026-11-12 22:40" \
        --instr GOLD --kier S --wejscie FIRE --kapital 5000 --wynik-pln -38.5 \
        [--entry 3878 --entry-real 3877.6 --sl 3884 --tp 3866 --rr-plan 2.0 --rr-real 1.9 \
         --ryzyko-plan 1.0 --ryzyko-real 1.1 --czas-trwania 35m --filtry "-" \
         --naruszenia "-" --uwagi "-"]
    python rejestr.py licznik --plik renko_rejestr.jsonl --dzien 2026-11-12

Plik rejestru zawiera dane rachunku i nie trafia do repozytorium.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")
BREAKEVEN_PROC = 0.1      # |wynik| < 0,1% kapitału = transakcja neutralna [r3-C]
LIMIT_STRAT_Z_RZEDU = 2   # 2 zamknięte straty z rzędu → SESJA ZAKOŃCZONA
LIMIT_WYNIKU_DNIA = -2.6  # wynik dnia ≤ −2,6% → SESJA ZAKOŃCZONA


def pl(x, nd=1, sign=False) -> str:
    """Liczba z przecinkiem dziesiętnym (format wklejki)."""
    s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
    return s.replace(".", ",")


def parse_czas(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


def wczytaj(plik: Path) -> list[dict]:
    if not plik.exists():
        return []
    return [json.loads(line) for line in plik.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def licznik_dnia(wpisy: list[dict], dzien: str, do_czasu: datetime | None = None) -> dict:
    """Straty z rzędu i wynik dnia (%) dla dnia kalendarzowego Europe/Warsaw.
    Strata ≤ −0,1% zwiększa licznik, zysk ≥ 0,1% go zeruje, breakeven nic nie zmienia."""
    dnia = sorted((w for w in wpisy if w["czas"].startswith(dzien)), key=lambda w: w["czas"])
    if do_czasu is not None:
        dnia = [w for w in dnia if parse_czas(w["czas"]) <= do_czasu]
    straty, wynik = 0, 0.0
    for w in dnia:
        p = w["wynik_proc"]
        wynik += p
        if p <= -BREAKEVEN_PROC:
            straty += 1
        elif p >= BREAKEVEN_PROC:
            straty = 0
    zakonczona = straty >= LIMIT_STRAT_Z_RZEDU or wynik <= LIMIT_WYNIKU_DNIA
    return {"dzien": dzien, "transakcje": len(dnia), "straty_z_rzedu": straty,
            "wynik_proc": round(wynik, 3), "sesja_zakonczona": zakonczona}


def wklejka(w: dict) -> str:
    c = parse_czas(w["czas"])
    rr = (f"RR 1:{pl(w['rr_plan'])}→1:{pl(w['rr_real'])}"
          if w.get("rr_plan") is not None and w.get("rr_real") is not None else "RR —")
    ry = (f"ryzyko {pl(w['ryzyko_plan'])}%→{pl(w['ryzyko_real'])}%"
          if w.get("ryzyko_plan") is not None and w.get("ryzyko_real") is not None
          else "ryzyko —")
    lk = w["licznik_po"]
    uwagi = "; ".join(x for x in (w.get("uwagi"), w.get("naruszenia") and
                                  f"naruszenie: {w['naruszenia']}") if x and x != "-")
    return (f"REJESTR │ #{w['id']} │ {c:%d.%m %H:%M} │ {w['instrument']} │ {w['kierunek']} │ "
            f"wejście: {w['wejscie']} │ {rr} │ {ry} │ wynik {pl(w['wynik_pln'], 2, True)} PLN "
            f"({pl(w['wynik_proc'], 1, True)}%) │ czas {w.get('czas_trwania') or '—'} │ "
            f"filtry: {w.get('filtry') or '—'} │ licznik: {lk['straty_z_rzedu']}/"
            f"{pl(lk['wynik_proc'], 1, True)}% │ uwagi: {uwagi or '—'}")


def dodaj(a) -> None:
    plik = Path(a.plik)
    wpisy = wczytaj(plik)
    parse_czas(a.czas)  # walidacja formatu
    if a.kapital <= 0:
        sys.exit("--kapital musi być dodatni")
    w = {
        "id": max((x["id"] for x in wpisy), default=0) + 1,
        "czas": a.czas, "instrument": a.instr, "kierunek": a.kier, "wejscie": a.wejscie,
        "entry": a.entry, "entry_real": a.entry_real, "sl": a.sl, "tp": a.tp,
        "rr_plan": a.rr_plan, "rr_real": a.rr_real,
        "ryzyko_plan": a.ryzyko_plan, "ryzyko_real": a.ryzyko_real,
        "wynik_pln": a.wynik_pln, "wynik_proc": round(a.wynik_pln / a.kapital * 100, 3),
        "kapital": a.kapital, "czas_trwania": a.czas_trwania, "filtry": a.filtry,
        "naruszenia": a.naruszenia, "uwagi": a.uwagi,
    }
    w["licznik_po"] = licznik_dnia(wpisy + [w], a.czas[:10])
    with plik.open("a", encoding="utf-8") as f:
        f.write(json.dumps(w, ensure_ascii=False) + "\n")
    print(wklejka(w))
    if w["licznik_po"]["sesja_zakonczona"]:
        print("SESJA ZAKOŃCZONA – zakaz nowych wejść do 00:00 Europe/Warsaw "
              "(dozwolone warianty 4, 5, 6).")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dodaj", help="dopisz zamkniętą transakcję")
    d.add_argument("--plik", default="renko_rejestr.jsonl")
    d.add_argument("--czas", required=True, help="zamknięcie: 'RRRR-MM-DD GG:MM' Europe/Warsaw")
    d.add_argument("--instr", required=True)
    d.add_argument("--kier", required=True, choices=["L", "S"])
    d.add_argument("--wejscie", required=True, choices=["FIRE", "wyjątek", "naruszenie"])
    d.add_argument("--kapital", type=float, required=True, help="kapitał wolny, PLN")
    d.add_argument("--wynik-pln", type=float, required=True)
    for opt in ("entry", "entry-real", "sl", "tp", "rr-plan", "rr-real",
                "ryzyko-plan", "ryzyko-real"):
        d.add_argument(f"--{opt}", type=float)
    for opt in ("czas-trwania", "filtry", "naruszenia", "uwagi"):
        d.add_argument(f"--{opt}")
    lk = sub.add_parser("licznik", help="licznik dnia")
    lk.add_argument("--plik", default="renko_rejestr.jsonl")
    lk.add_argument("--dzien", required=True, help="RRRR-MM-DD")
    a = ap.parse_args()
    if a.cmd == "dodaj":
        dodaj(a)
    else:
        print(json.dumps(licznik_dnia(wczytaj(Path(a.plik)), a.dzien), ensure_ascii=False))


if __name__ == "__main__":
    main()
