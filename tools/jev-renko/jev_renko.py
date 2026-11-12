#!/usr/bin/env python3
"""
jev_renko.py — status CZEKAĆ / ARM / FIRE dla wykresów Renko (D1, H1, M5) według
profilu R11 2.4-trading-r3. Jev (TypeSafe System One) odpowiada na pytania opisowe
o wykresy w `state` (trend, wyzwalacz M5, ostrzeżenia); reguły liczbowe profilu
(limit dnia, konfluencja, okno płynności, %B, makro, ryzyko i RR po kosztach)
liczy kod z pola `dane`. Opis: README.md.

Użycie:
    python jev_renko.py renko_RRRR-MM-DD_GGMM.json --dry-run
    python jev_renko.py renko_RRRR-MM-DD_GGMM.json --log renko_log.jsonl \
        --rejestr renko_rejestr.jsonl --blokady renko_blokady.jsonl
    python jev_renko.py renko_RRRR-MM-DD_GGMM.json --override m5_sell_trigger=nie
    (klucz: TYPESAFE_API_KEY poza sesją Claude Code w chmurze; w niej dodaje go proxy)

Kody wyjścia: 0 CZEKAĆ, 1 błąd, 2 FIRE SELL, 3 FIRE BUY, 4 SPRAWDŹ, 5 ARM,
6 SESJA ZAKOŃCZONA.

Analiza edukacyjna; nie stanowi porady inwestycyjnej. Pole `dane` nie jest
wysyłane do Jev.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

_here = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


jr = _load("jev_run", _here.parent / "jev-run" / "jev_run.py")
jz = _load("jev_zima", _here.parent / "jev-zima" / "jev_zima.py")
rj = _load("rejestr", _here / "rejestr.py")

SELL, BUY = "SELL", "BUY"
TREND = {SELL: ("d1_bearish", "h1_bearish", "m5_bearish"),
         BUY: ("d1_bullish", "h1_bullish", "m5_bullish")}
TRIGGER = {SELL: "m5_sell_trigger", BUY: "m5_buy_trigger"}
EXTREME = {SELL: "h1_oversold_extreme", BUY: "h1_overbought_extreme"}
AGAINST = {SELL: ("h1_provisional_up", "m5_provisional_up"),
           BUY: ("h1_provisional_down", "m5_provisional_down")}
DECISION_KEYS = (*TREND[SELL], *TREND[BUY], TRIGGER[SELL], TRIGGER[BUY],
                 EXTREME[SELL], EXTREME[BUY], *AGAINST[SELL], *AGAINST[BUY])

# Progi profilu R11 2.4-trading-r3 (dyscyplina_wykonania)
KONFLUENCJA_MIN = 2           # 1. bramka konfluencji: ≥ 2/3
OKNO_OD, OKNO_DO = 8, 23      # 3. filtr płynności: wejścia 08:00–23:00 Europe/Warsaw
RYZYKO_MAX = 1.3              # 4. bramka ryzyka: ≤ 1,3% kapitału po kosztach
RR_MIN = 1.8                  # 6. filtr RR: ≥ 1,8 po kosztach
PCTB_SHORT_MIN, PCTB_LONG_MAX = 0.05, 0.95   # 7. filtr gonienia rynku (M5)
MAKRO_MIN = 15                # 9. filtr zdarzeń makro: ±15 min
PCTR_SELL_MAX, PCTR_BUY_MIN = -30, -70       # wyzwalacz M5: SELL %R < −30, BUY %R > −70

EXIT_CODES = {"CZEKAĆ": 0, "FIRE SELL": 2, "FIRE BUY": 3, "SPRAWDŹ": 4, "ARM": 5,
              "SESJA ZAKOŃCZONA": 6}
UNSURE = "nierozstrzygnięte"
JEV_FIELDS = ("model", "state", "questions")


def validate(payload: dict) -> None:
    errors = []
    state = payload.get("state")
    if not isinstance(state, (str, dict, list)) or jr.is_empty(state):
        errors.append("brak lub puste pole 'state'")
    elif isinstance(state, str) and "<" in state:
        errors.append("'state' zawiera szablonowe znaczniki <...>; wpisz odczyt wykresów")
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not questions:
        errors.append("brak słownika 'questions'")
    else:
        for key in DECISION_KEYS:
            q = questions.get(key)
            if q is None:
                errors.append(f"{key}: brak pytania wymaganego przez tabelę decyzyjną")
                continue
            if q.get("type") != "noul":
                errors.append(f"{key}: pytanie decyzyjne musi być typu 'noul'")
            if jr.is_empty(q.get("instructions")):
                errors.append(f"{key}: brak 'instructions'")
    dane = payload.get("dane", {})
    if not isinstance(dane, dict):
        errors.append("'dane' musi być słownikiem")
    else:
        try:
            parse_czas(dane)
        except ValueError:
            errors.append("dane.czas: oczekiwano 'RRRR-MM-DD GG:MM' (Europe/Warsaw)")
        for k in ("m5_pctB", "m5_pctR", "m5_sar", "m5_cena", "spread", "wartosc_punktu", "kapital", "ryzyko_proc",
                  "entry", "sl", "tp", "lot_min", "lot_krok"):
            if dane.get(k) is not None and not isinstance(dane[k], (int, float)):
                errors.append(f"dane.{k}: oczekiwano liczby")
    if errors:
        sys.exit("Błędy walidacji:\n  - " + "\n  - ".join(errors))


def parse_czas(dane: dict) -> datetime | None:
    c = dane.get("czas")
    if c in (None, "", "RRRR-MM-DD GG:MM"):
        return None
    return rj.parse_czas(c)


def setup_po_kosztach(kier: str, d: dict) -> tuple[dict | None, str | None]:
    """Lot, ryzyko i RR po kosztach (bramka 4, filtr 6). Realny dystans ryzyka =
    |SL − entry| + spread; RR = |TP − entry| / realny dystans ryzyka."""
    brak = [k for k in ("entry", "sl", "tp", "spread", "wartosc_punktu", "kapital",
                        "ryzyko_proc") if d.get(k) is None]
    if brak:
        return None, "brak danych: " + ", ".join(brak)
    e, sl, tp, spread = d["entry"], d["sl"], d["tp"], d["spread"]
    if kier == SELL and not (sl > e > tp) or kier == BUY and not (sl < e < tp):
        return None, f"niespójne poziomy dla {kier}: entry {e}, SL {sl}, TP {tp}"
    dyst = abs(sl - e) + spread
    wp, kap = d["wartosc_punktu"], d["kapital"]
    lot_min, krok = d.get("lot_min") or 0.01, d.get("lot_krok") or 0.01
    budzet = kap * min(d["ryzyko_proc"], RYZYKO_MAX) / 100
    lot = math.floor(budzet / (dyst * wp) / krok + 1e-9) * krok
    lot = round(max(lot, lot_min), 6)
    ryzyko_pln = lot * dyst * wp
    return {"entry": e, "sl": sl, "tp": tp, "spread": spread, "dystans_ryzyka": round(dyst, 4),
            "lot": lot, "ryzyko_pln": round(ryzyko_pln, 2),
            "ryzyko_proc": round(ryzyko_pln / kap * 100, 3),
            "zysk_pln": round(lot * abs(tp - e) * wp, 2),
            "rr": round(abs(tp - e) / dyst, 3)}, None


def decide(answers: dict, yes: float, no: float, overrides: dict | None = None,
           dane: dict | None = None, licznik: dict | None = None):
    """Zwraca (status, powód, odpowiedzi tak/nie, info). Kolejność jak w profilu:
    limit dnia → kierunek D1 → bramka konfluencji → wyzwalacz M5 (ARM→FIRE) →
    checklista FIRE (okno płynności, ryzyko, RR, %B) i filtr makro."""
    v = {k: jr.classify(answers.get(k, {}).get("noul"), yes, no) for k in DECISION_KEYS}
    v.update(overrides or {})
    d = dane or {}
    info = {"kierunek": None, "konfluencja": None, "zgodne": [], "ostrzezenia": [],
            "checklista": None, "blokady": [], "setup": None, "makro": "nieznany [E]"}

    def out(status, reason):
        return status, reason, v, info

    # 0. limit strat dziennych (warunek wstępny – blokuje także setupy)
    if licznik is None:
        info["ostrzezenia"].append("licznik dnia nieznany – podaj --rejestr")
    elif licznik["sesja_zakonczona"]:
        return out("SESJA ZAKOŃCZONA", f"limit dnia: straty z rzędu {licznik['straty_z_rzedu']}, "
                   f"wynik {licznik['wynik_proc']:+.2f}%; dozwolone warianty 4, 5, 6")

    # 1. kierunek nadrzędny z D1 (zakaz BUY przy SELL D1 i odwrotnie)
    bear, bull = v["d1_bearish"], v["d1_bullish"]
    if bear == "tak" and bull == "tak":
        return out("SPRAWDŹ", "sprzeczne odpowiedzi: D1 jednocześnie spadkowy i wzrostowy")
    if bear == "tak":
        k = SELL
    elif bull == "tak":
        k = BUY
    elif UNSURE in (bear, bull):
        return out("SPRAWDŹ", "trend D1 nierozstrzygnięty; uzupełnij opis D1")
    else:
        return out("CZEKAĆ", "D1 bez kierunku – brak biasu nadrzędnego")
    info["kierunek"] = k

    # 2. bramka konfluencji ≥ 2/3 (interwały zgodne z D1)
    keys = TREND[k]
    info["zgodne"] = [x[:2].upper() for x in keys if v[x] == "tak"]
    n = len(info["zgodne"])
    info["konfluencja"] = n
    if n < KONFLUENCJA_MIN:
        if any(v[x] == UNSURE for x in keys[1:]):
            return out("SPRAWDŹ", "trend H1 lub M5 nierozstrzygnięty; uzupełnij opis")
        return out("CZEKAĆ", f"konfluencja {n}/3 poniżej progu – bramka konfluencji blokuje SETUP")

    # ostrzeżenia spoza profilu (nie blokują; reguła 'przeglad_okresowy')
    if v[EXTREME[k]] == "tak":
        info["ostrzezenia"].append(
            f"H1 skrajnie {'wyprzedany' if k == SELL else 'wykupiony'} – ryzyko wejścia po dużym ruchu")
    hit = [x[:2].upper() for x in AGAINST[k] if v[x] == "tak"]
    if hit:
        info["ostrzezenia"].append(f"cegły tymczasowe {'+'.join(hit)} biegną przeciw kierunkowi {k}")

    # 3. wyzwalacz M5 (ARM → FIRE): nowy blok w kierunku D1 [Jev] + %R i SAR [kod]
    t = v[TRIGGER[k]]
    if t == UNSURE:
        return out("SPRAWDŹ", "kolor ostatniej zamkniętej cegły M5 nierozstrzygnięty; uzupełnij opis M5")
    if t == "nie":
        return out("ARM", f"{k}, konfluencja {n}/3 – czekam na nowy blok {k} na M5 (świeży zrzut)")
    pr, sar, cena = d.get("m5_pctR"), d.get("m5_sar"), d.get("m5_cena")
    wz = {"%R": None if pr is None else (pr < PCTR_SELL_MAX if k == SELL else pr > PCTR_BUY_MIN),
          "SAR": None if sar is None or cena is None else (sar > cena if k == SELL else sar < cena)}
    info["wyzwalacz"] = wz
    if False in wz.values():
        nie = [x for x, ok in wz.items() if ok is False]
        return out("ARM", f"nowy blok {k} na M5, ale wyzwalacz niepełny: {', '.join(nie)} "
                   f"(SELL: %R < {PCTR_SELL_MAX} i SAR nad ceną; BUY: %R > {PCTR_BUY_MIN} i SAR pod ceną)")
    if None in wz.values():
        return out("ARM", "nowy blok na M5; brak danych do wyzwalacza: dane.m5_pctR, m5_sar, m5_cena")

    # 4. checklista FIRE i filtr makro
    czas = parse_czas(d)
    ch = {}
    ch["1_wyzwalacz"] = True
    if czas is None:
        ch["2_okno_plynnosci"] = None
    else:
        w_oknie = OKNO_OD <= czas.hour < OKNO_DO
        ch["2_okno_plynnosci"] = w_oknie or bool(d.get("swiadomie_poza_oknem"))
        if not w_oknie and d.get("swiadomie_poza_oknem"):
            info["ostrzezenia"].append("świadomie poza oknem – lot zredukowany do minimum")
    setup, err = setup_po_kosztach(k, d)
    if setup and d.get("swiadomie_poza_oknem") and czas and not (OKNO_OD <= czas.hour < OKNO_DO):
        setup = setup_po_kosztach(k, dict(d, ryzyko_proc=0))[0]  # lot minimalny
    info["setup"] = setup
    if err:
        info["ostrzezenia"].append(f"bramka ryzyka/RR: {err}")
    ch["3_ryzyko"] = None if setup is None else setup["ryzyko_proc"] <= RYZYKO_MAX
    ch["4_rr"] = None if setup is None else setup["rr"] >= RR_MIN
    pb = d.get("m5_pctB")
    ch["5_pctB"] = None if pb is None else (pb >= PCTB_SHORT_MIN if k == SELL else pb <= PCTB_LONG_MAX)
    info["checklista"] = ch

    makro = d.get("makro")
    if makro is None:
        info["makro"] = "nieznany [E] – sprawdź kalendarz przed wejściem"
    elif czas is None:
        info["makro"] = "nieznany [E] – brak dane.czas"
    else:
        blok = [m for m in makro
                if abs(rj.parse_czas(m["czas"]) - czas) <= timedelta(minutes=MAKRO_MIN)]
        if blok:
            do = max(rj.parse_czas(m["czas"]) for m in blok) + timedelta(minutes=MAKRO_MIN)
            info["makro"] = f"zablokowane do {do:%H:%M} – zdarzenie: {blok[0]['nazwa']}"
            info["blokady"].append("makro")
        else:
            info["makro"] = "okno FIRE wolne"

    nazwy = {"2_okno_plynnosci": "płynność", "3_ryzyko": "ryzyko", "4_rr": "RR", "5_pctB": "%B"}
    info["blokady"] = [nazwy[x] for x, ok in ch.items() if ok is False] + info["blokady"]
    if info["blokady"]:
        return out("ARM", f"wyzwalacz {k} wystąpił, ale blokuje: {', '.join(info['blokady'])}")
    brak = [nazwy[x] for x, ok in ch.items() if ok is None]
    if brak:
        return out("ARM", f"wyzwalacz {k} wystąpił; brak danych do checklisty FIRE: {', '.join(brak)}")
    return out(f"FIRE {k}", f"checklista FIRE 5×TAK, konfluencja {n}/3")


def blokada_wpis(d: dict, info: dict, czas: datetime | None) -> dict:
    s = info["setup"] or {}
    par = []
    if d.get("m5_pctB") is not None:
        par.append(f"%B={rj.pl(d['m5_pctB'], 2)}")
    if s:
        par += [f"RR=1:{rj.pl(s['rr'], 2)}", f"ryzyko={rj.pl(s['ryzyko_proc'], 2)}%"]
    c = f"{czas:%d.%m %H:%M}" if czas else "??.?? ??:??"
    kier = "S" if info["kierunek"] == SELL else "L"
    wkl = (f"BLOKADA │ {c} │ {d.get('instrument', '?')} │ {kier} │ filtr: "
           f"{', '.join(info['blokady'])} │ parametry: {' / '.join(par) or '—'} │ "
           f"hipoteza po [Xh]: [E] do uzupełnienia")
    return {"czas": d.get("czas"), "instrument": d.get("instrument"), "kierunek": kier,
            "filtry": info["blokady"], "parametry": par, "hipoteza": None, "wklejka": wkl}


def raport(status, reason, v, info, answers, d, model, licznik, overrides, model_v):
    czas = parse_czas(d)
    c = f"{czas:%d.%m.%Y ~%H:%M}" if czas else "?"
    print(f"\n{d.get('instrument', '?')} | {c} Europe/Warsaw | typ: Renko ATR | model {model}")
    if licznik:
        print(f"Licznik dnia: straty z rzędu {licznik['straty_z_rzedu']} | wynik dnia "
              f"{rj.pl(licznik['wynik_proc'], 2, True)}% [U] (limit: 2 / −2,6%)")
    if info["kierunek"]:
        print(f"BIAS: {info['kierunek']} (D1) | konfluencja MTF: "
              f"{', '.join(info['zgodne']) or '—'} – {info['konfluencja']}/3")
    if info["checklista"]:
        ch = info["checklista"]
        fmt = {True: "TAK", False: "NIE", None: "– brak danych"}
        print("Checklista FIRE: " + " | ".join(
            f"[{k[0]}] {k[2:].replace('_', ' ')}: {fmt[x]}" for k, x in ch.items()))
        print(f"Filtr makro: {info['makro']}")
    s = info["setup"]
    if s:
        print(f"Setup po kosztach: entry {s['entry']} | SL {s['sl']} | TP {s['tp']} | spread "
              f"{s['spread']} | lot {s['lot']} | ryzyko {s['ryzyko_pln']} PLN "
              f"({rj.pl(s['ryzyko_proc'], 2)}%) | RR 1:{rj.pl(s['rr'], 2)}")
    for w in info["ostrzezenia"]:
        print(f"⚠ {w}")
    print("\nOdpowiedzi Jev (tak >= próg, nie <= próg):")
    for key, val in v.items():
        noul = answers.get(key, {}).get("noul")
        note = f"  ← ocena analityka (model: {model_v[key]})" if key in overrides else ""
        print(f"  {key:24} noul={noul if noul is not None else '-':<6} {val}{note}")
    print(f"\nSTATUS: {status} – {reason}")
    print("Analiza edukacyjna, nie porada inwestycyjna. CFD: większość rachunków "
          "detalicznych traci kapitał.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("payload")
    ap.add_argument("--log", default="renko_log.jsonl")
    ap.add_argument("--rejestr", help="rejestr transakcji (licznik dnia), np. renko_rejestr.jsonl")
    ap.add_argument("--blokady", default="renko_blokady.jsonl", help="rejestr blokad")
    ap.add_argument("--yes", type=float, default=0.7, help="próg 'tak' dla noul")
    ap.add_argument("--no", type=float, default=0.3, help="próg 'nie' dla noul")
    ap.add_argument("--override", action="append", default=[], metavar="KLUCZ=tak|nie",
                    help="ocena analityka dla pytania; zapisywana w dzienniku obok odpowiedzi modelu")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not (0 <= args.no < args.yes <= 1):
        sys.exit("Progi muszą spełniać 0 <= --no < --yes <= 1")
    overrides = jr.parse_overrides(args.override, DECISION_KEYS)

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    payload.setdefault("model", "jev-latest")
    validate(payload)
    dane = payload.get("dane", {})
    czas = parse_czas(dane)
    licznik = None
    if args.rejestr:
        if czas is None:
            sys.exit("--rejestr wymaga dane.czas")
        licznik = rj.licznik_dnia(rj.wczytaj(Path(args.rejestr)), f"{czas:%Y-%m-%d}", czas)
    print("Walidacja OK.")
    if args.dry_run:
        return

    resp = jz.ask({k: payload[k] for k in JEV_FIELDS})
    answers = jr.extract_answers(resp)
    model_v = decide(answers, args.yes, args.no, None, dane, licznik)[2]
    status, reason, v, info = decide(answers, args.yes, args.no, overrides, dane, licznik)
    record = {
        "timestamp": datetime.now(jr.TZ).isoformat(timespec="seconds"),
        "model": resp.get("model", payload["model"]),
        "payload_file": args.payload,
        "state_sha256": hashlib.sha256(
            jr.canonical(payload["state"]).encode()).hexdigest()[:16],
        "questions_sha256": hashlib.sha256(
            json.dumps(payload["questions"], sort_keys=True).encode()).hexdigest()[:16],
        "dane": dane,
        "answers": answers,
        "decision": {"result": status, "reason": reason, "inputs": v, "info": info,
                     "licznik": licznik, "thresholds": {"yes": args.yes, "no": args.no},
                     "overrides": {k: {"analityk": val, "model": model_v[k],
                                       "noul": answers.get(k, {}).get("noul")}
                                   for k, val in overrides.items()}},
        "usage": resp.get("usage"),
        "raw": resp,
    }
    with Path(args.log).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    raport(status, reason, v, info, answers, dane, record["model"], licznik, overrides, model_v)
    if overrides:
        model_status = decide(answers, args.yes, args.no, None, dane, licznik)[0]
        if model_status != status:
            print(f"Status bez ocen analityka: {model_status}")
    if info["blokady"]:
        wpis = blokada_wpis(dane, info, czas)
        with Path(args.blokady).open("a", encoding="utf-8") as f:
            f.write(json.dumps(wpis, ensure_ascii=False) + "\n")
        print(f"\n{wpis['wklejka']}\nZapisano blokadę do {args.blokady}")
    print(f"Zapisano do {args.log}")
    sys.exit(EXIT_CODES[status])


if __name__ == "__main__":
    main()
