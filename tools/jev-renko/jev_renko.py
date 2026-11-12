#!/usr/bin/env python3
"""
jev_renko.py — decyzja KUP / SPRZEDAJ / CZEKAJ dla wykresów Renko (D1, H1, M5)
modelem Jev (TypeSafe System One). Jev odpowiada na pytania o opis wykresów
w `state`, decyzję wyznacza tabela decyzyjna w kodzie (decide). Opis: README.md.

Użycie:
    python jev_renko.py renko_RRRR-MM-DD_GGMM.json --dry-run
    python jev_renko.py renko_RRRR-MM-DD_GGMM.json --log renko_log.jsonl
    python jev_renko.py renko_RRRR-MM-DD_GGMM.json --override m5_sell_trigger=nie
    (klucz: TYPESAFE_API_KEY poza sesją Claude Code w chmurze; w niej dodaje go proxy)

Kody wyjścia: 0 — CZEKAJ, 1 — błąd, 2 — SPRZEDAJ, 3 — KUP, 4 — SPRAWDŹ.

Narzędzie interpretuje zestaw wskaźników; nie jest rekomendacją inwestycyjną.
Wspólne funkcje (klucz API, endpoint, odczyt odpowiedzi, progi noul) pochodzą
z ../jev-run/jev_run.py; zapytanie i dziennik jak w ../jev-zima/jev_zima.py.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

_here = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


jr = _load("jev_run", _here.parent / "jev-run" / "jev_run.py")
jz = _load("jev_zima", _here.parent / "jev-zima" / "jev_zima.py")

D1_BEAR, D1_BULL = "d1_bearish", "d1_bullish"
H1_BEAR, H1_BULL = "h1_bearish", "h1_bullish"
M5_SELL, M5_BUY = "m5_sell_trigger", "m5_buy_trigger"
H1_OVERSOLD, H1_OVERBOUGHT = "h1_oversold_extreme", "h1_overbought_extreme"
PROV_UP = ("h1_provisional_up", "m5_provisional_up")
PROV_DOWN = ("h1_provisional_down", "m5_provisional_down")
DECISION_KEYS = (D1_BEAR, D1_BULL, H1_BEAR, H1_BULL, M5_SELL, M5_BUY,
                 H1_OVERSOLD, H1_OVERBOUGHT, *PROV_UP, *PROV_DOWN)
TREND_KEYS = (D1_BEAR, D1_BULL, H1_BEAR, H1_BULL)

EXIT_CODES = {"CZEKAJ": 0, "SPRZEDAJ": 2, "KUP": 3, "SPRAWDŹ": 4}
UNSURE = "nierozstrzygnięte"


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
    if errors:
        sys.exit("Błędy walidacji:\n  - " + "\n  - ".join(errors))


def _entry(v: dict, trigger: str, extreme: str, against: tuple,
           action: str, trend: str, extreme_txt: str, against_txt: str):
    """Wspólna gałąź dla zgodnego trendu D1+H1 (w dół lub w górę).
    against: pytania o cegły tymczasowe przeciw kierunkowi wejścia (H1, M5)."""
    if v[trigger] == "nie":
        return "CZEKAJ", f"trend {trend} na D1 i H1, brak sygnału wejścia na M5"
    if v[trigger] == UNSURE:
        return "SPRAWDŹ", "sygnał wejścia na M5 nierozstrzygnięty; uzupełnij opis M5"
    if v[extreme] == "tak":
        return "CZEKAJ", f"sygnał na M5, ale H1 {extreme_txt}; ryzyko wejścia po dużym ruchu"
    hit = [k.split("_")[0].upper() for k in against if v[k] == "tak"]
    if hit:
        return "CZEKAJ", (f"sygnał na M5, ale tymczasowe cegły {'+'.join(hit)} "
                          f"biegną {against_txt}")
    if UNSURE in (v[extreme], *(v[k] for k in against)):
        return "SPRAWDŹ", "oscylatory H1 lub cegły tymczasowe nierozstrzygnięte"
    return action, f"trend {trend} na D1 i H1, sygnał wejścia na M5"


def decide(answers: dict, yes: float, no: float,
           overrides: dict | None = None) -> tuple[str, str, dict]:
    """Tabela decyzyjna; reguły sprawdzane od góry, wygrywa pierwsza pasująca.
    overrides: oceny analityka zastępujące klasyfikację odpowiedzi modelu."""
    v = {k: jr.classify(answers.get(k, {}).get("noul"), yes, no) for k in DECISION_KEYS}
    v.update(overrides or {})
    bear = v[D1_BEAR] == "tak" and v[H1_BEAR] == "tak"
    bull = v[D1_BULL] == "tak" and v[H1_BULL] == "tak"
    if bear and bull:
        return "SPRAWDŹ", "sprzeczne odpowiedzi: trend jednocześnie spadkowy i wzrostowy", v
    if bear:
        return (*_entry(v, M5_SELL, H1_OVERSOLD, PROV_UP, "SPRZEDAJ", "spadkowy",
                        "skrajnie wyprzedany", "w górę"), v)
    if bull:
        return (*_entry(v, M5_BUY, H1_OVERBOUGHT, PROV_DOWN, "KUP", "wzrostowy",
                        "skrajnie wykupiony", "w dół"), v)
    if any(v[k] == UNSURE for k in TREND_KEYS):
        return "SPRAWDŹ", "trend D1 lub H1 nierozstrzygnięty; uzupełnij opis", v
    return "CZEKAJ", "D1 i H1 bez wspólnego kierunku", v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("payload")
    ap.add_argument("--log", default="renko_log.jsonl")
    ap.add_argument("--yes", type=float, default=0.7, help="próg 'tak' dla noul")
    ap.add_argument("--no", type=float, default=0.3, help="próg 'nie' dla noul")
    ap.add_argument("--override", action="append", default=[], metavar="KLUCZ=tak|nie",
                    help="ocena analityka dla pytania decyzyjnego; zapisywana w dzienniku "
                         "obok odpowiedzi modelu (można podać kilka razy)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not (0 <= args.no < args.yes <= 1):
        sys.exit("Progi muszą spełniać 0 <= --no < --yes <= 1")
    overrides = jr.parse_overrides(args.override, DECISION_KEYS)

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    payload.setdefault("model", "jev-latest")
    validate(payload)
    print("Walidacja OK.")
    if args.dry_run:
        return

    resp = jz.ask(payload)
    answers = jr.extract_answers(resp)
    model_inputs = decide(answers, args.yes, args.no)[2]
    result, reason, inputs = decide(answers, args.yes, args.no, overrides)
    record = {
        "timestamp": datetime.now(jr.TZ).isoformat(timespec="seconds"),
        "model": resp.get("model", payload["model"]),
        "payload_file": args.payload,
        "state_sha256": hashlib.sha256(
            jr.canonical(payload["state"]).encode()).hexdigest()[:16],
        "questions_sha256": hashlib.sha256(
            json.dumps(payload["questions"], sort_keys=True).encode()).hexdigest()[:16],
        "answers": answers,
        "decision": {"result": result, "reason": reason, "inputs": inputs,
                     "thresholds": {"yes": args.yes, "no": args.no},
                     "overrides": {k: {"analityk": val, "model": model_inputs[k],
                                       "noul": answers.get(k, {}).get("noul")}
                                   for k, val in overrides.items()}},
        "usage": resp.get("usage"),
        "raw": resp,
    }
    log = Path(args.log)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n{record['timestamp']}  model={record['model']}")
    print(f"Tabela decyzyjna (tak >= {args.yes:.2f}, nie <= {args.no:.2f}):")
    for key, val in inputs.items():
        noul = answers.get(key, {}).get("noul")
        note = f"  ← ocena analityka (model: {model_inputs[key]})" if key in overrides else ""
        print(f"  {key:24} noul={noul if noul is not None else '-':<6} {val}{note}")
    if overrides:
        model_result = decide(answers, args.yes, args.no)[0]
        if model_result != result:
            print(f"Wynik bez ocen analityka: {model_result}")
    print(f"Wynik: {result} – {reason}")
    print(f"\nZapisano do {log}")
    sys.exit(EXIT_CODES[result])


if __name__ == "__main__":
    main()
