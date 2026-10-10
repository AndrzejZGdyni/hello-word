// Ocena niewspółosiowości (centrówki) z widma drgań przy użyciu Jev (TypeSafe System One).
// Użycie:
//   node ocena_centrowki.mjs pomiar.json --dry-run   # pokazuje zapytanie, bez wywołania API
//   TYPESAFE_API_KEY=... node ocena_centrowki.mjs pomiar.json
// W sesji Claude Code w chmurze klucz dokleja proxy (sekret sieciowy), więc:
//   TYPESAFE_API_KEY=placeholder NODE_USE_ENV_PROXY=1 node ocena_centrowki.mjs pomiar.json
import { readFileSync } from "node:fs";

const [, , plik = "pomiar.json", ...flagi] = process.argv;
const dryRun = flagi.includes("--dry-run");
const pomiar = JSON.parse(readFileSync(plik, "utf8"));

// --- 1. Wskaźniki liczone w kodzie (deterministyczne, bez modelu) ---
const r2 = (x) => Math.round(x * 100) / 100;
const roznicaFaz = (a, b) => {
  const d = Math.abs(a - b) % 360;
  return d > 180 ? 360 - d : d;
};

const wskazniki = {};
for (const [nazwa, l] of Object.entries(pomiar.lozyska)) {
  const rad1x = Math.max(l.H["1x"], l.V["1x"]);
  const rad2x = Math.max(l.H["2x"], l.V["2x"]);
  wskazniki[nazwa] = {
    ratio_2x_to_1x_radial: r2(rad2x / rad1x),
    ratio_2x_to_1x_axial: r2(l.A["2x"] / l.A["1x"]),
    ratio_axial_to_radial_1x: r2(l.A["1x"] / rad1x),
    ratio_3x_to_1x_radial: r2(Math.max(l.H["3x"], l.V["3x"]) / rad1x),
  };
}
const [a, b] = Object.values(pomiar.lozyska);
const fazaPrzezSprzeglo =
  a.phase_1x && b.phase_1x
    ? {
        phase_diff_1x_radial_H_deg: roznicaFaz(a.phase_1x.H, b.phase_1x.H),
        phase_diff_1x_axial_deg: roznicaFaz(a.phase_1x.A, b.phase_1x.A),
      }
    : null;

// --- 2. Stan przekazywany do Jev ---
const state = {
  machine: pomiar.maszyna,
  measurement_units: "vibration velocity mm/s RMS; phase in degrees",
  bearings_on_both_sides_of_coupling: pomiar.lozyska,
  computed_indicators: wskazniki,
  phase_across_coupling: fazaPrzezSprzeglo,
  technician_notes: pomiar.obserwacje ?? null,
};

const kontekst =
  "Use the vibration spectra in `bearings_on_both_sides_of_coupling` (1x, 2x, 3x running-speed " +
  "harmonics in H, V and A directions), the ratios in `computed_indicators` and the phase " +
  "differences in `phase_across_coupling`. ";

// --- 3. Pytania (niezależne, wykonywane równolegle) ---
const questions = {
  misalignment: {
    type: "noul",
    instructions:
      kontekst +
      "Does the vibration pattern indicate shaft misalignment across the coupling?",
    criteria: {
      true: "Pattern consistent with misalignment: elevated 2x relative to 1x, significant axial " +
        "vibration, and/or approx. 180 deg phase shift across the coupling.",
      false: "Pattern not consistent with misalignment, or explained better by another fault.",
    },
  },
  misalignment_type: {
    type: "choice",
    instructions: kontekst + "Which type of misalignment best matches the pattern?",
    criteria: {
      angular: "Dominant axial 1x (often with 2x), approx. 180 deg axial phase across the coupling.",
      parallel: "Dominant radial 2x, often exceeding 1x, approx. 180 deg radial phase across the coupling.",
      combined: "Both elevated axial and radial components with 1x and 2x; mixed phase evidence.",
      none: "No misalignment pattern is present.",
    },
  },
  alt_unbalance: {
    type: "noul",
    instructions: kontekst +
      "Is unbalance a more likely explanation than misalignment (dominant radial 1x, low axial, low 2x)?",
  },
  alt_bent_shaft: {
    type: "noul",
    instructions: kontekst +
      "Is a bent shaft a plausible alternative explanation (high axial 1x, phase shift along the same shaft)?",
  },
  alt_looseness: {
    type: "noul",
    instructions: kontekst +
      "Is mechanical looseness a plausible alternative explanation (long series of harmonics, possible 0.5x)?",
  },
  check_soft_foot: {
    type: "noul",
    instructions: kontekst +
      "Should soft foot be checked before re-alignment, given the data and technician notes?",
  },
  severity: {
    type: "score",
    instructions: kontekst +
      "How strongly does the evidence indicate that the machine needs re-alignment?",
    criteria: [
      "No action: no misalignment signs.",
      "Monitor: weak signs, 2x clearly below 1x, axial vibration low.",
      "Plan re-alignment: 2x comparable to or above 1x, or clearly elevated axial vibration.",
      "Urgent: strong 2x/3x harmonics with high axial and radial levels on both coupling sides.",
    ],
  },
};

const request = { model: process.env.TYPESAFE_DEFAULT_MODEL ?? "jev-latest", state, questions };

if (dryRun) {
  console.log(JSON.stringify(request, null, 2));
  process.exit(0);
}

// --- 4. Wywołanie Jev ---
const { TypeSafeClient } = await import("@typesafe-ai/sdk");
const client = new TypeSafeClient(); // klucz z TYPESAFE_API_KEY
const { answers, usage } = await client.systemOne(request);

// --- 5. Polityka decyzji (progi do kalibracji na własnych przypadkach) ---
const p = answers.misalignment.noul;
const typ = answers.misalignment_type;
const alternatywy = Object.entries(answers)
  .filter(([k]) => k.startsWith("alt_"))
  .filter(([, v]) => v.noul >= 0.5)
  .map(([k, v]) => `${k.replace("alt_", "")} (${r2(v.noul)})`);

const doDiagnosty = (p > 0.3 && p < 0.7) || typ.confidence < 0.6 || alternatywy.length > 0;

console.log("Wskaźniki:", JSON.stringify(wskazniki), JSON.stringify(fazaPrzezSprzeglo));
console.log(`Niewspółosiowość: p = ${r2(p)}`);
console.log(`Rodzaj: ${typ.choice} (pewność ${r2(typ.confidence)})`, typ.probabilities);
console.log(`Pilność: ${r2(answers.severity.score)} / 3 – ${answers.severity.legend[Math.round(answers.severity.score)]}`);
console.log(`Alternatywne przyczyny ≥ 0.5: ${alternatywy.join(", ") || "brak"}`);
console.log(`Sprawdzić miękką stopę przed centrowaniem: ${answers.check_soft_foot.noul >= 0.5 ? "tak" : "nie"} (${r2(answers.check_soft_foot.noul)})`);
console.log(doDiagnosty ? "➜ Do weryfikacji przez diagnostę." : "➜ Wynik jednoznaczny.");
console.log(`Tokeny: we ${usage.input_tokens}, wy ${usage.output_tokens}`);
