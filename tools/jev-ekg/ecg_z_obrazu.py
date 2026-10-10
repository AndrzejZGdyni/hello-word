#!/usr/bin/env python3
"""Odtwarza załamki R i odstępy RR ze zrzutu EKG (obraz rastrowy) – wyłącznie lokalnie.

MATERIAŁ EDUKACYJNY, nie narzędzie medyczne. Zakłada układ raportu: 3 paski po 10 s, ślad w kolorze
czerwonym na jasnej siatce, nagłówek u góry i stopka u dołu.

Użycie:
  pdftoppm -png -r 72 raport.pdf strona         # PDF → PNG (poppler-utils)
  python3 -I ecg_z_obrazu.py strona-1.png wynik.json [--hr-raport 64] [--kontrola kontrola]

Wymaga: numpy, Pillow. Nie wysyła niczego poza maszynę. Nie dodawaj obrazów do repozytorium.
"""
import argparse, json
import numpy as np
from PIL import Image, ImageDraw

REFRAKCJA_S = 0.40   # po zaakceptowanym R odrzucamy piki (załamek T, drugi pik) w tym oknie
PROG_REL = 0.45      # min. wyniosłość = 45 % mediany wyniosłości 20 najsilniejszych pików
KRAWEDZ_S = 0.5      # piki w pierwszych/ostatnich ~0,5 s – niepewne (artefakty brzegowe)
SEKUND_NA_PASEK = 10


def wczytaj_slad(sciezka):
    img = Image.open(sciezka).convert("RGB")
    a = np.asarray(img).astype(int)
    h, w, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    red = (r > 190) & (g < 150) & (b < 170) & (r - g > 70)      # ślad (z antyaliasingiem)
    red[: int(h * 0.28)] = False                                 # pomiń nagłówek i ikonę
    red[int(h * 0.82):] = False                                  # pomiń stopkę
    rows = np.where(red.any(axis=1))[0]
    paski, start = [], rows[0]
    for p, q in zip(rows[:-1], rows[1:]):
        if q - p > 40:
            paski.append((int(start), int(p))); start = q
    paski.append((int(start), int(rows[-1])))
    cols = np.where(red.any(axis=0))[0]
    return img, red, paski, int(cols.min()), int(cols.max())


def profil(red, ya, yb, x0, x1):
    """Dla każdej kolumny: najwyższy czerwony piksel (górna obwiednia śladu)."""
    xs = np.arange(x0, x1 + 1)
    top = np.full(len(xs), np.nan)
    for i, x in enumerate(xs):
        ys = np.where(red[ya:yb + 1, x])[0]
        if ys.size:
            top[i] = ys.min()
    ok = ~np.isnan(top)
    top = np.interp(np.arange(len(xs)), np.where(ok)[0], top[ok])
    return xs, yb - top                                          # wyżej na obrazie = większa wartość


def maksima_z_wyniosloscia(sig):
    out = []
    for i in range(1, len(sig) - 1):
        if sig[i] >= sig[i - 1] and sig[i] > sig[i + 1]:
            l = i
            while l > 0 and sig[l - 1] <= sig[i]: l -= 1
            r = i
            while r < len(sig) - 1 and sig[r + 1] <= sig[i]: r += 1
            out.append((i, float(sig[i] - max(sig[l:i + 1].min(), sig[i:r + 1].min()))))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("obraz"); ap.add_argument("wynik")
    ap.add_argument("--hr-raport", type=float, help="tętno z nagłówka raportu (kontrola zgodności)")
    ap.add_argument("--kontrola", help="prefiks plików PNG z nałożonymi znacznikami R (do oceny wzrokowej)")
    arg = ap.parse_args()

    img, red, paski, x0, x1 = wczytaj_slad(arg.obraz)
    pxs = (x1 - x0) / SEKUND_NA_PASEK
    kand = []
    for k, (ya, yb) in enumerate(paski):
        xs, sig = profil(red, ya, yb, x0, x1)
        kand += [(k * SEKUND_NA_PASEK + (xs[i] - x0) / pxs, p) for i, p in maksima_z_wyniosloscia(sig)]

    prog = PROG_REL * float(np.median(sorted((p for _, p in kand), reverse=True)[:20]))
    przyj = []
    for t, p in sorted(kand, key=lambda z: -z[1]):               # zachłannie po wyniosłości
        if p < prog: break
        if all(abs(t - u) >= REFRAKCJA_S for u, _ in przyj): przyj.append((t, p))
    przyj.sort()
    t = np.array([u for u, _ in przyj]); amp = np.array([p for _, p in przyj]); rr = np.diff(t)
    czas = SEKUND_NA_PASEK * len(paski)
    wyn = dict(
        zrodlo=f"obraz rastrowy; ślad odtworzony z pikseli (~{pxs:.0f} px/s)",
        liczba_uderzen=len(t), zalamki_R_s=[round(float(u), 2) for u in t],
        niepewne_krawedziowe_s=[round(float(u), 2) for u in t if u < KRAWEDZ_S or u > czas - 0.3],
        hr_z_rr_bpm=round(60 / float(rr.mean()), 1),
        rr_s=dict(min=round(float(rr.min()), 2), max=round(float(rr.max()), 2), srednia=round(float(rr.mean()), 3),
                  sd=round(float(rr.std()), 3), cv_proc=round(float(rr.std() / rr.mean() * 100), 1)),
        amplituda_R_px_cv_proc=round(float(amp.std() / amp.mean() * 100), 1),
        prog_px=round(prog, 1), refrakcja_s=REFRAKCJA_S, rozdzielczosc_czasowa_ms=round(1000 / pxs, 1),
    )
    if arg.hr_raport:
        wyn["hr_raport_bpm"] = arg.hr_raport
        wyn["roznica_hr_bpm"] = round(wyn["hr_z_rr_bpm"] - arg.hr_raport, 1)
    json.dump(wyn, open(arg.wynik, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in wyn.items() if k != "zalamki_R_s"}, ensure_ascii=False, indent=1))

    if arg.kontrola:                                             # nakładka do oceny wzrokowej
        out = img.copy(); d = ImageDraw.Draw(out)
        for u in t:
            k = min(int(u // SEKUND_NA_PASEK), len(paski) - 1); ya, _ = paski[k]
            x = int(x0 + (u - SEKUND_NA_PASEK * k) * pxs)
            d.line([(x, ya - 34), (x, ya - 6)], fill=(0, 150, 0), width=3)
        for k, (ya, yb) in enumerate(paski):
            out.crop((0, ya - 60, out.width, yb + 30)).save(f"{arg.kontrola}_pasek{k+1}.png")


if __name__ == "__main__":
    main()
