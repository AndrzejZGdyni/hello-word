#!/usr/bin/env python3
"""
jev_zima.py — ocena gotowości domowego ogrzewania na zimę modelem Jev
(TypeSafe System One). Jev odpowiada na pytania o raport, tabela decyzyjna
w kodzie (decide) wyznacza poziom. Opis: README.md w tym katalogu.

Użycie:
    python jev_zima.py zima_RRRR-MM-DD.json --dry-run
    python jev_zima.py zima_RRRR-MM-DD.json --log zima_log.jsonl
    (klucz: TYPESAFE_API_KEY poza sesją Claude Code w chmurze; w niej dodaje go proxy)

Kody wyjścia: 0 — OK, 1 — błąd, 2 — KRYTYCZNE, 3 — ALERT, 4 — SPRAWDŹ, 5 — UWAGA.

Wspólne funkcje (klucz API, endpoint, odczyt odpowiedzi, progi noul) pochodzą
z ../jev-run/jev_run.py.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

_spec = importlib.util.spec_from_file_location(
    "jev_run", Path(__file__).resolve().parent.parent / "jev-run" / "jev_run.py")
jr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jr)

VORTEX_KEY = "vortex_disruption_risk"
COLD_KEY = "cold_wave_imminent"
COAL_KEY = "coal_unavailable"
DELAY_KEY = "coal_delivery_delays"
GRID_EMERGENCY_KEY = "grid_emergency_measures"
GRID_RESERVE_KEY = "grid_reserve_low"
DECISION_KEYS = (VORTEX_KEY, COLD_KEY, COAL_KEY, DELAY_KEY,
                 GRID_EMERGENCY_KEY, GRID_RESERVE_KEY)

EXIT_CODES = {"OK": 0, "KRYTYCZNE": 2, "ALERT": 3, "SPRAWDŹ": 4, "UWAGA": 5}


def validate(payload: dict) -> None:
    errors = []
    state = payload.get("state")
    if not isinstance(state, (str, dict, list)) or jr.is_empty(state):
        errors.append("brak lub puste pole 'state'")
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
            instr = q.get("instructions")
            if jr.is_empty(instr) or (isinstance(instr, str) and instr.strip().startswith("[")):
                errors.append(f"{key}: brak lub szablonowe 'instructions'")
    if errors:
        sys.exit("Błędy walidacji:\n  - " + "\n  - ".join(errors))


def decide(answers: dict, yes: float, no: float) -> tuple[str, str, dict]:
    """Tabela decyzyjna; reguły sprawdzane od góry, wygrywa pierwsza pasująca."""
    v = {k: jr.classify(answers.get(k, {}).get("noul"), yes, no) for k in DECISION_KEYS}
    if v[COLD_KEY] == "tak" and (v[COAL_KEY] == "tak" or v[GRID_EMERGENCY_KEY] == "tak"):
        return "KRYTYCZNE", "mróz przy brakach opału lub ograniczeniach zasilania", v
    if v[COAL_KEY] == "tak":
        return "ALERT", "braki węgla w sprzedaży", v
    if v[GRID_EMERGENCY_KEY] == "tak":
        return "ALERT", "stopnie zasilania lub apel o ograniczenie poboru", v
    if v[COLD_KEY] == "tak":
        return "ALERT", "fala mrozów teraz lub w ciągu 7 dni", v
    if v[DELAY_KEY] == "tak" or v[GRID_RESERVE_KEY] == "tak":
        return "UWAGA", "opóźnienia dostaw opału lub niska rezerwa mocy", v
    if v[VORTEX_KEY] == "tak":
        return "UWAGA", "ryzyko rozbicia wiru polarnego w dalszej perspektywie", v
    if "nierozstrzygnięte" in v.values():
        return "SPRAWDŹ", "odpowiedź nierozstrzygnięta lub brakująca; uzupełnij state", v
    return "OK", "brak przesłanek zagrożenia", v


def ask(payload: dict) -> dict:
    try:
        r = requests.post(
            jr.API_URL,
            headers=jr.auth_headers(), json=payload, timeout=60,
        )
    except requests.RequestException as e:
        sys.exit(f"Błąd połączenia: {e}")
    if r.status_code == 401:
        sys.exit("HTTP 401: brak lub zły klucz. Ustaw TYPESAFE_API_KEY albo uruchom w sesji "
                 "Claude Code ze środowiskiem, w którym TypeSafe jest podłączony.")
    if r.status_code != 200:
        sys.exit(f"HTTP {r.status_code}: {r.text[:500]}")
    return r.json()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("payload")
    ap.add_argument("--log", default="zima_log.jsonl")
    ap.add_argument("--yes", type=float, default=0.7, help="próg 'tak' dla noul")
    ap.add_argument("--no", type=float, default=0.3, help="próg 'nie' dla noul")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not (0 <= args.no < args.yes <= 1):
        sys.exit("Progi muszą spełniać 0 <= --no < --yes <= 1")

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    payload.setdefault("model", "jev-latest")
    validate(payload)
    print("Walidacja OK.")
    if args.dry_run:
        return

    resp = ask(payload)
    answers = jr.extract_answers(resp)
    result, reason, inputs = decide(answers, args.yes, args.no)
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
                     "thresholds": {"yes": args.yes, "no": args.no}},
        "usage": resp.get("usage"),
        "raw": resp,
    }
    log = Path(args.log)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n{record['timestamp']}  model={record['model']}")
    for name, a in answers.items():
        print(f"  {name}: {a}")
    print(f"\nTabela decyzyjna (tak >= {args.yes:.2f}, nie <= {args.no:.2f}):")
    for key, val in inputs.items():
        print(f"  {key}: {val}")
    print(f"Wynik: {result} – {reason}")
    print(f"\nZapisano do {log}")
    sys.exit(EXIT_CODES[result])


if __name__ == "__main__":
    main()
