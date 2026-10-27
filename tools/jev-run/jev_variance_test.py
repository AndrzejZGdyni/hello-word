#!/usr/bin/env python3
"""Test wariancji Jev: warianty W1–W4, N przebiegów, surowe wyniki i rozkłady do CSV.

Uruchamiać w katalogu tools/jev-run. Wymaga TYPESAFE_API_KEY w środowisku
(obsługiwanego przez jev_run.py). Pytania pochodzą z jev_hormuz_template.json;
wariant V4 to stan wzorcowy z 26.10.2026 (kontrola regresji, oczekiwany wynik OK).
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict

VARIANTS = {
    "V4": "Stan na 26.10.2026 rano. Według danych Washington Institute w październiku odnotowano 28 ataków na statki handlowe (113 od 28 lutego), a według IMO w październiku uszkodzono 11 supertankowców VLCC (ponad 30 od początku wojny). Według danych Kpler średni eksport ropy z Bliskiego Wschodu wynosi ponad 24 mln bbl/d wobec przedwojennego poziomu 23,3 mln bbl/d. Ruch Huti zadeklarował uderzenia na saudyjski obiekt Aramco w Yanbu, rafinerię Rabigh oraz rurociąg East-West; Arabia Saudyjska nie potwierdziła tych doniesień. W oficjalnych komunikatach wojskowych brak potwierdzenia postawienia min morskich oraz brak oficjalnych zapowiedzi Iranu o zamknięciu Cieśniny Ormuz. Stawki ubezpieczeń od ryzyka wojennego (War Risk Premium) oraz koszty frachtu wzrosły, natomiast w Teheranie rozpoczęły się rozmowy z mediatorami z Kataru, a notowania WTI na otwarciu sesji spadły z 103,27 USD do 101,65 USD.",
    "W1": "Stan na 28.10.2026. US 5th Fleet potwierdziła wybuch miny kontaktowej pod kadłubem tankowca na wschodnim torze wodnym Cieśniny Ormuz; trałowce wyłowiły dwie kolejne miny. Iran nie ogłosił zamknięcia cieśniny. Według Kpler przepływ ropy przez Ormuz spadł do 17 mln bbl/d (przedwojennie ok. 20,5 mln bbl/d). Arabia Saudyjska nie zgłasza uszkodzeń infrastruktury lądowej.",
    "W2": "Stan na 28.10.2026. Według Kpler przepływ ropy przez Cieśninę Ormuz wynosi 12,3 mln bbl/d wobec ok. 20,5 mln bbl/d przed wojną; część armatorów wstrzymała rejsy z powodu ataków dronów. Brak potwierdzeń zaminowania akwenu i brak oficjalnej zapowiedzi Iranu o zamknięciu cieśniny. Infrastruktura saudyjska bez potwierdzonych uszkodzeń.",
    "W3": "Stan na 28.10.2026. Saudi Aramco oficjalnie potwierdziła uszkodzenie zakładu przetwórczego Abqaiq; szacowana utrata ok. 5 mln bbl/d na co najmniej 3 miesiące. Tranzyt przez Cieśninę Ormuz w normie (ok. 20,8 mln bbl/d według Kpler). Brak ataków na statki w ostatnich 7 dniach, brak doniesień o minach.",
    "W4": "Stan na 28.10.2026. Irański parlament przyjął rezolucję rekomendującą zamknięcie Cieśniny Ormuz; Najwyższa Rada Bezpieczeństwa Narodowego nie podjęła decyzji. UKMTO zgłasza niezidentyfikowany obiekt pływający na torze wodnym, US Navy prowadzi rozpoznanie bez potwierdzenia. Przepływ przez cieśninę niższy o ok. 15% względem okresu przedwojennego; ataki na statki trwają.",
}

TEMPLATE = "jev_hormuz_template.json"
RUNNER = "jev_run.py"
LOG = "jev_log.jsonl"
ANSWERS_KEY = "answers"
HASH_KEY = "questions_sha256"
ITERATIONS = 5
TIMEOUT_S = 180
OUT_RAW = "jev_variance_raw.csv"
OUT_SUMMARY = "jev_variance_summary.csv"
META = ("variant", "iteration", HASH_KEY)
# Kody wyjścia jev_run.py: 0 OK, 2 TRIP, 3 ALERT, 4 SPRAWDŹ to poprawne przebiegi; 1 to błąd.
RUNNER_OK_CODES = {0, 2, 3, 4}


def count_lines(path):
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def read_last(path):
    with open(path, encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    return json.loads(lines[-1])


def flatten(prefix, value, row):
    """Spłaszcza zagnieżdżone odpowiedzi, np. {"p": 0.12, "label": "false"}."""
    if isinstance(value, dict):
        for k, v in value.items():
            flatten(f"{prefix}.{k}", v, row)
    else:
        row[prefix] = value


def run_variant(name, payload):
    rows = []
    fd, tmp = tempfile.mkstemp(prefix=f"jev_{name}_", suffix=".json", dir=".")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    try:
        for i in range(1, ITERATIONS + 1):
            tag = f"[{name} #{i}/{ITERATIONS}]"
            before = count_lines(LOG)
            try:
                res = subprocess.run(
                    [sys.executable, RUNNER, tmp, "--log", LOG],
                    capture_output=True, text=True, timeout=TIMEOUT_S,
                )
            except subprocess.TimeoutExpired:
                print(f"{tag} przekroczony limit czasu – pomijam")
                continue
            if res.returncode not in RUNNER_OK_CODES:
                print(f"{tag} błąd (kod {res.returncode}): {res.stderr.strip()[:300]}")
                continue
            if count_lines(LOG) <= before:
                print(f"{tag} brak nowego wpisu w {LOG} – pomijam (ochrona przed odczytem starego wyniku)")
                continue
            last = read_last(LOG)
            row = {"variant": name, "iteration": i, HASH_KEY: last.get(HASH_KEY, "")}
            row["decision"] = last.get("decision", {}).get("result", "")
            for q, v in last.get(ANSWERS_KEY, {}).items():
                flatten(q, v, row)
            rows.append(row)
            print(f"{tag} {row['decision']}")
    finally:
        os.remove(tmp)
    return rows


def write_raw(rows):
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(OUT_RAW, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows):
    """Rozkład zamiast średniej: średnia ukrywa odczyty dwumodalne (cel testu W3)."""
    values = defaultdict(list)
    for r in rows:
        for k, v in r.items():
            if k not in META and v is not None:
                values[(r["variant"], k)].append(v)
    with open(OUT_SUMMARY, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "question", "n", "min", "max", "rozklad"])
        for (variant, q), vals in sorted(values.items()):
            numeric = [v for v in vals if isinstance(v, (int, float))]
            if numeric and len(numeric) == len(vals):
                dist = Counter(round(float(v), 2) for v in vals)
                vmin, vmax = min(numeric), max(numeric)
            else:
                dist = Counter(str(v) for v in vals)
                vmin = vmax = ""
            dist_str = "; ".join(f"{k}:{c}" for k, c in sorted(dist.items(), key=lambda x: str(x[0])))
            writer.writerow([variant, q, len(vals), vmin, vmax, dist_str])


def main():
    with open(TEMPLATE, encoding="utf-8") as f:
        base = json.load(f)
    rows = []
    for name, state in VARIANTS.items():
        print(f"Wariant {name}")
        rows.extend(run_variant(name, dict(base, state=state)))
    if not rows:
        print("Brak poprawnych przebiegów – nic nie zapisano.")
        return
    hashes = {r[HASH_KEY] for r in rows}
    if len(hashes) > 1:
        print(f"UWAGA: w serii wystąpiło {len(hashes)} różnych hashy: {sorted(hashes)}")
    write_raw(rows)
    write_summary(rows)
    print(f"\nZapisano: {OUT_RAW} ({len(rows)} przebiegów), {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
