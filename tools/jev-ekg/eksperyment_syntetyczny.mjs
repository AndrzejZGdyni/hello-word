// MATERIAŁ EDUKACYJNY – eksperyment na danych SYNTETYCZNYCH, bez danych osobowych.
// Pytanie badawcze: czy opis kryteriów z progami liczbowymi poprawia ocenę regularności rytmu przez Jev
// w porównaniu z opisem słownym, i jak wypada prosta reguła w kodzie?
//
// Serie RR są generowane z zadaną klasą (prawda "z konstrukcji"):
//   regular             – stały rytm z niewielkim szumem
//   slightly_irregular  – łagodna, gładka zmienność (jak arytmia oddechowa)
//   markedly_irregular  – nagłe zmiany: "ectopic" (przedwczesne uderzenia z przerwą) lub "random" (losowe RR)
//
// Użycie:
//   node eksperyment_syntetyczny.mjs --dry-run [--seed 42]     # tylko generowanie + reguła w kodzie
//   TYPESAFE_API_KEY=... node eksperyment_syntetyczny.mjs [--seed 42]
// W sesji Claude Code w chmurze klucz dokleja proxy:
//   TYPESAFE_API_KEY=placeholder NODE_USE_ENV_PROXY=1 node eksperyment_syntetyczny.mjs
import { writeFileSync } from "node:fs";

const arg = process.argv.slice(2);
const dryRun = arg.includes("--dry-run");
const seed = Number(arg[arg.indexOf("--seed") + 1]) || 42;
const WSPOLBIEZNOSC = 4;

// --- Generator pseudolosowy (powtarzalny) ---
function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(seed);
const gauss = () => Math.sqrt(-2 * Math.log(rnd() || 1e-9)) * Math.cos(2 * Math.PI * rnd());
const r2 = (x) => Math.round(x * 100) / 100;
const r3 = (x) => Math.round(x * 1000) / 1000;
const srednia = (a) => a.reduce((s, v) => s + v, 0) / a.length;

// --- Generowanie serii ---
const BAZY = [0.67, 0.8, 1.0, 1.2]; // ok. 90, 75, 60, 50/min
function generuj(typ) {
  const base = BAZY[Math.floor(rnd() * BAZY.length)];
  const n = Math.floor(30 / base) + 2;
  let rr = [];
  if (typ === "regular") {
    for (let i = 0; i < n; i++) rr.push(base * (1 + 0.02 * gauss()));
  } else if (typ === "slightly_irregular") {
    const a = 0.05 + 0.04 * rnd(), per = 4 + 2 * rnd(), ph = rnd() * 2 * Math.PI;
    for (let i = 0; i < n; i++) rr.push(base * (1 + a * Math.sin((2 * Math.PI * i) / per + ph) + 0.01 * gauss()));
  } else if (typ === "ectopic") {
    for (let i = 0; i < n; i++) rr.push(base * (1 + 0.015 * gauss()));
    const zdarzen = 2 + Math.floor(rnd() * 2);
    let p = 2 + Math.floor(rnd() * 3);
    for (let z = 0; z < zdarzen && p < n - 3; z++, p += 5 + Math.floor(rnd() * 5)) {
      rr[p] = base * 0.6 * (1 + 0.02 * gauss()); // przedwczesne uderzenie
      rr[p + 1] = base * 1.4 * (1 + 0.02 * gauss()); // przerwa wyrównawcza
    }
  } else if (typ === "random") {
    for (let i = 0; i < n; i++) rr.push(base * (0.6 + 0.9 * rnd()));
  }
  // szum detekcji i rozdzielczość 10 ms; obcięcie do ok. 30 s
  rr = rr.map((v) => Math.round((v + 0.005 * gauss()) * 100) / 100);
  const wynik = []; let t = 0.5;
  for (const v of rr) { t += v; if (t > 29.8) break; wynik.push(v); }
  return { base, rr: wynik };
}

// --- Wskaźniki (jak w ocena_ekg.mjs) ---
function wskazniki(rr) {
  const sr = srednia(rr);
  const sd = Math.sqrt(srednia(rr.map((v) => (v - sr) ** 2)));
  const d = rr.slice(1).map((v, i) => v - rr[i]);
  return {
    beats_detected: rr.length + 1,
    heart_rate_from_rr_bpm: r2(60 / sr),
    rr_s: { min: r2(Math.min(...rr)), max: r2(Math.max(...rr)), mean: r3(sr), sd: r3(sd), cv_percent: r2((sd / sr) * 100) },
    rmssd_s: r3(Math.sqrt(srednia(d.map((v) => v * v)))),
    max_successive_rr_difference_s: r2(Math.max(...d.map(Math.abs))),
  };
}

// --- Reguła w kodzie (te same progi liczbowe, co w wariancie "numeric") ---
function regula(w) {
  const cv = w.rr_s.cv_percent, md = w.max_successive_rr_difference_s;
  if (cv > 10 || md >= 0.2) return "markedly_irregular";
  if (cv >= 3 || md >= 0.1) return "slightly_irregular";
  return "regular";
}

// --- Zbiór przypadków ---
const PLAN = [["regular", "regular", 8], ["slightly_irregular", "slightly_irregular", 8], ["ectopic", "markedly_irregular", 6], ["random", "markedly_irregular", 6]];
const przypadki = [];
for (const [typ, prawda, n] of PLAN)
  for (let i = 0; i < n; i++) {
    const { base, rr } = generuj(typ);
    przypadki.push({ id: `${typ}_${i + 1}`, podtyp: typ, prawda, base, rr, w: wskazniki(rr) });
  }

// --- Pytania: ta sama treść, różny opis kryteriów ---
const kontekst = "Use `rr_intervals_s` and `computed_indicators`. ";
const instr = kontekst + "How regular is the rhythm, judging only from the RR intervals?";
const questions = {
  regularity_verbal: {
    type: "choice",
    instructions: instr,
    criteria: {
      regular: "RR intervals very similar (low variability, no abrupt beat-to-beat changes).",
      slightly_irregular: "Moderate, smoothly varying RR intervals (e.g. gradual variation) without abrupt jumps.",
      markedly_irregular: "Large and abrupt beat-to-beat changes, irregularly irregular pattern, pauses or premature beats.",
      cannot_judge: "Too few beats or too unreliable detection to judge regularity.",
    },
  },
  regularity_numeric: {
    type: "choice",
    instructions: instr,
    criteria: {
      regular: "RR coefficient of variation below about 3% and maximum successive RR difference below about 0.10 s.",
      slightly_irregular: "RR coefficient of variation about 3–10% with smooth variation; maximum successive RR difference below about 0.20 s.",
      markedly_irregular: "RR coefficient of variation above about 10%, or any successive RR difference of about 0.20 s or more (abrupt changes, premature beats, pauses).",
      cannot_judge: "Too few beats or too unreliable detection to judge regularity.",
    },
  },
};
const stanDla = (p) => ({
  note: "Teaching experiment: RR intervals from a single-lead tracing; no clinical context.",
  recording: { duration_s: 30, leads: 1, time_resolution_ms: 10 },
  rr_intervals_s: p.rr,
  computed_indicators: p.w,
});

const KLASY = ["regular", "slightly_irregular", "markedly_irregular", "cannot_judge"];
const dokladnosc = (pred) => pred.filter((x) => x.pred === x.prawda).length / pred.length;
function macierz(pred) {
  const m = Object.fromEntries(["regular", "slightly_irregular", "markedly_irregular"].map((k) => [k, Object.fromEntries(KLASY.map((c) => [c, 0]))]));
  for (const x of pred) m[x.prawda][x.pred]++;
  return m;
}
function raport(nazwa, pred) {
  console.log(`\n=== ${nazwa} ===`);
  console.log(`Dokładność ogółem: ${(dokladnosc(pred) * 100).toFixed(0)}% (${pred.filter((x) => x.pred === x.prawda).length}/${pred.length})`);
  for (const pt of ["regular", "slightly_irregular", "ectopic", "random"]) {
    const g = pred.filter((x) => x.podtyp === pt);
    console.log(`  ${pt.padEnd(19)} ${g.filter((x) => x.pred === x.prawda).length}/${g.length}`);
  }
  console.log("Macierz pomyłek (wiersz = prawda, kolumny = ocena):");
  console.log("  " + "".padEnd(20) + KLASY.map((k) => k.slice(0, 10).padStart(11)).join(""));
  for (const [k, w] of Object.entries(macierz(pred))) console.log("  " + k.padEnd(20) + KLASY.map((c) => String(w[c]).padStart(11)).join(""));
}

console.log(`Eksperyment syntetyczny: seed ${seed}, ${przypadki.length} serii RR.`);
const baseline = przypadki.map((p) => ({ podtyp: p.podtyp, prawda: p.prawda, pred: regula(p.w) }));
raport("Reguła w kodzie (progi liczbowe)", baseline);

if (dryRun) {
  console.log("\n(--dry-run) Przykładowe żądanie dla pierwszej serii:");
  console.log(JSON.stringify({ model: "jev-latest", state: stanDla(przypadki[0]), questions }, null, 1).slice(0, 1500) + "\n...");
  process.exit(0);
}

// --- Wywołania Jev ---
const { TypeSafeClient } = await import("@typesafe-ai/sdk");
const client = new TypeSafeClient();
let tokWe = 0, tokWy = 0, bledy = 0;
async function pool(items, n, fn) {
  const out = []; let i = 0;
  await Promise.all(Array.from({ length: n }, async () => { while (i < items.length) { const k = i++; out[k] = await fn(items[k]); } }));
  return out;
}
const odp = await pool(przypadki, WSPOLBIEZNOSC, async (p) => {
  try {
    const r = await client.systemOne({ state: stanDla(p), questions });
    tokWe += r.usage.input_tokens; tokWy += r.usage.output_tokens;
    return r.answers;
  } catch (e) { bledy++; return null; }
});

const wyniki = {};
for (const wariant of ["regularity_verbal", "regularity_numeric"]) {
  const pred = przypadki.map((p, i) => {
    const a = odp[i]?.[wariant];
    return { id: p.id, podtyp: p.podtyp, prawda: p.prawda, pred: a?.choice ?? "cannot_judge", conf: a?.confidence ?? 0, probs: a?.probabilities ?? null };
  });
  wyniki[wariant] = pred;
  raport(`Jev – kryteria ${wariant === "regularity_verbal" ? "SŁOWNE" : "LICZBOWE"}`, pred);
  const sr = (g) => (g.length ? (srednia(g.map((x) => x.conf))).toFixed(2) : "–");
  const ok = pred.filter((x) => x.pred === x.prawda), zle = pred.filter((x) => x.pred !== x.prawda);
  console.log(`Średnia pewność: poprawne ${sr(ok)} (n=${ok.length}), błędne ${sr(zle)} (n=${zle.length})`);
  for (const [nazwa, f] of [["pewność ≥0,9", (x) => x.conf >= 0.9], ["0,6–0,9", (x) => x.conf >= 0.6 && x.conf < 0.9], ["<0,6", (x) => x.conf < 0.6]]) {
    const g = pred.filter(f);
    console.log(`  ${nazwa.padEnd(14)} n=${String(g.length).padStart(2)}  trafność ${g.length ? ((g.filter((x) => x.pred === x.prawda).length / g.length) * 100).toFixed(0) + "%" : "–"}`);
  }
}
console.log(`\nZgodność odpowiedzi obu wariantów: ${przypadki.filter((_, i) => wyniki.regularity_verbal[i].pred === wyniki.regularity_numeric[i].pred).length}/${przypadki.length}`);
console.log(`Tokeny: we ${tokWe}, wy ${tokWy}; błędy wywołań: ${bledy}`);
writeFileSync("eksperyment_synt_wyniki.json", JSON.stringify({ seed, baseline, ...wyniki, przypadki: przypadki.map(({ id, podtyp, prawda, rr }) => ({ id, podtyp, prawda, rr })) }, null, 1));
console.log("Zapisano: eksperyment_synt_wyniki.json (dane syntetyczne)");
