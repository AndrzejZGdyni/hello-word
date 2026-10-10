// Ocena luzów mechanicznych (typ A/B/C) wentylatora spalin przy użyciu Jev (TypeSafe System One).
// Układ: silnik (łożyska kulkowe/walcowe) – sprzęgło kłowe – wentylator (łożyska dwurzędowe baryłkowe).
// Użycie:
//   node ocena_luzow.mjs pomiar.json --dry-run   # pokazuje zapytanie, bez wywołania API
//   TYPESAFE_API_KEY=... node ocena_luzow.mjs pomiar.json
// W sesji Claude Code w chmurze klucz dokleja proxy (sekret sieciowy), więc:
//   TYPESAFE_API_KEY=placeholder NODE_USE_ENV_PROXY=1 node ocena_luzow.mjs pomiar.json
import { readFileSync } from "node:fs";

const [, , plik = "pomiar.json", ...flagi] = process.argv;
const dryRun = flagi.includes("--dry-run");
const pomiar = JSON.parse(readFileSync(plik, "utf8"));
const r2 = (x) => Math.round(x * 100) / 100;
const roznicaFaz = (a, b) => {
  const d = Math.abs(a - b) % 360;
  return d > 180 ? 360 - d : d;
};

// --- Progi robocze (reguły praktyczne, nie wartości normowe – do kalibracji) ---
const PROG_HARM_REL = 0.1; // harmoniczna istotna, gdy ≥ 10 % amplitudy 1x ...
const PROG_HARM_ABS = 0.2; // ... i ≥ 0,2 mm/s (poniżej – poziom szumu)
const PROG_SERII_C = 5; // min. długość serii harmonicznych dla typu C
const PROG_NIESTAB_FAZY_DEG = 20; // odch. std. fazy 1x z powtórzeń → faza niestabilna
const PROG_FAZY_ZLACZA_DEG = 135; // skok fazy 1x (pion) przez złącze ~180° → typ A
const PROG_2X_1X_B = 0.5; // 2x/1x dla typu B

// --- 1. Strefa ISO 20816-3 (granice A/B, B/C, C/D w mm/s RMS; zweryfikuj z normą) ---
const GRANICE = {
  1: { sztywny: [2.3, 4.5, 7.1], podatny: [3.5, 7.1, 11.0] },
  2: { sztywny: [1.4, 2.8, 4.5], podatny: [2.3, 4.5, 7.1] },
};
const m = pomiar.maszyna;
const granice = GRANICE[m.grupa_ISO_20816_3][m.fundament];
const strefa = (v) => ["A", "B", "C", "D"][granice.filter((g) => v > g).length];

// --- 2. Narzędzia: widmo rzędowe, statystyka kołowa fazy ---
const rzedy = pomiar.rzedy;
const amp = (tab, o) => tab[rzedy.indexOf(o)];
const widmo = (tab) => Object.fromEntries(rzedy.map((o, i) => [`${o}x`, tab[i]]));
const kolo = (stopnie) => {
  const rad = stopnie.map((d) => (d * Math.PI) / 180);
  const x = rad.reduce((s, a) => s + Math.cos(a), 0) / rad.length;
  const y = rad.reduce((s, a) => s + Math.sin(a), 0) / rad.length;
  const R = Math.min(1, Math.hypot(x, y));
  return {
    mean: ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360,
    std: R > 0 ? (Math.sqrt(-2 * Math.log(R)) * 180) / Math.PI : 180,
  };
};
const LOZYSKA_EN = {
  kulkowe: "ball bearing",
  walcowe: "cylindrical roller bearing",
  "dwurzędowe baryłkowe": "double-row spherical roller bearing (self-aligning)",
};

// --- 3. Wskaźniki luzów liczone w kodzie ---
const analizaKierunku = (tab) => {
  const a1 = amp(tab, 1);
  const prog = Math.max(PROG_HARM_ABS, PROG_HARM_REL * a1);
  let seria = 1; // najwyższy rząd w nieprzerwanej serii 1x, 2x, 3x ... powyżej progu
  for (let o = 2; o <= 10 && amp(tab, o) >= prog; o++) seria = o;
  const polowkowe = [0.5, 1.5, 2.5];
  const energia = Math.sqrt([2, 3, 4, 5, 6, 7, 8, 9, 10].reduce((s, o) => s + amp(tab, o) ** 2, 0));
  return {
    harmonic_series_length: seria,
    half_orders_present_of_3: polowkowe.filter((o) => amp(tab, o) >= prog).length,
    ratio_half_order_to_1x: r2(Math.max(...polowkowe.map((o) => amp(tab, o))) / a1),
    ratio_2x_to_1x: r2(amp(tab, 2) / a1),
    ratio_3x_to_1x: r2(amp(tab, 3) / a1),
    ratio_harmonics_rms_to_1x: r2(energia / a1),
  };
};

const punkty = {};
const typyWgReguly = {};
for (const [nazwa, p] of Object.entries(pomiar.punkty)) {
  const H = analizaKierunku(p.H);
  const V = analizaKierunku(p.V);
  const fH = kolo(p.faza_1x_H);
  const fV = kolo(p.faza_1x_V);
  const niestab = Math.max(fH.std, fV.std);
  const seria = Math.max(H.harmonic_series_length, V.harmonic_series_length);
  const polowkowe = Math.max(H.half_orders_present_of_3, V.half_orders_present_of_3);
  const rel2x = Math.max(H.ratio_2x_to_1x, V.ratio_2x_to_1x);

  // złącza: skok fazy 1x w pionie między kolejnymi stacjami
  const zl = p.zlacza_pionowe_1x;
  let maxSkok = 0;
  let gdzie = null;
  for (let i = 1; i < zl.length; i++) {
    const d = roznicaFaz(zl[i - 1].faza, zl[i].faza);
    if (d > maxSkok) {
      maxSkok = d;
      gdzie = `${zl[i - 1].stacja} → ${zl[i].stacja}`;
    }
  }

  // reguła robocza dla typów A / B / C
  const typy = [];
  const czyC = seria >= PROG_SERII_C && (polowkowe >= 2 || niestab >= PROG_NIESTAB_FAZY_DEG);
  if (maxSkok >= PROG_FAZY_ZLACZA_DEG) typy.push("A");
  if (!czyC && seria >= 3 && rel2x >= PROG_2X_1X_B && niestab >= PROG_NIESTAB_FAZY_DEG) typy.push("B");
  if (czyC) typy.push("C");
  typyWgReguly[nazwa] = { typy, seria, ratio: Math.max(H.ratio_harmonics_rms_to_1x, V.ratio_harmonics_rms_to_1x) };

  const maxOverall = Math.max(p.overall.H, p.overall.V, p.overall.A);
  punkty[nazwa] = {
    bearing_type: LOZYSKA_EN[p.lozysko] ?? p.lozysko,
    spectrum_H_mm_s: widmo(p.H),
    spectrum_V_mm_s: widmo(p.V),
    axial_mm_s: p.A,
    overall_mm_s: p.overall,
    iso_20816_3_zone: strefa(maxOverall),
    time_waveform: p.przebieg_czasowy,
    noise_floor_mm_s: p.podloga_szumu_mm_s,
    phase_1x_repeated_measurements_deg: { H: p.faza_1x_H, V: p.faza_1x_V },
    computed_indicators: {
      horizontal: H,
      vertical: V,
      ratio_H_to_V_1x: r2(amp(p.H, 1) / amp(p.V, 1)),
      ratio_2x_to_1x_axial: r2(p.A["2x"] / p.A["1x"]),
      phase_1x_instability_std_deg: r2(niestab),
    },
    vertical_1x_across_joints: zl,
    joint_analysis: {
      max_phase_jump_deg: maxSkok,
      at_joint: gdzie,
      amplitude_foundation_to_bearing_housing: r2(zl[zl.length - 1].amp / zl[0].amp),
      structural_looseness_A_indicated: maxSkok >= PROG_FAZY_ZLACZA_DEG,
    },
  };
}

// lokalizacja wg reguły: punkt z najdłuższą serią harmonicznych wśród punktów z podejrzeniem luzu
const kandydaci = Object.entries(typyWgReguly).filter(([, v]) => v.typy.length > 0);
kandydaci.sort((a, b) => b[1].seria - a[1].seria || b[1].ratio - a[1].ratio);
const lokalizacjaReguly = kandydaci.length ? kandydaci[0][0] : null;
const typyReguly = [...new Set(kandydaci.flatMap(([, v]) => v.typy))];

// faza przez sprzęgło (silnik DE ↔ wentylator DE), średnie kołowe z powtórzeń
const sprzeglo = {
  phase_diff_1x_radial_H_deg: Math.round(
    roznicaFaz(kolo(pomiar.punkty.motor_DE.faza_1x_H).mean, kolo(pomiar.punkty.fan_DE.faza_1x_H).mean),
  ),
  phase_diff_1x_radial_V_deg: Math.round(
    roznicaFaz(kolo(pomiar.punkty.motor_DE.faza_1x_V).mean, kolo(pomiar.punkty.fan_DE.faza_1x_V).mean),
  ),
  note: "fan_DE phase is averaged from unstable repeated readings if phase_1x_instability_std_deg is high",
};

// --- 4. Stan przekazywany do Jev ---
const fr = m.obroty_rpm / 60;
const state = {
  machine: {
    description: m.opis,
    setup:
      "motor – jaw coupling (elastomer insert) – fan; fan rotor supported on both sides (between bearings); " +
      "motor bearings: ball (NDE) and cylindrical roller (DE, coupling side); fan bearings: double-row spherical roller",
    speed_rpm: m.obroty_rpm,
    running_speed_Hz: fr,
    power_kW: m.power_kW ?? m.moc_kW,
    iso_20816_3: { group: m.grupa_ISO_20816_3, foundation: m.fundament, zone_limits_AB_BC_CD_mm_s: granice },
  },
  units: "vibration velocity mm/s RMS; phase in degrees; spectrum keys are multiples of running speed",
  measurement_points: punkty,
  phase_across_coupling_motor_DE_to_fan_DE: sprzeglo,
  technician_notes: pomiar.obserwacje ?? null,
};

const kontekst =
  "Use the order spectra of all four points in `measurement_points` (including half-orders 0.5x, 1.5x, 2.5x), " +
  "their `computed_indicators`, the repeated 1x phase readings, the vertical 1x amplitude/phase across joints " +
  "(housing → pedestal → frame → foundation), the time-waveform indicators, the noise floor, the phase across the " +
  "coupling and `technician_notes`. ";

// --- 5. Pytania (niezależne, wykonywane równolegle) ---
const KRYT_LOK = Object.fromEntries(
  Object.entries(punkty).map(([k, v]) => [
    k,
    `Strongest looseness signature (longest harmonic series, half-order components, unstable phase) is at ${k} (${v.bearing_type}).`,
  ]),
);
KRYT_LOK.none = "No point shows a looseness signature.";

const questions = {
  looseness: {
    type: "noul",
    instructions:
      kontekst + "Does the vibration pattern indicate mechanical looseness (loose or worn fit, loose mounting, structural weakness)?",
    criteria: {
      true:
        "Long series of integer harmonics of running speed (1x…8x or more), often with half-order components " +
        "(0.5x, 1.5x, 2.5x), raised noise floor, unstable 1x phase between repeated measurements, and/or ~180 deg " +
        "vertical 1x phase shift across a joint (foot, base plate, frame, foundation).",
      false:
        "Few harmonics, stable phase, no half-orders and no phase reversal across joints; pattern is better explained by another single fault.",
    },
  },
  looseness_type: {
    type: "choice",
    instructions: kontekst + "Which type of looseness best matches the pattern?",
    criteria: {
      structural_foundation:
        "Type A: weak or loose feet, base plate, frame or foundation; dominant 1x (sometimes 2x) in the loose direction, ~180 deg vertical 1x phase shift across the loose joint, no long harmonic series.",
      bearing_pedestal_or_frame:
        "Type B: loose pedestal or housing bolts, cracked frame or bearing support; 1x and 2x with a few harmonics, directional or unstable phase.",
      rotating_fit:
        "Type C: loose or worn fit of a bearing or rotating component – bearing ring or adapter sleeve loose in housing or on shaft, excessive bearing clearance, loose impeller hub; long series of harmonics, half-order components, raised noise floor, erratic phase.",
      none: "No looseness pattern.",
    },
  },
  location: {
    type: "choice",
    instructions: kontekst + "Where is the looseness located?",
    criteria: KRYT_LOK,
  },
  alt_misalignment_or_coupling_wear: {
    type: "noul",
    instructions:
      kontekst +
      "Is misalignment or jaw-coupling wear/backlash a more likely main cause than looseness " +
      "(high 2x relative to 1x, high axial vibration, ~180 deg 1x phase shift across the coupling, symptoms strongest at the coupling-side bearings of both machines)?",
  },
  alt_bearing_defect: {
    type: "noul",
    instructions:
      kontekst +
      "Is a rolling-bearing defect a more likely explanation (discrete bearing defect frequencies with harmonics and sidebands in the envelope spectrum; see `technician_notes`)?",
  },
  alt_rotor_stator_rub: {
    type: "noul",
    instructions:
      kontekst + "Is a rotor–stator rub (e.g. fan wheel against casing or inlet cone) a plausible cause (harmonics and half-orders with erratic amplitude)?",
  },
  alt_unbalance: {
    type: "noul",
    instructions:
      kontekst + "Is unbalance (e.g. build-up on the fan wheel) the primary cause of the high vibration instead of looseness?",
  },
  severity: {
    type: "score",
    instructions: kontekst + "How serious is the condition, considering vibration level, ISO zone, temperature and waveform?",
    criteria: [
      "0 – No looseness signs.",
      "1 – Slight: few harmonics, no half-orders, vibration in ISO zone A/B.",
      "2 – Moderate: harmonic series with some half-order components or unstable phase, zone B/C; inspect at the next planned stop.",
      "3 – Serious: long harmonic series with half-orders, raised noise floor, zone C, raised bearing temperature; inspect soon and limit operating time.",
      "4 – Critical: zone D or impacting/truncated waveform, risk of component failure; stop and inspect.",
    ],
  },
  action: {
    type: "choice",
    instructions: kontekst + "What is the most appropriate next action?",
    criteria: {
      continue_monitoring: "No looseness or only slight signs; keep the normal measurement interval.",
      tighten_and_check_mounting:
        "Check and torque foot, base plate and pedestal bolts, grouting and frame cracks; re-measure (types A and B).",
      inspect_bearing_seat_and_clearance:
        "Inspect bearing housing bore, shaft seat, adapter or withdrawal sleeve and lock nut, outer-ring creep; measure bearing radial clearance (type C).",
      inspect_coupling_and_alignment: "Check jaw-coupling insert wear and backlash and re-check alignment.",
      stop_and_inspect: "Stop the fan as soon as the process allows and inspect (critical condition).",
      investigate_other_cause: "Pattern points to another fault; diagnose before maintenance on mounting or bearings.",
    },
  },
};

const request = { model: process.env.TYPESAFE_DEFAULT_MODEL ?? "jev-latest", state, questions };

if (dryRun) {
  console.log(JSON.stringify(request, null, 2));
  process.exit(0);
}

// --- 6. Wywołanie Jev ---
const { TypeSafeClient } = await import("@typesafe-ai/sdk");
const client = new TypeSafeClient();
const { model, answers, usage } = await client.systemOne(request);

// --- 7. Polityka decyzji (progi do kalibracji na własnych przypadkach) ---
const TYP_JEV = { structural_foundation: "A", bearing_pedestal_or_frame: "B", rotating_fit: "C" };
const p = answers.looseness.noul;
const typ = answers.looseness_type;
const lok = answers.location;
const act = answers.action;
const alternatywy = Object.entries(answers)
  .filter(([k, v]) => k.startsWith("alt_") && v.noul >= 0.5)
  .map(([k, v]) => `${k.replace("alt_", "")} (${r2(v.noul)})`);
const typJev = TYP_JEV[typ.choice];
const rozbTyp = typJev ? !typyReguly.includes(typJev) : typyReguly.length > 0;
const rozbLok = lok.choice === "none" ? lokalizacjaReguly !== null : lokalizacjaReguly !== lok.choice;
const doDiagnosty =
  (p > 0.3 && p < 0.7) || typ.confidence < 0.6 || lok.confidence < 0.6 || act.confidence < 0.6 ||
  alternatywy.length > 0 || rozbTyp || rozbLok;

console.log(`Model: ${model}`);
console.log(`ISO 20816-3: grupa ${m.grupa_ISO_20816_3}, fundament ${m.fundament}, granice ${granice.join(" / ")} mm/s`);
for (const [k, v] of Object.entries(punkty)) {
  const ci = v.computed_indicators;
  console.log(
    `  ${k.padEnd(10)} strefa ${v.iso_20816_3_zone}  seria ${Math.max(ci.horizontal.harmonic_series_length, ci.vertical.harmonic_series_length)}x  ` +
      `połówkowe ${Math.max(ci.horizontal.half_orders_present_of_3, ci.vertical.half_orders_present_of_3)}/3  ` +
      `niestab. fazy ${ci.phase_1x_instability_std_deg}°  skok fazy przez złącze ${v.joint_analysis.max_phase_jump_deg}°  ` +
      `typy wg reguły: ${typyWgReguly[k].typy.join("+") || "-"}`,
  );
}
console.log(`Faza przez sprzęgło: H ${sprzeglo.phase_diff_1x_radial_H_deg}°, V ${sprzeglo.phase_diff_1x_radial_V_deg}°`);
console.log(`Luz mechaniczny: p = ${r2(p)}`);
console.log(`Rodzaj: ${typ.choice} (pewność ${r2(typ.confidence)})`, typ.probabilities);
console.log(`Lokalizacja: ${lok.choice} (pewność ${r2(lok.confidence)}); wg reguły: ${lokalizacjaReguly ?? "brak"}`);
console.log(`Pilność: ${r2(answers.severity.score)} / 4 – ${answers.severity.legend[Math.round(answers.severity.score)]}`);
console.log(`Alternatywne przyczyny ≥ 0.5: ${alternatywy.join(", ") || "brak"}`);
console.log(`Zalecenie: ${act.choice} (pewność ${r2(act.confidence)})`, act.probabilities);
if (rozbTyp || rozbLok) console.log("⚠ Ocena Jev różni się od reguły roboczej (typ lub lokalizacja).");
console.log(doDiagnosty ? "➜ Do weryfikacji przez diagnostę." : "➜ Wynik jednoznaczny.");
console.log(`Tokeny: we ${usage.input_tokens}, wy ${usage.output_tokens}`);
