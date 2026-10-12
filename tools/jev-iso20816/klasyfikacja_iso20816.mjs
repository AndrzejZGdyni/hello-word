// Klasyfikacja maszyny wg ISO 20816-3 (grupa, fundament) + strefa A/B/C/D dla pomiarów.
// Podział pracy: kod = reguły liczbowe i tabela granic; Jev = interpretacja opisu tekstowego.
import { readFileSync } from "node:fs";
const w = JSON.parse(readFileSync(process.argv[2], "utf8"));
const m = w.maszyna;

// Granice A/B, B/C, C/D [mm/s RMS] – zweryfikuj z normą (źródła wtórne: Fabrico).
const GRANICE = {
  1: { sztywny: [2.3, 4.5, 7.1], podatny: [3.5, 7.1, 11.0] },
  2: { sztywny: [1.4, 2.8, 4.5], podatny: [2.3, 4.5, 7.1] },
};
const strefa = (v, g) => ["A", "B", "C", "D"][g.filter((x) => v > x).length];

const state = {
  machine_description: m.opis_tekstowy,
  foundation_description: m.opis_fundamentu,
  rated_power_kW: m.moc_kW,
  motor_shaft_height_mm: m.wysokosc_osi_silnika_mm,
  speed_rpm: m.obroty_rpm,
  measured_first_natural_frequency_Hz: m.czestosc_wlasna_ukladu_Hz,
};
const questions = {
  scope: {
    type: "choice",
    instructions: "Which part of the ISO 20816 series is the natural choice for judging overall vibration of this machine?",
    criteria: {
      part3_industrial: "Industrial machine above 15 kW and 120-30000 rpm judged by in-situ measurements on bearings or housings: electric motor or generator (also the motor that drives a pump), fan or blower, compressor, steam turbine up to 50 MW. Rotodynamic pumps are NOT in this part.",
      pump_part7: "Rotodynamic pump (centrifugal, mixed-flow or axial) for industrial use above 1 kW, including boiler feed pumps: the pump itself is judged by ISO 10816-7. A flexibly coupled driver is judged separately.",
      part2_large_steam: "Land-based steam turbine or generator above 50 MW at 1500/1800/3000/3600 rpm.",
      part4_gas_turbine: "Gas turbine set with fluid-film bearings.",
      part5_hydro_pumping: "Machine set in a hydraulic power plant or a pumping plant.",
      other_or_unclear: "Reciprocating machine, below 15 kW, or description insufficient.",
    },
  },
  foundation: {
    type: "choice",
    instructions: "Is the support (foundation) of the machine rigid or flexible in the direction of measurement, in the sense of ISO 20816-3?",
    criteria: {
      rigid: "Machine-plus-support first natural frequency is well above running speed (at least ~25% higher): massive concrete block, heavily grouted baseplate.",
      flexible: "First natural frequency is below or close to running speed: steel frame or skid, spring or elastomer mounts, light structure.",
      unclear: "Description does not allow deciding.",
    },
  },
};
const { TypeSafeClient } = await import("@typesafe-ai/sdk");
const { model, answers, usage } = await new TypeSafeClient().systemOne({ model: process.env.TYPESAFE_DEFAULT_MODEL ?? "jev-latest", state, questions });
const r2 = (x) => Math.round(x * 100) / 100;

// Grupa – reguła w kodzie (silnik: wysokość osi; reszta: moc).
let grupa = null, powodGrupy;
if (m.wysokosc_osi_silnika_mm != null && m.wysokosc_osi_silnika_mm >= 315) [grupa, powodGrupy] = [1, "wysokość osi ≥ 315 mm"];
else if (m.moc_kW > 300) [grupa, powodGrupy] = [1, "moc > 300 kW"];
else if (m.wysokosc_osi_silnika_mm != null && m.wysokosc_osi_silnika_mm >= 160) [grupa, powodGrupy] = [2, "wysokość osi 160–315 mm"];
else if (m.moc_kW >= 15) [grupa, powodGrupy] = [2, "moc 15–300 kW"];
else powodGrupy = "poniżej zakresu ISO 20816-3 (moc < 15 kW)";

// Fundament – reguła liczbowa, jeśli znana częstość własna; w innym razie Jev.
let fund, powodFund;
if (m.czestosc_wlasna_ukladu_Hz != null) {
  fund = m.czestosc_wlasna_ukladu_Hz >= 1.25 * (m.obroty_rpm / 60) ? "sztywny" : "podatny";
  powodFund = `reguła: f_własna ${m.czestosc_wlasna_ukladu_Hz} Hz ${fund === "sztywny" ? "≥" : "<"} 1,25 × ${r2(m.obroty_rpm / 60)} Hz`;
} else {
  const f = answers.foundation;
  fund = f.choice === "rigid" ? "sztywny" : f.choice === "flexible" ? "podatny" : null;
  powodFund = `Jev: ${f.choice} (pewność ${r2(f.confidence)})`;
  if (f.confidence < 0.8) fund = null; // za niska pewność – podaj obie wersje
}

console.log(`Model: ${model}`);
if (answers.scope.choice === "pump_part7") {
  console.log("➜ Opisana maszyna to pompa wirnikowa: ocenia się ją wg ISO 10816-7, a nie ISO 20816-3.");
  console.log("  Tabela granic ISO 10816-7 nie jest zaimplementowana. Silnik napędowy opisz osobno (typ: silnik).");
  process.exit(0);
}
console.log(`Zakres normy wg Jev: ${answers.scope.choice} (pewność ${r2(answers.scope.confidence)})`);
console.log(`Grupa: ${grupa ?? "—"} (${powodGrupy})`);
console.log(`Fundament: ${fund ?? "NIEJEDNOZNACZNY"} (${powodFund})`);
if (grupa == null) { console.log("➜ Poza zakresem ISO 20816-3 lub brak danych."); process.exit(0); }
for (const typ of fund ? [fund] : ["sztywny", "podatny"]) {
  const g = GRANICE[grupa][typ];
  console.log(`\nGranice (${typ}): A/B ${g[0]}  B/C ${g[1]}  C/D ${g[2]} mm/s RMS`);
  console.log(`  A: ≤ ${g[0]}   B: ${g[0]}–${g[1]}   C: ${g[1]}–${g[2]}   D: > ${g[2]}`);
  for (const [k, p] of Object.entries(w.punkty)) console.log(`  ${k.padEnd(10)} ${String(p.v_rms_mm_s).padStart(5)} mm/s → strefa ${strefa(p.v_rms_mm_s, g)}`);
}
if (!fund) console.log("\n➜ Fundament niejednoznaczny: podano obie wersje; zmierz częstość własną lub opisz fundament dokładniej.");
if (answers.scope.choice !== "part3_industrial") console.log("➜ Uwaga: Jev wskazuje inną część serii ISO 20816 niż -3; tabela granic może nie obowiązywać.");
console.log(`Tokeny: we ${usage.input_tokens}, wy ${usage.output_tokens}`);
