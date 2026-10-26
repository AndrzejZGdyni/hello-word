#!/usr/bin/env python3
"""
jev_run.py — wysyła payload do Jev (TypeSafe System One), dopisuje wynik
do dziennika JSONL i sygnalizuje przekroczenie progu decyzyjnego.

Użycie:
    python jev_run.py jev_hormuz_2026-10-26.json
    python jev_run.py payload.json --dry-run        # walidacja bez wysyłki
    python jev_run.py payload.json --threshold 0.9 --log jev_log.jsonl

Klucz API: zmienna TYPESAFE_API_KEY lub plik ~/.typesafe/api_key.
Endpoint i autoryzacja zgodne z https://api.typesafe.ai/openapi.json
(POST /v1/systemone, nagłówek "Authorization: Bearer <klucz>").

Kody wyjścia: 0 — OK, 1 — błąd (walidacja, sieć, HTTP), 2 — TRIP (p >= próg).
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
TRIP_KEY = "immediate_closure_probability"
TZ = ZoneInfo("Europe/Warsaw")
EXIT_TRIP = 2


def load_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        return key.strip()
    path = Path.home() / ".typesafe" / "api_key"
    if path.exists():
        return path.read_text().strip()
    sys.exit("Brak klucza: ustaw TYPESAFE_API_KEY lub ~/.typesafe/api_key")


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
        trip_q = questions.get(TRIP_KEY)
        if trip_q is not None and trip_q.get("type") != "noul":
            errors.append(f"{TRIP_KEY}: pytanie progowe musi być typu 'noul'")
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


def last_value(log: Path, key: str):
    if not log.exists():
        return None
    for line in reversed(log.read_text(encoding="utf-8").splitlines()):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        val = rec.get("answers", {}).get(key, {}).get("noul")
        if val is not None:
            return val, rec.get("timestamp")
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("payload")
    ap.add_argument("--log", default="jev_log.jsonl")
    ap.add_argument("--threshold", type=float, default=0.90)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    payload.setdefault("model", "jev-latest")
    validate(payload)
    print("Walidacja OK.")
    if args.dry_run:
        return

    try:
        r = requests.post(
            API_URL,
            headers={AUTH_HEADER: AUTH_PREFIX + load_key(),
                     "Content-Type": "application/json"},
            json=payload, timeout=60,
        )
    except requests.RequestException as e:
        sys.exit(f"Błąd połączenia: {e}")
    if r.status_code != 200:
        sys.exit(f"HTTP {r.status_code}: {r.text[:500]}")
    resp = r.json()
    answers = extract_answers(resp)

    log = Path(args.log)
    prev = last_value(log, TRIP_KEY)
    record = {
        "timestamp": datetime.now(TZ).isoformat(timespec="seconds"),
        "model": resp.get("model", payload["model"]),
        "payload_file": args.payload,
        "state_sha256": hashlib.sha256(
            canonical(payload["state"]).encode()).hexdigest()[:16],
        "questions_sha256": hashlib.sha256(
            json.dumps(payload["questions"], sort_keys=True).encode()).hexdigest()[:16],
        "answers": answers,
        "usage": resp.get("usage"),
        "raw": resp,
    }
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n{record['timestamp']}  model={record['model']}")
    for name, a in answers.items():
        print(f"  {name}: {a}")

    tripped = False
    trip = answers.get(TRIP_KEY, {}).get("noul")
    if trip is not None:
        if prev:
            print(f"\n{TRIP_KEY}: {trip:.3f} (poprzednio {prev[0]:.3f}, {prev[1]})")
        tripped = trip >= args.threshold
        print(f"Próg p>={args.threshold:.2f}: {'TRIP' if tripped else 'OK'}")
    elif TRIP_KEY in payload["questions"]:
        print(f"\nUWAGA: brak odpowiedzi '{TRIP_KEY}' w wyniku")
    print(f"\nZapisano do {log}")
    if tripped:
        sys.exit(EXIT_TRIP)


if __name__ == "__main__":
    main()
