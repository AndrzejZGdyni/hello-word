#!/usr/bin/env python3
"""Minimalny klient Jev (TypeSafe) przez OpenRouter System One API.

Użycie:
  python3 tools/jev_decide.py "opis sytuacji" pytanie.json
  python3 tools/jev_decide.py "opis sytuacji" --yesno "Czy klient jest sfrustrowany?"
  python3 tools/jev_decide.py "opis sytuacji" --choice "Który dział?" techniczny rozliczenia

Klucz: zmienna środowiskowa OPENROUTER_API_KEY. Model: JEV_MODEL (domyślnie typesafe/jev-1.13).
"""
import json
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("JEV_URL", "https://openrouter.ai/api/v1/systemone")
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.13")


def build_questions(args):
    if args[0] == "--yesno":
        return {"q": {"type": "noul", "instructions": args[1]}}
    if args[0] == "--choice":
        return {"q": {"type": "choice", "instructions": args[1],
                      "criteria": {opt: opt for opt in args[2:]}}}
    with open(args[0], encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("Brak zmiennej OPENROUTER_API_KEY")
    body = {"model": MODEL, "state": sys.argv[1], "questions": build_questions(sys.argv[2:])}
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(json.dumps(json.load(resp), indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}")


if __name__ == "__main__":
    main()
