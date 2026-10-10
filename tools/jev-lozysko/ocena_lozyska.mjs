// Ocena stanu łożyska tocznego z widma obwiedni przy użyciu Jev (TypeSafe System One).
// Użycie:
//   node ocena_lozyska.mjs pomiar.json --dry-run   # pokazuje zapytanie, bez wywołania API
//   TYPESAFE_API_KEY=... node ocena_lozyska.mjs pomiar.json
// W sesji Claude Code w chmurze klucz dokleja proxy (sekret sieciowy), więc:
//   TYPESAFE_API_KEY=placeholder NODE_USE_ENV_PROXY=1 node ocena_lozyska.mjs pomiar.json
import { readFileSync } from "node:fs";

const [, , plik = "pomiar.json", ...flagi] = process.argv;
const dryRun = flagi.includes("--dry-run");
const pomiar = JSON.parse(readFileSync(plik, "utf8"));
const r2 = (x) => Math.round(x * 100) / 100;

// --- 1. Częstotliwości charakterystyczne łożyska (wzory kinematyczne) ---
const { liczba_elementow_tocznych: n, srednica_elementu_mm: d, srednica_podzialowa_mm: D, kat_dzialania_deg } =
  pomiar.lozysko;
const fr = pomiar.maszyna.obroty_rpm / 60;
const ratio = (d / D) * Math.cos((kat_dzialania_deg * Math.PI) / 180);
const czestotliwosci = {
  running_speed_1x: fr,
  BPFO_outer_race: (n / 2) * fr * (1 - ratio),
  BPFI_inner_race: (n / 2) * fr * (1 + ratio),
  BSF_rolling_element: (D / (2 * d)) * fr * (1 - ratio ** 2),
  FTF_cage: (fr / 2) * (1 - ratio),
};

// --- 2. Dopasowanie prążków obwiedni do harmonicznych i wstęg bocznych ---
const TOL = 0.02; // ±2 % tolerancji (poślizg, dokładność obrotów)
const prazki = pomiar.obwiednia.prazki;
const znajdz = (f) => prazki.find((p) => Math.abs(p.f - f) <= f * TOL);

const dopasowanie = {};
for (const [nazwa, f0] of Object.entries(czestotliwosci)) {
  if (nazwa === "running_speed_1x") continue;
  const harmoniczne = [];
  for (let k = 1; k <= 6; k++) {
    const p = znajdz(k * f0);
    if (p) harmoniczne.push({ order: k, f: p.f, amp_gE: p.amp });
  }
  // wstęgi boczne 1x (typowe dla bieżni wewnętrznej) i FTF (typowe dla elementów tocznych)
  const wstegi = { "±1x": 0, "±FTF": 0 };
  for (const h of harmoniczne) {
    for (const s of [-1, 1]) {
      if (znajdz(h.f + s * fr)) wstegi["±1x"]++;
      if (znajdz(h.f + s * czestotliwosci.FTF_cage)) wstegi["±FTF"]++;
    }
  }
  dopasowanie[nazwa] = {
    expected_Hz: r2(f0),
    harmonics_found: harmoniczne,
    harmonics_count: harmoniczne.length,
    sideband_matches: wstegi,
  };
}
const niedopasowane = prazki.filter(
  (p) =>
    !Object.values(dopasowanie).some((m) => m.harmonics_found.some((h) => h.f === p.f)) &&
    !Array.from({ length: 6 }, (_, k) => (k + 1) * fr).some((f) => Math.abs(p.f - f) <= f * TOL),
);

// --- 3. Stan przekazywany do Jev ---
const state = {
  machine: pomiar.maszyna,
  bearing: pomiar.lozysko,
  units: "envelope spectrum amplitudes in gE; acceleration in g; frequencies in Hz",
  characteristic_frequencies_Hz: Object.fromEntries(Object.entries(czestotliwosci).map(([k, v]) => [k, r2(v)])),
  envelope_filter_band_Hz: pomiar.obwiednia.pasmo_filtra_Hz,
  envelope_peak_matches: dopasowanie,
  unmatched_envelope_peaks: niedopasowane,
  time_domain_indicators: pomiar.wskazniki_czasowe,
  technician_notes: pomiar.obserwacje ?? null,
};

const kontekst =
  "Use the matched envelope-spectrum peaks in `envelope_peak_matches` (harmonics of the bearing " +
  "defect frequencies and their sidebands), `unmatched_envelope_peaks`, the indicators in " +
  "`time_domain_indicators` and `technician_notes`. ";

// --- 4. Pytania (niezależne, wykonywane równolegle) ---
const questions = {
  fault_location: {
    type: "choice",
    instructions: kontekst + "Which rolling bearing defect best explains the envelope spectrum?",
    criteria: {
      outer_race: "Series of BPFO harmonics, typically without 1x sidebands (stationary outer ring).",
      inner_race: "BPFI harmonics modulated by 1x sidebands (rotating inner ring passes the load zone).",
      rolling_element: "BSF (often 2xBSF) harmonics with FTF sidebands.",
      cage: "FTF and its harmonics, possibly modulating other defect frequencies.",
      none: "No bearing defect frequencies are present; the spectrum is not explained by a bearing defect.",
    },
  },
  damage_stage: {
    type: "score",
    instructions: kontekst + "What stage of rolling bearing damage does the evidence indicate?",
    criteria: [
      "Stage 0 – healthy: no defect frequencies, low envelope level, kurtosis near 3.",
      "Stage 1 – incipient: ultrasonic / high-frequency activity only, defect frequencies barely visible.",
      "Stage 2 – developing: clear defect frequency with a few harmonics in the envelope, rising trend.",
      "Stage 3 – advanced: many harmonics and sidebands, high envelope level, defect frequencies may appear in velocity spectrum.",
      "Stage 4 – near failure: broadband noise floor rise, harmonics smear, 1x rises; failure imminent.",
    ],
  },
  lubrication_problem: {
    type: "noul",
    instructions: kontekst +
      "Is a lubrication problem (insufficient or degraded grease) a more likely explanation than a localized defect? " +
      "Lubrication issues raise broadband high-frequency levels without discrete defect-frequency harmonics.",
  },
  action: {
    type: "choice",
    instructions: kontekst + "What maintenance action is most appropriate now?",
    criteria: {
      continue_monitoring: "No defect or only incipient signs; keep the normal measurement interval.",
      shorten_interval: "Developing defect; shorten the measurement interval and plan replacement.",
      plan_replacement: "Clear, progressing defect; schedule bearing replacement at the next planned stop.",
      replace_urgently: "Advanced damage or near failure; replace as soon as possible.",
    },
  },
};

const request = { model: process.env.TYPESAFE_DEFAULT_MODEL ?? "jev-latest", state, questions };

if (dryRun) {
  console.log(JSON.stringify(request, null, 2));
  process.exit(0);
}

// --- 5. Wywołanie Jev ---
const { TypeSafeClient } = await import("@typesafe-ai/sdk");
const client = new TypeSafeClient();
const { model, answers, usage } = await client.systemOne(request);

// --- 6. Polityka decyzji (progi do kalibracji na własnych przypadkach) ---
const loc = answers.fault_location;
const stage = answers.damage_stage;
const act = answers.action;
const doDiagnosty = loc.confidence < 0.6 || act.confidence < 0.6 || answers.lubrication_problem.noul >= 0.5;

console.log(`Model: ${model}`);
console.log("Częstotliwości [Hz]:", JSON.stringify(state.characteristic_frequencies_Hz));
for (const [k, m] of Object.entries(dopasowanie))
  console.log(`  ${k}: ${m.harmonics_count} harm., wstęgi ${JSON.stringify(m.sideband_matches)}`);
console.log(`Lokalizacja uszkodzenia: ${loc.choice} (pewność ${r2(loc.confidence)})`, loc.probabilities);
console.log(`Stadium: ${r2(stage.score)} / 4 – ${stage.legend[Math.round(stage.score)]}`);
console.log(`Problem ze smarowaniem: p = ${r2(answers.lubrication_problem.noul)}`);
console.log(`Zalecenie: ${act.choice} (pewność ${r2(act.confidence)})`, act.probabilities);
console.log(doDiagnosty ? "➜ Do weryfikacji przez diagnostę." : "➜ Wynik jednoznaczny.");
console.log(`Tokeny: we ${usage.input_tokens}, wy ${usage.output_tokens}`);
