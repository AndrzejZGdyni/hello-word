#!/usr/bin/env python3
"""Test wariantów zestawu zimowego: każdy wariant N razy, decyzje i odpowiedzi do CSV.

Uruchamiać w katalogu tools/jev-zima; klucz jak w jev_zima.py. Kolumna 'oczekiwany'
to wynik, jakiego wymaga tabela decyzyjna dla danego opisu; niezgodność wypisywana
jest jako NIEZGODNOŚĆ.
"""
import csv
import json
from collections import Counter

import jev_zima as z

ITERATIONS = 3
OUT = "zima_warianty.csv"

VARIANTS = {
    "Z0": ("UWAGA", "Stan na 28.10.2026. Modele meteorologiczne ECMWF i NOAA dla Pomorza wskazują na grudzień w normie termicznej, ale z rosnącym ryzykiem rozbicia wiru polarnego w styczniu i lutym, co może przynieść nagłe, silne fale mrozów. Na rynku paliw stałych podaż jest stabilna: węgiel sortymentu Orzech (Big-Bag 1000 kg) jest regularnie dostępny w e-sklepie PGG, a dostawy kurierskie realizowane są bez opóźnień. Polskie Sieci Elektroenergetyczne (PSE) utrzymują bezpieczną rezerwę mocy, jednak w przypadku mrozów połączonych z brakiem generacji wiatrowej rośnie ryzyko wahań napięcia lub apeli o ograniczenie poboru. Magazyny gazu są pełne, co stabilizuje makroekonomiczny system grzewczy."),
    "Z1": ("OK", "Stan na 05.12.2026. Według IMGW temperatury na Pomorzu w najbliższym tygodniu 2–6°C, powyżej normy; prognozy sezonowe ECMWF nie wskazują zaburzeń wiru polarnego. Węgiel Orzech jest dostępny w e-sklepie PGG i na składach, zamówienia dostarczane w terminie. PSE raportuje rezerwę mocy na bezpiecznym poziomie i nie wydało żadnych komunikatów o ograniczeniach."),
    "Z2": ("ALERT", "Stan na 10.12.2026. Według IMGW temperatury na Pomorzu w najbliższym tygodniu 1–5°C. W e-sklepie PGG węgiel Orzech jest niedostępny od 10 dni, a składy w regionie wprowadziły limit 1 tony na klienta. Zamówienia złożone przed brakami są dostarczane w terminie. PSE utrzymuje bezpieczną rezerwę mocy."),
    "Z3": ("KRYTYCZNE", "Stan na 20.01.2027. Na Pomorzu trwa fala mrozów: według IMGW temperatury nocą do −22°C, ostrzeżenia 3. stopnia ważne do końca tygodnia. PSE ogłosiło 11. stopień zasilania dla odbiorców przemysłowych i zaapelowało do gospodarstw domowych o ograniczenie zużycia energii w godzinach 17–20. Węgiel jest dostępny w sprzedaży, dostawy realizowane z kilkudniowym opóźnieniem."),
    "Z4": ("UWAGA", "Stan na 15.11.2026. Według IMGW temperatury w najbliższym tygodniu w normie (0–4°C); prognozy sezonowe bez sygnałów zaburzenia wiru polarnego. Węgiel Orzech jest dostępny w e-sklepie PGG, ale firmy kurierskie zgłaszają 2–3 tygodnie opóźnienia w dostawach Big-Bagów. PSE raportuje bezpieczną rezerwę mocy."),
}


def main():
    base = json.load(open("zima_template.json", encoding="utf-8"))
    rows, decisions = [], {}
    for name, (expected, state) in VARIANTS.items():
        for i in range(1, ITERATIONS + 1):
            resp = z.ask(dict(base, state=state))
            answers = z.jr.extract_answers(resp)
            result, reason, _ = z.decide(answers, 0.7, 0.3)
            row = {"variant": name, "iteration": i, "oczekiwany": expected,
                   "decision": result, "reason": reason}
            row.update({k: a.get("noul") for k, a in answers.items()})
            rows.append(row)
            print(f"[{name} #{i}] {result} – {reason}")
        decisions[name] = (expected, Counter(r["decision"] for r in rows if r["variant"] == name))
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
