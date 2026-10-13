# MASTER PROMPT: SV16 board. Make a netted, footprint-based KiCad PCB (NO ROUTING)

WORKING FOLDER: this `rebuild/` folder is the ONLY folder you have. Every input and every output lives in it. Do not look for files outside it. Relative paths in this prompt are relative to this folder.

You are an autonomous PCB agent working in a local folder that contains the SV16 board files. Your job is to take an UNROUTED KiCad PCB and produce a NETTED, FOOTPRINT-BASED board file: every footprint is the final one, every value is set, every pad is assigned to its net, the layer stack and planes are defined, and the board has NO tracks and NO vias. The board must show the full ratsnest (every net unrouted). Do NOT route anything. Do NOT generate release files.

You have no human to ask during the run. When a decision is not in this document, use the default given here, record it in REPORT.md, and continue. Always finish by writing REPORT.md.

Read this whole prompt before you touch any file.

---

## 0. Scope

IN SCOPE:
- Apply the footprint changes in section 3.2.
- Set the values in section 3.1 and the other changes in section 3.3.
- Make sure every pad is on the net the schematic/spec says (section 4). Do not change pad numbers.
- Define the stackup and the two inner planes (In1.Cu GND zone, In2.Cu split power zone) as zones, so the planes exist. Zones are defined, not routed copper; fill them only if the tool requires it, and say so.
- Delete the old tracks and vias from the uploaded file (section 2, rule 4).
- Write the netted board and REPORT.md.

OUT OF SCOPE (do NOT do these):
- Routing of any net. No new tracks. No new vias (except none; do not add vias).
- Length matching, differential-pair tuning, trace-width routing, or copper pours beyond the two inner planes.
- Gerber, drill, BOM and position (pick-and-place) release files.
- Changing the placement. Components stay where they are.

Expected result: the board shows 0 tracks, 0 vias, and all nets as ratsnest lines. "Unconnected" items are EXPECTED and are NOT an error for this task. Report the count, do not fix it.

---

## 1. Files you must read (all in this folder)

1. `<UNROUTED_FILE>`: the UNROUTED KiCad PCB the user placed in this folder. This is your starting board. Its name is not fixed. Find it as the `.kicad_pcb` file in this folder that is NOT `SBSV-16_rebuild_step1_values.kicad_pcb` and NOT `sv16_board_netted.kicad_pcb` (the output). If there is no such file, STOP, write REPORT.md saying the unrouted board is missing, and do not invent a board. If more than one candidate exists, pick the one with 0 tracks and 0 vias. State your choice in REPORT.md.
2. `SV16_TODO_rebuild_step1.pdf`: the checklist. Use sections A (footprints), B (open values), C (values set), D (schematic checks), E (purchases) as reference. Ignore section F (routing) for this task.
3. `BOM_rebuild_step1.csv` (and the PDF `SV16_BOM_rebuild_step1.pdf`): part list, values and footprints with bought/needed status.
4. `PCB_COMPONENTS.pdf` (spec, 19 pages, in this folder): source for values, pinouts and net names. Section 3 = component list. Section 4 = pin-level connections. Section 10 = corrections you must respect.
5. The schematic (`*.kicad_sch`), if it is in this folder. It is not expected here; if it is absent, say so. It is the source of truth for net names and pin connections. If it is absent, record that in REPORT.md. Do not invent a netlist.

---

## 2. Hard rules

1. Do NOT move any component. Keep every footprint at its current X/Y and rotation. A footprint is replaced in place (same reference, same position, same rotation). If a new footprint would overlap another part, report the conflict and do not move anything.
2. Do NOT change pad numbers. Do NOT rename nets, except the defaults in section 5.
3. Do NOT change schematic connectivity. If the schematic is present, match it. If not, keep the nets as they are in the unrouted file and report any mismatch with section 4.
4. Do NOT copy, merge or import ANY tracks or vias from: `sv16_board_routed_draft.kicad_pcb`, `routing_state.json`, `routing.kicad_pcb.txt`, `sv16_board_working.kicad_pcb`, `sv16_board_placed_native.kicad_pcb`, or any `routing/` folder. Delete the tracks and vias that are in the uploaded file.
5. Do NOT route anything. Do NOT add tracks or vias.
6. Do NOT guess values. Parts marked UNDECIDED in section 3.3 stay as they are, and you report them.
7. Do NOT delete a net or a footprint. Do NOT delete a pad.
8. Do NOT generate Gerber, drill, BOM or position release files.
9. Do NOT claim the board is routed, DRC-clean or fabrication-ready. This task is netted footprints only.
10. Do NOT fabricate counts, file contents or part data. Quote the numbers from the files you actually produced.

---

## 3. Footprints and values

### 3.1 Starting-point facts

`SBSV-16_rebuild_step1_values.kicad_pcb` (this folder) is a copy of the uploaded board with 37 Value fields changed. It has 141 footprints at the original positions, 119 nets, and the old 1,783 tracks and 179 vias. Use it as a reference for values. The 37 changed values are:

- Q2: BC817 -> MMBT3904 (SOT-23)
- Q4: BC807 -> MMBT3906 (SOT-23)
- C36, C37: 100 nF -> 22 pF
- R1, R13, R14, R15, R16, R17, R18, R19, R26, R32: 10k
- R2, R3, R4, R5, R25: 4.7k
- R6, R7, R8, R31, R33, R34: 1k
- R9, R10, R11, R12: 100R
- R21, R22, R23, R24: 0R
- R27, R28, R29, R30: 470R
- R36, R37: 5.1k
- R38: 12.4k
- R39, R46: 33k
- R40, R41, R43: 100k
- R47: 10k

In your unrouted file, check each value. Set any that are not set. Record in REPORT.md which were already set.

### 3.2 Footprint changes (current -> new)

For each row, verify the KiCad library name exists in your local footprint library before use. If it does not, do not guess: record the item as NOT DONE with the reason, and continue.

| Ref | Current footprint | New footprint | Reason |
|---|---|---|---|
| C25 | Capacitor_SMD:C_0805_2012Metric | Capacitor_SMD:CP_Elec_4x5.4 | 10 uF electrolytic (bought) |
| C30 | Capacitor_SMD:C_0805_2012Metric | Capacitor_SMD:CP_Elec_4x5.4 | 10 uF electrolytic (bought) |
| C32 | Capacitor_SMD:C_0805_2012Metric | Capacitor_SMD:C_0603_1608Metric | 470 nF in 0603 |
| C36 | Capacitor_SMD:C_0603_1608Metric | Capacitor_SMD:C_0805_2012Metric | 22 pF C0G 0805 (bought) |
| C37 | Capacitor_SMD:C_0603_1608Metric | Capacitor_SMD:C_0805_2012Metric | same as C36 |
| R5 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_0805_2012Metric | 4.7k 0805 pack (bought) |
| R25 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_0805_2012Metric | 4.7k 0805 pack (bought) |
| R6 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_1206_3216Metric | 1k 1206 pack (bought) |
| R7 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_1206_3216Metric | 1k 1206 pack (bought) |
| R8 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_1206_3216Metric | 1k 1206 pack (bought) |
| R9 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0805_2012Metric | 100R 0805 pack (bought) |
| R10 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0805_2012Metric | same |
| R11 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0805_2012Metric | same |
| R12 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0805_2012Metric | same |
| R47 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0603_1608Metric | 10k 5% 0603 (Yageo RC0603JR-0710KL, in cart) |
| FB1 | Inductor_SMD:L_0603_1608Metric (or the 0603 ferrite footprint) | Inductor_SMD:L_0805_2012Metric | 600R ferrite 0805 (TDK MPZ2012S601ATD25, in cart, qty 2) |
| Y2 | Crystal:Crystal_HC49-4H_Vertical | Crystal:Crystal_SMD_HC49-SD (verify; or the footprint of the bought SMD HC49/U 12 MHz crystal) | SMD 12 MHz crystal (to buy) |
| L1 | Inductor_SMD:L_Sunlord_SWPA6045S | Inductor_SMD:L_Sunlord_MWSA0518_5.4x5.2mm (verify pads against the bought CD54 datasheet) | spec footprint |
| L2 | Inductor_SMD:L_Sunlord_SWPA6045S | Inductor_SMD:L_Sunlord_MWSA0518_5.4x5.2mm (same as L1) | spec footprint |
| R21 | Resistor_SMD:R_0603_1608Metric | Keep the R_0603 footprint, set value 0R, mark it as a solder-bridge link in REPORT.md. Do not route it. | no 0R bought |
| R22 | Resistor_SMD:R_0603_1608Metric | same as R21 | |
| R23 | Resistor_SMD:R_0603_1608Metric | same as R21 | |
| R24 | Resistor_SMD:R_0603_1608Metric | same as R21 | |

Footprints that are ALREADY correct (do not change): C21 (CP_EIA-7343-31 tantalum), C22 (CP_Elec_6.3x5.4), C23 (CP_Elec_8x10.5), C24 (CP_Elec_8x10.5), C39 (CP_Elec_4x5.4), C40 and C41 (CP_Elec_6.3x5.4), C42 (CP_Elec_4x5.4). R1 and the other 10k 0603 resistors. R2 to R4, R27 to R30, R36, R37 (0805). R31, R33, R34, R39, R46, R49 (1206). R38 (0402). R40, R41, R43, R44, R45, R48 (0603). J8 USB-C HRO TYPE-C-31-M-12. J9 barrel jack. D8, D9, D11 (SMA). Headers J1, J3 to J6, J10 (2.54 mm).

FB1 (600R ferrite): change the footprint to 0805 (Inductor_SMD:L_0805_2012Metric) and set the value to 600R @100MHz. The bought part is TDK MPZ2012S601ATD25 (0805). Keep the net connections.

### 3.3 Other changes

- ADD J7: footprint Connector_PinHeader_2.54mm:PinHeader_2x25_P2.54mm_Vertical, marked NOT FITTED (DNP). Spec: footprint only. J7 pads are not connected to nets unless the spec says so.
- D6 (red LED, INITN indicator): mark DNP. Keep footprint and nets.
- J2 (1.27 mm 2x5 box header): mark DNP. Spec allows leaving it unpopulated and using J1.
- J6 (MOTOR, keyed): use a shrouded, keyed 1x6 2.54 mm header (the shroud key stops reversed insertion). Keep the 1x6 footprint. Record in REPORT.md.
- J3: move back to its original position (x 194.65 mm, y 120.24 mm, as in the source board). Do not move any other component.
- G*** logo footprint: leave it removed and record that in REPORT.md.
- Values kept from the board, not in spec. Keep them and report their purpose as unverified: R45 (100k), R48 (100k, EN divider top), R49 (33k, EN divider bottom), C34 (100 nF), C35 (100 pF). R44: no value anywhere, leave it unset and report it. U6 COMP RC network: no values in the spec or the board. The inputs are in the spec: L2 = 10 uH (section 3.4), output bulk C21 = 100 uF tantalum plus 100 nF, and the 1V1 target from R38 12.4k / R39 33k (0.8 x (1 + 12.4/33) = 1.10 V). Compute Rc and Cc from the MP1584EN datasheet compensation method and mark them as calculated, not verified. If you cannot do this, leave them unset and report it.
- C39, C40, C41, C42 stay ELECTROLYTIC (user decision). Do not change to ceramic.
- C23: change to 470 uF 25 V electrolytic, same CP_Elec_8x10.5 footprint. Reason: 16 V on a 12 V input is 75% of rated voltage, too close to the limit for an electrolytic. 25 V gives about 48%. Report the change.

### 3.4 Parts not yet in hand (report them, do not change the design because of them)

- U1 FPGA LFE5U-12F-6TG144C (not bought)
- U3 second W25Q64JVSSIQ (1 of 2 bought)
- Y1 ECS-3225MV-250 (active 25 MHz XO, 3.2x2.5 mm, 4 pads, 1.62 to 3.63 V, CMOS 15 pF). Pin 1 Tri-state (high or NC = active, low = high-Z), pin 2 GND, pin 3 OUT, pin 4 VDD. Not yet in hand.
- Y2 12 MHz SMD crystal (not bought)
- D8, D9, D11: third SS34 (2 of 3 bought)
- 10k 0603 5% resistors: 12 pieces (Yageo RC0603JR-0710KL, in cart, qty 110): R1, R13-R19, R26, R32 and R47. The user uses 5% parts only.
- 22 pF 0805 C0G caps: 2 pieces (Yageo CC0805JRNPO9BN220).
- Barrel jack J9, SW1, SW2, JP1 shunt, headers: the user says they already have these; confirm the footprints match.

---

## 4. Nets: what each pad must be connected to

The spec (`PCB_COMPONENTS.pdf`) section 4 gives the pin connections. The board already has nets assigned to pads. Your job is to check them against the spec and report differences, and only fix them if the schematic says so.

Key connections (check these pads):

- U1 FPGA power. 1V1 on pins 20, 29, 38, 66, 83, 130. 2V5 on pins 17, 53, 96, 132. 3V3 on pins 9, 16, 36, 43, 70, 86, 100, 122, 137. GND on pins 8, 15, 21, 32, 42, 65, 75, 85, 87, 101, 123, 129, 131, 138. NC on pins 109, 144.
- U1 configuration: CCLK (pin 54) to R9 (100R) to U2.6 and R8 (1k) to 3V3. Pin 46 (MISO) to R11 to U2.2. Pin 47 (MOSI) to R10 to U2.5. Pin 49 (CSSPIN) to R12 to U2.1. Pin 51 unused.
- PROGRAMN (pin 57): R2 (4.7k) to 3V3, SW2 to GND, J1 pin 4, Q1 drain.
- INITN (pin 55): R3 (4.7k) to 3V3, J1 pin 10, R31 (1k) to Q4 base.
- DONE (pin 56): R4 (4.7k) to 3V3, J1 pin 9, R32 (10k) to Q2 base.
- CFG_0 (pin 62) to R6 (1k) to GND. CFG_1 (pin 59) to R5 (4.7k) to 3V3. CFG_2 (pin 58) to R7 (1k) to GND.
- TCK, TMS, TDI, TDO (pins 63, 64, 61, 60): J1 pins 8, 6, 3, 2 and J2 pins 5, 2, 3, 4.
- clk_25m (pin 133): Y1 output (OUT pad).
- ext_rst_n (pin 134): SW1, R1 (10k) to 3V3, C1 (100 nF) to GND.
- uart_rx, uart_tx (pins 73, 74): U4 (CH340G) or J10, through R21 to R24.
- flash_sck, flash_cs_n, flash_mosi, flash_miso (pins 110, 111, 112, 113): U3 pins 6, 1, 5, 2.
- spi0_sck, spi0_cs_n, spi0_mosi, spi0_miso (pins 114 to 117): J3 pins 12, 11, 13, 14.
- led[0..3] (pins 39, 40, 41, 44): R27 to R30 (470R) to D2 to D5, to 3V3.
- gpio_a[0..7] (pins 45 to 52): J5 pins 1 to 8. gpio_a[8..15] (pins 97 to 99, 104 to 108): J3 pins 3 to 10. gpio_b[0..15] (pins 135, 136, 139 to 143, 128, 124 to 127, 1 to 4): J4 pins 3 to 18.
- pwm_out, motor_dir1, motor_dir2, motor_fault_n (pins 88, 89, 102, 103): J6 pins 3 to 6.

Power and regulators:
- U5 AP62300TWU-7 (SOT-23-6): VIN from VM_IN, SW to L1 (10 uH) to 3V3. FB pin must be on net 3V3 (spec correction 1). Connect `U5_FB` to 3V3 as the spec says, and report the change. R46 (33k) and R47 (10k) feedback divider. R48 and R49: EN divider from VM_IN (values UNDECIDED). C38 100 nF on BST.
- U6 MP1584EN-LF-Z (SOIC-8, exposed pad = GND): output 1V1 via L2 (10 uH). Catch diode D11 (SS34). R38 (12.4k) top, R39 (33k) bottom. R40 (100k) FREQ to GND. R41 (100k) and C31 (470 nF) EN delay. C33 100 nF BST. COMP RC network: the net `U6_COMP_RC` exists. Values are not in the spec or the board: leave unset and report the inputs needed.
- U7 LP5907MFX-2.5 (SOT-23-5): 3V3 in, 2V5 out. C30 (10 uF) on input, C42 (10 uF electrolytic) on output. R43 (100k) 3V3 to EN, C32 (470 nF) EN to GND.
- VM_IN: from J9 barrel jack, through FB1, to D8/D9 (SS34) OR with USB VBUS. VM_IN also goes to J6 pin 1.
- U8 USBLC6-2SC6: ESD on USB_DP and USB_DN, VBUS clamp.

If the schematic is present, it overrides this section. Record each difference in REPORT.md.

---

## 5. Net-name decisions (defaults)

The board uses two names that differ from the spec. The user has not decided them. Apply the defaults and list them in REPORT.md for the user to confirm.

| Item | Board uses | Spec uses | DEFAULT |
|---|---|---|---|
| USB data pair | USB_DP, USB_DN | USB_D+, USB_D- | Keep USB_DP and USB_DN |
| 5 V rail | 5V_USB | 5V (J3, J4 pins 17, 18) | Keep 5V_USB |

Do not rename any other net. The file already has these nets: clk_25m, ext_rst_n, uart_rx, uart_tx, flash_sck, flash_cs_n, flash_mosi, flash_miso, spi0_sck, spi0_cs_n, spi0_mosi, spi0_miso, VM_IN, VM_IN_RAW, 3V3, 2V5, 1V1, GND, CCLK, DONE, INITN, PROGRAMN, TCK, TMS, TDI, TDO, U2_CLK, U2_CS, U2_DI, U2_DO, U2_HOLD, U2_WP, U3_HOLD, U3_WP, U4_DTR, U4_RXD, U4_TXD, U4_V3, U5_BST, U5_EN, U5_FB, U5_SW, U6_BST, U6_COMP, U6_COMP_RC, U6_EN, U6_FREQ, U6_SW, U7_EN, Y2_XI, Y2_XO, led0 to led3 (and led0_k to led3_k), motor_dir1, motor_dir2, motor_fault_n, pwm_out, A0 to A15, B0 to B15, CC1, CC2, CFG_0, CFG_1, CFG_2, D1_A, D6_K, D7_A, DTR_F, FB_1V1, J9_VIN, J10_RX, J10_TX, Q1_G, Q2_B, Q2_C, Q4_B, Q4_C, USB_DN_F, USB_DP_F, USB_VBUS.

Count the nets you actually find. If the number differs from the list above, report the difference and the names involved.

---

## 6. Planes and stackup (zones, not routing)

- Layers: F.Cu signal (top), In1.Cu GND plane, In2.Cu power plane, B.Cu signal (bottom). The unrouted file currently types In1.Cu and In2.Cu as "power" with no zones. Set In1.Cu to type plane with a zone on net GND covering the board. Set In2.Cu to a zone set for the split power pours: 3V3, 1V1 and 2V5. Keep copper out of the Edge.Cuts and the mounting holes.
- Do not add any other zone on F.Cu or B.Cu. Do not fill any zone unless the tool needs it to show the planes; if you fill, say so in REPORT.md.
- Keep the 4 mounting holes H1 to H4 (3.2 mm, M3). Check that the Edge.Cuts outline is 100 x 100 mm; if it is not, report it and do not change it.

---

## 7. Steps (log each step in WORKLOG.md)

Step 0. Create `agent_work/` in this folder. Create `WORKLOG.md`. Back up the original unrouted file to `agent_work/backup_<UNROUTED_FILE>` before you change anything.

Step 1. Identify `<UNROUTED_FILE>` (section 1). Record counts in WORKLOG.md: footprints, tracks, vias, zones, nets, layers, Edge.Cuts shape.

Step 2. Check the to-do and this prompt against the unrouted file. For each footprint in 3.2 and each value in 3.1, record whether it is already applied.

Step 3. Apply the footprint changes (3.2). Replace in place: same reference, same position, same rotation. Confirm no footprint moved (compare X/Y before and after for every reference).

Step 4. Apply the value changes not already set (3.1) and the other changes (3.3): J7 added DNP, D6 DNP, J2 DNP, the J6 keying note, FB1 kept.

Step 5. Delete all tracks and vias. Keep footprints, pads, nets, zones, graphic lines and text. Confirm 0 tracks and 0 vias.

Step 6. Check every pad's net against section 4 and the schematic (if present). Report each difference. Apply the net-name defaults in section 5.

Step 7. Set the planes and stackup (section 6). Do not route.

Step 8. Check the file opens and the footprint and net counts are right. Confirm the board shows the ratsnest (every net unrouted). Record the unconnected count; it is expected to be high and is not an error.

Step 9. Write REPORT.md (section 8) and save the board as `sv16_board_netted.kicad_pcb`.

---

## 8. REPORT.md (required content)

1. Summary. What input file was used, what output file was produced, and the one biggest open issue.
2. Input inventory. File names used, counts (footprints, tracks before deletion, vias before deletion, zones, nets), and the choice of unrouted file if there was more than one candidate.
3. Footprint changes. Table: reference, old footprint, new footprint, status (done, not done), reason.
4. Value changes. Table: reference, old value, new value, status, reason. Include the UNDECIDED items left unchanged.
5. Net check. Each net-name default applied. Every difference found against the schematic or section 4.
6. Planes and stackup. What was set, and whether any zone was filled.
7. Parts not in hand (section 3.4).
8. Decisions taken: L2 10 uH; Y1 ECS-3225MV-250; C23 to 25 V; J6 shrouded keyed header; U5 FB to 3V3; net names kept as in the file, spec names recorded in REPORT.md; G*** logo left removed; J3 back to original position; FB1 to 0805. Still open and to report: R44 (no value), U6 COMP RC values, and the unverified values R45, R48, R49, C34, C35.
9. Final counts: footprints, tracks (must be 0), vias (must be 0), nets, unconnected (expected to be high; report the number).
10. File list with paths.

---

## 9. Done means

The task is done when all of these are true, and REPORT.md says so with the counts:
1. Every footprint in 3.2 is applied with the library name, or is listed as NOT DONE with a reason.
2. No footprint moved.
3. Every value in 3.1 is set, and the UNDECIDED items are unchanged and reported.
4. J7 is added and DNP. D6 and J2 are DNP.
5. Tracks = 0. Vias = 0.
6. Every net in section 5 that exists in the file is still present, and every pad's net was checked against section 4.
7. The planes are defined (In1.Cu GND, In2.Cu split power).
8. `sv16_board_netted.kicad_pcb` is saved, and REPORT.md is written.

Routing, DRC and release files are NOT part of this task.

---

## 10. Final message

Tell the user, in plain words:
- the output file name;
- the footprint changes applied and any that were not done;
- the track and via counts (both 0);
- the net count and the unconnected count (expected, not an error);
- which decisions you made by default and which the user must confirm;
- the parts still not in hand.
