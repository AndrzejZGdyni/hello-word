#!/usr/bin/env python3
"""
jev_run.py — wysyła payload do Jev (TypeSafe System One), dopisuje wynik
do dziennika JSONL i sygnalizuje przekroczenie progu decyzyjnego.

Użycie:
    python jev_run.py jev_hormuz_2026-10-26.json
    python jev_run.py payload.json --dry-run        # walidacja bez wysyłki
    python jev_run.py payload.json --yes 0.7 --no 0.3 --log jev_log.jsonl

Klucz API: zmienna TYPESAFE_API_KEY lub plik ~/.typesafe/api_key. W sesji Claude Code
w chmurze z podłączonym TypeSafe klucz wstrzykuje proxy i żaden z nich nie jest potrzebny.
Endpoint i autoryzacja zgodne z https://api.typesafe.ai/openapi.json
(POST /v1/systemone, nagłówek "Authorization: Bearer <klucz>").

Decyzję podejmuje tabela decyzyjna (decide) na podstawie pięciu pytań typu noul
i dominującego poziomu skali production_loss_level;
opis w WZOR_PYTANIA.md, sekcja 4. Brzmienie pytań: jev_hormuz_template.json.

Kody wyjścia: 0 — OK, 1 — błąd (walidacja, sieć, HTTP), 2 — TRIP, 3 — ALERT,
4 — SPRAWDŹ (odpowiedź nierozstrzygnięta lub brakująca).
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_URL = os.environ.get("TYPESAFE_URL", "https://api.typesafe.ai/v1/systemone")
AUTH_HEADER = "Authorization"
AUTH_PREFIX = "Bearer "
TZ = ZoneInfo("Europe/Warsaw")

# Pytania wejściowe tabeli decyzyjnej (WZOR_PYTANIA.md, sekcja 4).
HALTED_KEY = "hormuz_transit_halted"
CLOSURE_KEY = "immediate_closure_probability"
MINES_KEY = "mines_confirmed"
FLOW_DROP_KEY = "flow_drop_significant"
STEPS_KEY = "formal_closure_steps"
DECISION_KEYS = (HALTED_KEY, CLOSURE_KEY, MINES_KEY, FLOW_DROP_KEY, STEPS_KEY)
PRODUCTION_KEY = "production_loss_level"
PRODUCTION_ALERT_LEVEL = 3   # utrata mocy rzędu 1 mln bbl/d i więcej

EXIT_CODES = {"OK": 0, "TRIP": 2, "ALERT": 3, "SPRAWDŹ": 4}


def load_key() -> str:
    """Klucz z TYPESAFE_API_KEY lub ~/.typesafe/api_key; pusty, gdy brak obu."""
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        return key.strip()
    path = Path.home() / ".typesafe" / "api_key"
    if path.exists():
        return path.read_text().strip()
    return ""


def auth_headers() -> dict:
    """Nagłówki żądania. Bez klucza nie wysyła Authorization: w sesji w chmurze
    klucz dodaje proxy, a poza nią API odpowie 401 z czytelnym komunikatem."""
    headers = {"Content-Type": "application/json"}
    key = load_key()
    if key:
        headers[AUTH_HEADER] = AUTH_PREFIX + key
    return headers


def canonical(value) -> str:
    """Tekst do hashowania; 'state' i 'instructions' mogą być str, dict lub list."""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def is_empty(value) -> bool:
    return not value or (isinstance(value, str) and not value.strip())


def validate(payload: dict) -> None:
    errors = []
    state = payload.get("state")
    if not isinstance(state, (str, dict, list)) or is_empty(state):
        errors.append("brak lub puste pole 'state'")
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not questions:
        errors.append("brak słownika 'questions'")
    else:
        for name, q in questions.items():
            qtype = q.get("type")
            if qtype not in ("noul", "score", "choice", "box"):
                errors.append(f"{name}: nieznany typ {qtype!r}")
            instr = q.get("instructions")
            if is_empty(instr) or (isinstance(instr, str) and instr.strip().startswith("[")):
                errors.append(f"{name}: brak lub szablonowe 'instructions'")
            if qtype == "score":
                # API dopuszcza 1–10 poziomów; jeden poziom nie niesie informacji.
                crit = q.get("criteria", [])
                if not isinstance(crit, list) or not (2 <= len(crit) <= 10):
                    errors.append(f"{name}: 'criteria' musi być listą 2–10 poziomów")
            if qtype == "choice":
                crit = q.get("criteria")
                if not isinstance(crit, dict) or not crit:
                    errors.append(f"{name}: 'criteria' musi być słownikiem opcji")
        for key in DECISION_KEYS:
            q = questions.get(key)
            if q is None:
                errors.append(f"{key}: brak pytania wymaganego przez tabelę decyzyjną")
            elif q.get("type") != "noul":
                errors.append(f"{key}: pytanie decyzyjne musi być typu 'noul'")
        q = questions.get(PRODUCTION_KEY)
        if q is None:
            errors.append(f"{PRODUCTION_KEY}: brak pytania wymaganego przez tabelę decyzyjną")
        elif q.get("type") != "score":
            errors.append(f"{PRODUCTION_KEY}: pytanie musi być typu 'score'")
    if errors:
        sys.exit("Błędy walidacji:\n  - " + "\n  - ".join(errors))


def extract_answers(resp: dict) -> dict:
    """Zwraca {klucz: wartość} według pola 'type' odpowiedzi (SystemOneResponse)."""
    out = {}
    for name, a in resp.get("answers", {}).items():
        if not isinstance(a, dict):
            continue
        t = a.get("type")
        if t == "noul":
            out[name] = {"noul": a["noul"]}
        elif t == "score":
            out[name] = {"score": a["score"], "confidence": a.get("confidence"),
                         "probabilities": a.get("probabilities")}
        elif t == "choice":
            out[name] = {"choice": a["choice"], "confidence": a.get("confidence"),
                         "probabilities": a.get("probabilities")}
        elif t == "box":
            out[name] = {"box": a["box"], "confidence": a.get("confidence")}
    return out


def classify(p, yes: float, no: float) -> str:
    """Noul -> 'tak' / 'nie' / 'nierozstrzygnięte' (brak odpowiedzi też)."""
    if p is None:
        return "nierozstrzygnięte"
    if p >= yes:
        return "tak"
    if p <= no:
        return "nie"
    return "nierozstrzygnięte"


def dominant_level(answer: dict):
    """Poziom skali o najwyższym prawdopodobieństwie (nie średnia 'score')."""
    probs = (answer or {}).get("probabilities")
    if not probs:
        return None
    return int(max(probs, key=probs.get))


def decide(answers: dict, yes: float, no: float) -> tuple[str, str, dict]:
    """Tabela decyzyjna; reguły sprawdzane od góry, wygrywa pierwsza pasująca."""
    v = {k: classify(answers.get(k, {}).get("noul"), yes, no) for k in DECISION_KEYS}
    halted, closure, mines = v[HALTED_KEY], v[CLOSURE_KEY], v[MINES_KEY]
    flow_drop, steps = v[FLOW_DROP_KEY], v[STEPS_KEY]
    production = dominant_level(answers.get(PRODUCTION_KEY))
    v[PRODUCTION_KEY] = production
    if halted == "tak":
        return "TRIP", "tranzyt wstrzymany", v
    if halted == "nie" and closure == "tak" and mines == "tak":
        return "TRIP", "zamknięcie zapowiedziane i wsparte minami", v
    if halted == "nie" and closure == "tak":
        return "ALERT", "zapowiedź zamknięcia bez potwierdzenia min", v
    if halted == "nie" and closure == "nie" and mines == "tak":
        return "ALERT", "miny potwierdzone, brak zapowiedzi zamknięcia", v
    if halted == "nie" and flow_drop == "tak":
        return "ALERT", "wyraźny spadek przepływów bez wstrzymania tranzytu", v
    if halted == "nie" and closure == "nie" and steps == "tak":
        return "ALERT", "formalne kroki w kierunku zamknięcia bez decyzji", v
    if production is not None and production >= PRODUCTION_ALERT_LEVEL:
        return "ALERT", "duża utrata mocy wydobywczych lub przetwórczych", v
    if "nierozstrzygnięte" in v.values():
        return "SPRAWDŹ", "odpowiedź nierozstrzygnięta lub brakująca; uzupełnij state", v
    return "OK", "brak przesłanek zamknięcia ani dużej utraty mocy", v


def last_decision(log: Path):
    if not log.exists():
        return None
    for line in reversed(log.read_text(encoding="utf-8").splitlines()):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        dec = rec.get("decision", {}).get("result")
        if dec is not None:
            return dec, rec.get("timestamp")
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("payload")
    ap.add_argument("--log", default="jev_log.jsonl")
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

    try:
        r = requests.post(
            API_URL,
            headers=auth_headers(), json=payload, timeout=60,
        )
    except requests.RequestException as e:
        sys.exit(f"Błąd połączenia: {e}")
    if r.status_code == 401:
        sys.exit("HTTP 401: brak lub zły klucz. Ustaw TYPESAFE_API_KEY albo uruchom w sesji "
                 "Claude Code ze środowiskiem, w którym TypeSafe jest podłączony.")
    if r.status_code != 200:
        sys.exit(f"HTTP {r.status_code}: {r.text[:500]}")
    resp = r.json()
    answers = extract_answers(resp)

    log = Path(args.log)
    prev = last_decision(log)
    result, reason, inputs = decide(answers, args.yes, args.no)
    record = {
        "timestamp": datetime.now(TZ).isoformat(timespec="seconds"),
        "model": resp.get("model", payload["model"]),
        "payload_file": args.payload,
        "state_sha256": hashlib.sha256(
            canonical(payload["state"]).encode()).hexdigest()[:16],
        "questions_sha256": hashlib.sha256(
            json.dumps(payload["questions"], sort_keys=True).encode()).hexdigest()[:16],
        "answers": answers,
        "decision": {"result": result, "reason": reason, "inputs": inputs,
                     "thresholds": {"yes": args.yes, "no": args.no}},
        "usage": resp.get("usage"),
        "raw": resp,
    }
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n{record['timestamp']}  model={record['model']}")
    for name, a in answers.items():
        print(f"  {name}: {a}")

    print(f"\nTabela decyzyjna (tak >= {args.yes:.2f}, nie <= {args.no:.2f}):")
    for key, val in inputs.items():
        print(f"  {key}: {val}")
    print(f"Wynik: {result} – {reason}")
    if prev:
        print(f"Poprzednio: {prev[0]} ({prev[1]})")
    print(f"\nZapisano do {log}")
    sys.exit(EXIT_CODES[result])


if __name__ == "__main__":
    main()
