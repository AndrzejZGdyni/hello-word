// MATERIAŁ EDUKACYJNY – nie jest oceną medyczną ani wytyczną kliniczną.
// Ocena jednokanałowego zapisu EKG (dane pochodne) przy użyciu Jev (TypeSafe System One).
// Użycie:
//   node ocena_ekg.mjs pomiar.przyklad.json --dry-run   # pokazuje zapytanie, bez wywołania API
//   TYPESAFE_API_KEY=... node ocena_ekg.mjs pomiar.przyklad.json
// W sesji Claude Code w chmurze klucz dokleja proxy (sekret sieciowy), więc:
//   TYPESAFE_API_KEY=placeholder NODE_USE_ENV_PROXY=1 node ocena_ekg.mjs pomiar.przyklad.json
import { readFileSync } from "node:fs";

const [, , plik = "pomiar.przyklad.json", ...flagi] = process.argv;
const dryRun = flagi.includes("--dry-run");
const pomiar = JSON.parse(readFileSync(plik, "utf8"));
const r2 = (x) => Math.round(x * 100) / 100;
const r3 = (x) => Math.round(x * 1000) / 1000;
const srednia = (a) => a.reduce((s, v) => s + v, 0) / a.length;

// --- 1. Wskaźniki liczone w kodzie ---
const t = pomiar.zalamki_R_s;
const rr = t.slice(1).map((v, i) => v - t[i]);
const sr = srednia(rr);
const sd = Math.sqrt(srednia(rr.map((v) => (v - sr) ** 2)));
const dRR = rr.slice(1).map((v, i) => v - rr[i]);
const rmssd = Math.sqrt(srednia(dRR.map((v) => v * v)));
const hrZRR = 60 / sr;
const hrNaglowek = pomiar.naglowek_raportu.tetno_bpm;
const roznicaHR = hrZRR - hrNaglowek;
const rozdz = pomiar.zapis.rozdzielczosc_czasowa_ms;

const wskazniki = {
  beats_detected: t.length,
  heart_rate_from_rr_bpm: r2(hrZRR),
  heart_rate_difference_vs_report_header_bpm: r2(roznicaHR),
  rr_s: { min: r2(Math.min(...rr)), max: r2(Math.max(...rr)), mean: r3(sr), sd: r3(sd), cv_percent: r2((sd / sr) * 100) },
  rmssd_s: r3(rmssd),
  max_successive_rr_difference_s: r2(Math.max(...dRR.map(Math.abs))),
  time_resolution_ms: rozdz,
  uncertain_edge_beats: pomiar.niepewne_krawedziowe_s.length,
  r_amplitude_cv_percent: pomiar.amplituda_R_cv_proc,
};
// orientacyjna kategoria tętna (reguła podręcznikowa, w kodzie – nie u Jeva)
const kategoriaTetna = hrZRR < 60 ? "poniżej 60/min" : hrZRR <= 100 ? "60–100/min" : "powyżej 100/min";

// --- 2. Stan przekazywany do Jev ---
const state = {
  note: "Educational exercise on a single-lead tracing reconstructed from an image; not a clinical assessment.",
  patient: { sex: pomiar.pacjent.plec, age: pomiar.pacjent.wiek, comment: "null = unknown; sex and age affect interval limits" },
  recording: {
    duration_s: pomiar.zapis.czas_s,
    leads: pomiar.zapis.liczba_odprowadzen,
    amplitude_scale: pomiar.zapis.skala_amplitudy,
    source: "R-wave times reconstructed from image pixels; intervals QRS/PR/QTc come from the report header (assumed ms)",
  },
  report_header: {
    heart_rate_bpm: hrNaglowek,
    qrs_ms: pomiar.naglowek_raportu.qrs_ms,
    pr_ms: pomiar.naglowek_raportu.pr_ms,
    qtc_ms: pomiar.naglowek_raportu.qtc_ms,
  },
  rr_intervals_s: rr.map(r2),
  computed_indicators: wskazniki,
};

const kontekst =
  "Use `rr_intervals_s` and `computed_indicators` for rhythm regularity and signal quality, and `report_header` " +
  "for the interval values. This is a single-lead tracing without amplitude calibration; sex and age are unknown. ";

// --- 3. Pytania (niezależne, wykonywane równolegle) ---
const questions = {
  rhythm_regularity: {
    type: "choice",
    instructions: kontekst + "How regular is the rhythm, judging only from the RR intervals?",
    criteria: {
      regular: "RR intervals very similar (low variability, no abrupt beat-to-beat changes).",
      slightly_irregular: "Moderate, smoothly varying RR intervals (e.g. gradual variation) without abrupt jumps.",
      markedly_irregular: "Large and abrupt beat-to-beat changes, irregularly irregular pattern, pauses or premature beats.",
      cannot_judge: "Too few beats or too unreliable detection to judge regularity.",
    },
  },
  intervals_assessment: {
    type: "choice",
    instructions:
      kontekst +
      "How do the report-header QRS, PR and QTc values and the heart rate compare with typical adult ranges? " +
      "Remember that limits for QTc depend on sex and age, which are unknown.",
    criteria: {
      all_typical: "All values lie comfortably within typical adult ranges for either sex.",
      borderline_present: "At least one value is near the boundary of the typical range or its interpretation depends on sex/age.",
      clearly_abnormal: "At least one value is clearly outside the typical adult range.",
      cannot_judge: "Insufficient information to compare the values.",
    },
  },
  signal_quality: {
    type: "score",
    instructions: kontekst + "How suitable is this recording for judging rhythm regularity?",
    criteria: [
      "0 – Unusable: detection unreliable, large inconsistencies with the report header.",
      "1 – Poor: many uncertain beats or strong inconsistencies.",
      "2 – Adequate for regularity, limited otherwise: few uncertain edge beats, heart rate consistent with the header, resolution about 10 ms.",
      "3 – Good: no uncertain beats and consistent values (not achievable from an image reconstruction).",
    ],
  },
  alt_detection_error_explains_pattern: {
    type: "noul",
    instructions:
      kontekst + "Could the RR pattern be mostly an artifact of detection errors (missed or false beats) rather than the underlying rhythm?",
  },
  review_priority: {
    type: "choice",
    instructions: kontekst + "In a teaching triage exercise, how should this tracing be queued for review by a clinician?",
    criteria: {
      no_review_needed: "Regular rhythm, typical intervals and good consistency; nothing to flag.",
      routine_review: "Mostly unremarkable, but borderline values or limits of the recording justify a routine look.",
      prompt_review: "Irregularity, clearly abnormal intervals or unreliable data call for a prompt look.",
      urgent_review: "Findings that would call for same-day attention.",
    },
  },
};

const request = { model: process.env.TYPESAFE_DEFAULT_MODEL ?? "jev-latest", state, questions };

if (dryRun) {
  console.log(JSON.stringify(request, null, 2));
  process.exit(0);
}

// --- 4. Wywołanie Jev ---
const { TypeSafeClient } = await import("@typesafe-ai/sdk");
const client = new TypeSafeClient();
const { model, answers, usage } = await client.systemOne(request);

// --- 5. Podsumowanie (próg pewności do kalibracji) ---
const niepewne = Object.entries(answers)
  .filter(([, v]) => (v.type === "noul" ? v.noul > 0.3 && v.noul < 0.7 : v.confidence < 0.6))
  .map(([k]) => k);

console.log("⚠ MATERIAŁ EDUKACYJNY – to nie jest ocena medyczna.");
console.log(`Model: ${model}`);
console.log(`Uderzenia: ${wskazniki.beats_detected}; tętno z RR ${wskazniki.heart_rate_from_rr_bpm}/min (nagłówek ${hrNaglowek}, różnica ${wskazniki.heart_rate_difference_vs_report_header_bpm}); kategoria orientacyjna: ${kategoriaTetna}`);
console.log(`RR: ${JSON.stringify(wskazniki.rr_s)}; RMSSD ${wskazniki.rmssd_s} s`);
const pokaz = (k, v) => `${k}: ${v.choice} (pewność ${r2(v.confidence)})`;
console.log(pokaz("Regularność rytmu", answers.rhythm_regularity), answers.rhythm_regularity.probabilities);
console.log(pokaz("Odstępy QRS/PR/QTc", answers.intervals_assessment), answers.intervals_assessment.probabilities);
console.log(`Jakość zapisu: ${r2(answers.signal_quality.score)} / 3 – ${answers.signal_quality.legend[Math.round(answers.signal_quality.score)]}`);
console.log(`Błąd detekcji tłumaczy wzorzec: p = ${r2(answers.alt_detection_error_explains_pattern.noul)}`);
console.log(pokaz("Kolejka przeglądu", answers.review_priority), answers.review_priority.probabilities);
console.log(niepewne.length ? `➜ Niepewne odpowiedzi: ${niepewne.join(", ")}.` : "➜ Odpowiedzi o wysokiej pewności (to nadal nie jest ocena medyczna).");
console.log(`Tokeny: we ${usage.input_tokens}, wy ${usage.output_tokens}`);
