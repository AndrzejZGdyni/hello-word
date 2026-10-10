// Ocena niewyważenia wirnika z widma drgań przy użyciu Jev (TypeSafe System One).
// Użycie:
//   node ocena_niewywazenia.mjs pomiar.json --dry-run   # pokazuje zapytanie, bez wywołania API
//   TYPESAFE_API_KEY=... node ocena_niewywazenia.mjs pomiar.json
// W sesji Claude Code w chmurze klucz dokleja proxy (sekret sieciowy), więc:
//   TYPESAFE_API_KEY=placeholder NODE_USE_ENV_PROXY=1 node ocena_niewywazenia.mjs pomiar.json
import { readFileSync } from "node:fs";

const [, , plik = "pomiar.json", ...flagi] = process.argv;
const dryRun = flagi.includes("--dry-run");
const pomiar = JSON.parse(readFileSync(plik, "utf8"));
const r2 = (x) => Math.round(x * 100) / 100;
const roznicaFaz = (a, b) => {
  const d = Math.abs(a - b) % 360;
  return d > 180 ? 360 - d : d;
};

// --- 1. Strefa ISO 20816-3 (granice A/B, B/C, C/D w mm/s RMS; zweryfikuj z normą) ---
const GRANICE = {
  1: { sztywny: [2.3, 4.5, 7.1], podatny: [3.5, 7.1, 11.0] },
  2: { sztywny: [1.4, 2.8, 4.5], podatny: [2.3, 4.5, 7.1] },
};
const { grupa_ISO_20816_3: grupa, fundament } = pomiar.maszyna;
const granice = GRANICE[grupa][fundament];
const maxOverall = Math.max(
  ...Object.values(pomiar.lozyska).flatMap((l) => ["H", "V", "A"].map((k) => l[k].overall)),
);
const strefa = ["A", "B", "C", "D"][granice.filter((g) => maxOverall > g).length];

// --- 2. Wskaźniki niewyważenia liczone w kodzie ---
const wskazniki = {};
for (const [nazwa, l] of Object.entries(pomiar.lozyska)) {
  const rad1x = Math.max(l.H["1x"], l.V["1x"]);
  wskazniki[nazwa] = {
    share_1x_of_overall_H: r2(l.H["1x"] / l.H.overall),
    ratio_H_to_V_1x: r2(l.H["1x"] / l.V["1x"]),
    ratio_axial_to_radial_1x: r2(l.A["1x"] / rad1x),
    ratio_2x_to_1x_radial: r2(Math.max(l.H["2x"], l.V["2x"]) / rad1x),
    phase_diff_H_V_1x_deg: roznicaFaz(l.phase_1x.H, l.phase_1x.V),
  };
}
const [de, nde] = Object.values(pomiar.lozyska);
const fazaMiedzyLozyskami = {
  phase_diff_DE_NDE_horizontal_1x_deg: roznicaFaz(de.phase_1x.H, nde.phase_1x.H),
  phase_diff_DE_NDE_vertical_1x_deg: roznicaFaz(de.phase_1x.V, nde.phase_1x.V),
};

// --- 2a. Rozkład wektorów 1x na składową statyczną S i parową C ---
// S = (A_DE + A_NDE) / 2, C = (A_DE − A_NDE) / 2; |C|/|S| < PROG_PAROWEJ → wystarczy 1 płaszczyzna.
const PROG_PAROWEJ = 0.2; // reguła praktyczna, nie wartość normowa – do kalibracji
const PROG_SPOJNOSCI_DEG = 30; // max różnica Δφ(DE–NDE) między kierunkami H i V
const wektor = (amp, fazaDeg) => {
  const rad = (fazaDeg * Math.PI) / 180;
  return [amp * Math.cos(rad), amp * Math.sin(rad)];
};
const modul = ([x, y]) => Math.hypot(x, y);
const rozkladSC = {};
for (const kier of ["H", "V"]) {
  const a = wektor(de[kier]["1x"], de.phase_1x[kier]);
  const b = wektor(nde[kier]["1x"], nde.phase_1x[kier]);
  const S = modul([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]);
  const C = modul([(a[0] - b[0]) / 2, (a[1] - b[1]) / 2]);
  rozkladSC[kier] = { static_S_mm_s: r2(S), couple_C_mm_s: r2(C), ratio_C_to_S: r2(C / S) };
}
const roznicaKierunkow = Math.abs(
  fazaMiedzyLozyskami.phase_diff_DE_NDE_horizontal_1x_deg - fazaMiedzyLozyskami.phase_diff_DE_NDE_vertical_1x_deg,
);
const maxCdoS = Math.max(rozkladSC.H.ratio_C_to_S, rozkladSC.V.ratio_C_to_S);
const maxC = Math.max(rozkladSC.H.couple_C_mm_s, rozkladSC.V.couple_C_mm_s);
const dekompozycja = {
  by_direction: rozkladSC,
  phase_consistency_H_vs_V_deg: roznicaKierunkow,
  phase_consistent: roznicaKierunkow <= PROG_SPOJNOSCI_DEG,
  max_ratio_C_to_S: maxCdoS,
  couple_threshold: PROG_PAROWEJ,
  // po idealnej korekcie w 1 płaszczyźnie zostaje ok. |C| na łożyskach
  est_residual_after_single_plane_mm_s: maxC,
  est_residual_zone: ["A", "B", "C", "D"][granice.filter((g) => maxC > g).length],
  planes_by_rule: maxCdoS < PROG_PAROWEJ ? 1 : 2,
};

// --- 3. Stan przekazywany do Jev ---
const state = {
  machine: pomiar.maszyna,
  units: "vibration velocity mm/s RMS; phase in degrees",
  bearings: pomiar.lozyska,
  computed_indicators: wskazniki,
  phase_between_bearings: fazaMiedzyLozyskami,
  static_couple_decomposition: dekompozycja,
  iso_20816_3: { zone: strefa, max_overall_mm_s: maxOverall, zone_limits_AB_BC_CD: granice },
  technician_notes: pomiar.obserwacje ?? null,
};

const kontekst =
  "Use the 1x, 2x, 3x spectra in `bearings`, the ratios and H–V phase difference in " +
  "`computed_indicators`, the phase between bearings in `phase_between_bearings`, " +
  "the static/couple vector decomposition in `static_couple_decomposition` (S = (A_DE + A_NDE)/2, " +
  "C = (A_DE − A_NDE)/2; ratio C/S below the couple threshold means the couple component is negligible), " +
  "the ISO 20816-3 zone and `technician_notes`. ";

// --- 4. Pytania (niezależne, wykonywane równolegle) ---
const questions = {
  unbalance: {
    type: "noul",
    instructions: kontekst + "Does the vibration pattern indicate rotor unbalance?",
    criteria: {
      true: "Dominant radial 1x (most of overall), low harmonics, low axial, H–V phase difference near 90 deg, H/V ratio roughly 1–3.",
      false: "Pattern not consistent with unbalance or better explained by another fault.",
    },
  },
  unbalance_type: {
    type: "choice",
    instructions: kontekst + "Which type of unbalance best matches the phase relationship between the bearings?",
    criteria: {
      static: "Bearings vibrate in phase (DE–NDE phase difference near 0 deg); couple component C small relative to static S (C/S below threshold).",
      couple: "Bearings vibrate in antiphase (DE–NDE phase difference near 180 deg); static component S small relative to couple C.",
      dynamic: "Combination of static and couple: DE–NDE phase difference clearly between 0 and 180 deg; both S and C significant (C/S above threshold).",
      overhung: "Overhung rotor: high axial 1x in phase at both bearings, radial phase pattern irregular.",
      none: "No unbalance is present.",
    },
  },
  alt_misalignment: {
    type: "noul",
    instructions: kontekst + "Is misalignment a more likely explanation (high 2x relative to 1x, high axial, ~180 deg across the coupling)?",
  },
  alt_looseness_or_weakness: {
    type: "noul",
    instructions: kontekst +
      "Is mechanical looseness or structural weakness more likely (very high H/V ratio above ~3, H–V phase near 0 or 180 deg, many harmonics)?",
  },
  alt_resonance: {
    type: "noul",
    instructions: kontekst +
      "Is a structural resonance near running speed a plausible amplifier (strongly directional 1x, unstable phase, very high H/V ratio)?",
  },
  balancing_planes: {
    type: "choice",
    instructions: kontekst +
      "If the rotor is balanced, how many correction planes are needed? Judge from the static/couple decomposition, " +
      "its H/V phase consistency and the expected residual vibration after single-plane correction.",
    criteria: {
      one_plane: "Couple component negligible (C/S below threshold in both directions, phases consistent); single-plane correction leaves acceptable residual vibration.",
      two_planes: "Couple component significant (C/S above threshold) or single-plane correction would leave residual vibration above the target zone.",
      not_applicable: "Unbalance is not the problem, or phase data are inconsistent and cannot support a balancing decision.",
    },
  },
  action: {
    type: "choice",
    instructions: kontekst + "What is the most appropriate next action?",
    criteria: {
      no_action: "Vibration acceptable (zone A/B) and no progressing trend.",
      clean_rotor_then_check: "Gradual rise with likely material build-up or wear on the rotor; clean first, then re-measure before balancing.",
      balance_single_plane: "Static unbalance on a narrow rotor; balance in one plane.",
      balance_two_planes: "Dynamic or couple unbalance; balance in two planes.",
      investigate_other_cause: "Pattern points to another fault; diagnose before balancing.",
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
const p = answers.unbalance.noul;
const typ = answers.unbalance_type;
const act = answers.action;
const alternatywy = Object.entries(answers)
  .filter(([k, v]) => k.startsWith("alt_") && v.noul >= 0.5)
  .map(([k, v]) => `${k.replace("alt_", "")} (${r2(v.noul)})`);
const plaszczyzny = answers.balancing_planes;
const planyJev = { one_plane: 1, two_planes: 2 }[plaszczyzny.choice];
// rozbieżność między regułą |C|/|S| a oceną Jev lub niespójna faza H/V → diagnosta
const rozbieznoscPlaszczyzn = planyJev !== undefined && planyJev !== dekompozycja.planes_by_rule;
const doDiagnosty =
  (p > 0.3 && p < 0.7) || typ.confidence < 0.6 || act.confidence < 0.6 || plaszczyzny.confidence < 0.6 ||
  alternatywy.length > 0 || !dekompozycja.phase_consistent || rozbieznoscPlaszczyzn;

console.log(`Model: ${model}`);
console.log(`ISO 20816-3: strefa ${strefa} (max ${maxOverall} mm/s; granice ${granice.join(" / ")})`);
console.log("Wskaźniki:", JSON.stringify(wskazniki), JSON.stringify(fazaMiedzyLozyskami));
console.log(`Niewyważenie: p = ${r2(p)}`);
console.log(`Rodzaj: ${typ.choice} (pewność ${r2(typ.confidence)})`, typ.probabilities);
console.log(
  `Rozkład S/C: H |S|=${rozkladSC.H.static_S_mm_s} |C|=${rozkladSC.H.couple_C_mm_s} (C/S ${rozkladSC.H.ratio_C_to_S}); ` +
    `V |S|=${rozkladSC.V.static_S_mm_s} |C|=${rozkladSC.V.couple_C_mm_s} (C/S ${rozkladSC.V.ratio_C_to_S}); ` +
    `spójność H/V ${dekompozycja.phase_consistency_H_vs_V_deg}° (${dekompozycja.phase_consistent ? "OK" : "NIESPÓJNE"})`,
);
console.log(
  `Reguła: ${dekompozycja.planes_by_rule} płaszczyzn(a) (próg C/S ${PROG_PAROWEJ}); ` +
    `szac. drgania po korekcie w 1 płaszczyźnie ≈ ${dekompozycja.est_residual_after_single_plane_mm_s} mm/s (strefa ${dekompozycja.est_residual_zone})`,
);
console.log(`Płaszczyzny wg Jev: ${plaszczyzny.choice} (pewność ${r2(plaszczyzny.confidence)})`, plaszczyzny.probabilities);
if (rozbieznoscPlaszczyzn) console.log("⚠ Jev i reguła C/S wskazują różną liczbę płaszczyzn.");
console.log(`Alternatywne przyczyny ≥ 0.5: ${alternatywy.join(", ") || "brak"}`);
console.log(`Zalecenie: ${act.choice} (pewność ${r2(act.confidence)})`, act.probabilities);
console.log(doDiagnosty ? "➜ Do weryfikacji przez diagnostę." : "➜ Wynik jednoznaczny.");
console.log(`Tokeny: we ${usage.input_tokens}, wy ${usage.output_tokens}`);
