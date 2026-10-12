# MASTER PROMPT: SV16 board. Apply footprint and value changes, then route, then DRC

You are an autonomous PCB engineering agent working in a local folder that contains the SV16 microcontroller board files. Your job is to take an UNROUTED KiCad PCB, apply the footprint and value changes the user has decided on, bring the board to a fully routed, DRC-clean state, and write a report. You do not have a human to ask during the run. When a decision is not in this document, use the default given here, mark it clearly in REPORT.md, and continue. Never stop partway without writing the report.

Read this whole prompt before you touch any file.

---

## 0. What the board is

- Project: SV16. A Lattice ECP5 LFE5U-12F-6TG144C FPGA board with a CH340G USB-UART bridge, two W25Q64JVSSIQ SPI flashes (U2 configuration flash, U3 firmware flash), an AP62300TWU-7 buck (U5, 3V3 output), an MP1584EN buck (U6, 1V1 output), an LP5907MFX-2.5 LDO (U7, 2V5 output), a USBLC6-2SC6 ESD device (U8), and a USB-C receptacle, barrel jack, JTAG, expansion headers, LEDs, reset/reconfigure switches and test points.
- Board size: 100 mm x 100 mm. Four mounting holes H1-H4, 3.2 mm, M3, 3 mm from the edges.
- Layer stack, 4 layers, 1.6 mm, 1 oz copper:
  - F.Cu: signal (top).
  - In1.Cu: solid GND plane.
  - In2.Cu: power plane. It carries the 3V3, 1V1 and 2V5 pours (split) and nothing else.
  - B.Cu: signal and ground (bottom).
  - NOTE: the uploaded file currently has In1.Cu and In2.Cu typed as "power" with no zones. You must make In1.Cu a solid GND zone and In2.Cu the split power zone described above.
- Minimum track and clearance for the fab: 0.2 mm / 0.2 mm. FPGA fan-out uses 0.25 mm signal traces and 0.2/0.4 mm vias.

The design is a DRAFT for a fabrication run. A board is only "done" when every acceptance check in section 9 passes.

---

## 1. Files you must read (all in the local folder)

Use the exact names below. If a file is missing, say so in REPORT.md and continue with what you have.

1. `<UNROUTED_FILE>`: the UNROUTED KiCad PCB the user added. This is your starting board. Its name is not yet fixed. Find it as the `.kicad_pcb` file that is NOT one of these three:
   - `sv16_board_placed_native.kicad_pcb` (old placement-only board, do not use)
   - `sv16_board_routed_draft.kicad_pcb` (old DRAFT routing, do not use, do not copy from it)
   - `rebuild/SBSV-16_rebuild_step1_values.kicad_pcb` (the value-only copy, used as a reference only, see section 3)
   If more than one candidate exists, pick the one with 0 tracks and 0 vias and a modification time newer than the rebuild copy, and state your choice in REPORT.md.
2. `rebuild/SV16_TODO_rebuild_step1.pdf`: the checklist. Sections A to G. Section G is the agent handoff. Treat it as the authoritative list of tasks.
3. `rebuild/SV16_BOM_rebuild_step1.pdf` and `rebuild/BOM_rebuild_step1.csv`: the parts list with bought/needed status for every reference designator.
4. `PCB_COMPONENTS.pdf` (the spec, 19 pages). Source for values, pinouts, net names and design rules. Section 3 has the component list. Section 4 has the pin-level connections. Section 7 has the layout rules. Section 10 has the corrections you must respect.
5. `rebuild/make_pdfs.py`: the script that generated the to-do and BOM PDFs. Read it if you need the exact text.
6. The schematic (`*.kicad_sch`), if present. It is the source of truth for net names and pin connections. If it is absent, record that in REPORT.md. Do not invent a netlist.

---

## 2. Hard rules (never break these)

1. Do NOT move any component. Keep every footprint at its current X/Y position and rotation, except where a footprint is replaced in place in KiCad (the new footprint keeps the reference's position). If a replaced footprint would sit on top of another part, stop and report the conflict instead of moving things.
2. Do NOT change pad numbers or net names, except for the net-name decisions in section 5.
3. Do NOT change schematic connectivity. Do not add or remove a connection except the two schematic fixes in section 6, which you can only record, not apply, if the schematic is not present.
4. Do NOT copy, merge or import ANY routing from these files: `sv16_board_routed_draft.kicad_pcb`, `routing_state.json`, `routing.kicad_pcb.txt`, `sv16_board_working.kicad_pcb`, `sv16_board_placed_native.kicad_pcb` (its tracks), or any `routing/` folder. The routing you produce must be new routing, made from the design rules in section 7.
5. Do NOT sacrifice power integrity to reach 100% connectivity. Do not drop a power route, a decoupling cap, or a ground return.
6. Do NOT lower clearances or trace widths below the values in section 7 to force routing. If you cannot route something at those values, leave it unrouted and report the net and the reason.
7. Do NOT guess values. Parts marked UNDECIDED in section 3.3 stay as they are, and you report them.
8. Do NOT delete a net to make the DRC pass.
9. Do NOT ignore DRC. Every DRC error must be fixed or listed in REPORT.md with the reason.
10. Do NOT generate Gerber, drill, BOM or position (pick-and-place) release files unless the acceptance checks in section 9 all pass. If they do not pass, do not generate them and say so.
11. Do NOT claim the board is finished, fabrication-ready or routed unless the DRC output supports it. Quote the DRC numbers.
12. Do NOT fabricate DRC results, file contents or part data. If a tool is missing (for example, `kicad-cli`), say so and report what you could and could not check.

---

## 3. Parts and values

### 3.1 Current state of the uploaded file

`rebuild/SBSV-16_rebuild_step1_values.kicad_pcb` is a copy of the uploaded board with 37 Value fields changed to the spec values. It has 141 footprints, the same positions as the original, and the same old tracks and vias (1,783 segments, 179 vias) that you must delete. Its 37 value changes are:

- Q2: BC817 -> MMBT3904 (SOT-23, same pinout per the spec)
- Q4: BC807 -> MMBT3906 (SOT-23, same pinout per the spec)
- C36, C37: 100 nF -> 22 pF
- R1, R13, R14, R15, R16, R17, R18, R19, R26, R32: 10k
- R2, R3, R4, R5, R25: 4.7k
- R6, R7, R8, R31, R33, R34: 1k
- R9, R10, R11, R12: 100R (100 ohm)
- R21, R22, R23, R24: 0R (0 ohm)
- R27, R28, R29, R30: 470R
- R36, R37: 5.1k
- R38: 12.4k
- R39, R46: 33k
- R40, R41, R43: 100k
- R47: 10k

Check each one in the unrouted file. If the unrouted file does not have a value set, set it. Record in REPORT.md which ones were already set.

### 3.2 Footprint changes to apply (current -> new)

Verify each KiCad library name exists in the local library before you use it. If a name does not exist, stop on that item, record it in REPORT.md, and continue with the rest.

| Ref | Current footprint | New footprint (KiCad library name) | Reason |
|---|---|---|---|
| C25 | Capacitor_SMD:C_0805_2012Metric | Capacitor_SMD:CP_Elec_4x5.4 | 10 uF electrolytic (decision, bought) |
| C30 | Capacitor_SMD:C_0805_2012Metric | Capacitor_SMD:CP_Elec_4x5.4 | 10 uF electrolytic (decision, bought) |
| C32 | Capacitor_SMD:C_0805_2012Metric | Capacitor_SMD:C_0603_1608Metric | 470 nF in 0603, as bought |
| C36 | Capacitor_SMD:C_0603_1608Metric | Capacitor_SMD:C_0805_2012Metric | 22 pF C0G 0805 bought (Yageo CC0805JRNPO9BN220) |
| C37 | Capacitor_SMD:C_0603_1608Metric | Capacitor_SMD:C_0805_2012Metric | same as C36 |
| R5 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_0805_2012Metric | 4.7k 0805 pack bought |
| R25 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_0805_2012Metric | 4.7k 0805 pack bought |
| R6 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_1206_3216Metric | 1k 1206 pack bought |
| R7 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_1206_3216Metric | 1k 1206 pack bought |
| R8 | Resistor_SMD:R_0603_1608Metric | Resistor_SMD:R_1206_3216Metric | 1k 1206 pack bought |
| R9 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0805_2012Metric | 100R 0805 pack bought |
| R10 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0805_2012Metric | same |
| R11 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0805_2012Metric | same |
| R12 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0805_2012Metric | same |
| R47 | Resistor_SMD:R_1206_3216Metric | Resistor_SMD:R_0603_1608Metric | 10k 1% 0603 to buy (Yageo RC0603FR-0710KL) |
| Y2 | Crystal:Crystal_HC49-4H_Vertical | Crystal:Crystal_SMD_HC49-SD (verify name; or the footprint matching the bought SMD HC49/U 12 MHz crystal) | 12 MHz SMD crystal to buy |
| L1 | Inductor_SMD:L_Sunlord_SWPA6045S | Inductor_SMD:L_Sunlord_MWSA0518_5.4x5.2mm (verify pads against the bought CD54 10 uH datasheet) | spec footprint |
| L2 | Inductor_SMD:L_Sunlord_SWPA6045S | Inductor_SMD:L_Sunlord_MWSA0518_5.4x5.2mm (same as L1) | spec footprint |
| R21 | Resistor_SMD:R_0603_1608Metric | Solder-bridge pad footprint, or R_0603 with 0R (see 3.4) | no 0R bought |
| R22 | Resistor_SMD:R_0603_1608Metric | same as R21 | |
| R23 | Resistor_SMD:R_0603_1608Metric | same as R21 | |
| R24 | Resistor_SMD:R_0603_1608Metric | same as R21 | |
| FB1 | Inductor_SMD:L_0603_1608Metric | keep the 0603 footprint if a ferrite is bought; otherwise solder-bridge pads (see 3.4) | no ferrite bought |

No change needed (already the right footprint): C21 (CP_EIA-7343-31 tantalum), C22 (CP_Elec_6.3x5.4), C23 (CP_Elec_8x10.5), C24 (CP_Elec_8x10.5), C39 (CP_Elec_4x5.4), C40 and C41 (CP_Elec_6.3x5.4), C42 (CP_Elec_4x5.4), R1 and the other 10k 0603 resistors, R2 to R4 and R27 to R30 and R36 to R37 (0805), R31, R33, R34 and R39, R46, R49 (1206), R38 (0402), R40, R41, R43, R44, R45, R48 (0603). J8 USB-C HRO TYPE-C-31-M-12 is correct. J9 barrel jack is correct.

### 3.3 Other board changes

- ADD J7: Connector_PinHeader_2.54mm:PinHeader_2x25_P2.54mm_Vertical, NOT FITTED (spec: footprint only). It has no net connections except as the spec says.
- D6 (red LED, INITN indicator): mark as DNP (spec: do not fit by default). Keep the footprint.
- The headers are standard 2.54 mm straight male headers. Their footprints are already correct. J2 is 1.27 mm 2x5; the spec allows leaving it unpopulated and using J1. Mark J2 DNP. J6 is keyed: add a keying notch to its silkscreen, or flag it.
- Values UNDECIDED. Leave as is and report them: R44 (no spec value), R45 (100k, not in spec), R48 and R49 (the AP62300 EN divider from VM_IN; board has 100k and 33k; the spec gives no values; confirm against the AP62300 datasheet, do not change), C34 (100 nF, not in spec), C35 (100 pF, not in spec).
- C39, C40, C41, C42 stay ELECTROLYTIC. This is the user's decision. Do not change them to ceramic.
- C23 is 470 uF 16 V on a 12 V input. This is a known derating (1.33x). Keep it. Report it.

### 3.4 Solder-bridge pads

Where the spec part is not bought and the function is a 0 ohm link or a ferrite, use a two-pad solder bridge. Use a 0603-sized pad pair with a jumper (for example, a KiCad "SolderJumper" footprint, if present, or two pads with a short track). Do not short two different nets with it. Record each one in REPORT.md, with the net names on each side.

### 3.5 Parts that are not yet bought (do not place anything that depends on them as final)

These parts are needed to build the board but do not block routing:
- U1 FPGA LFE5U-12F-6TG144C (not bought)
- U3 second W25Q64JVSSIQ (1 of 2 bought)
- Y1 YIC OSC25M-3.3I/S3-25T (active, 4-SMD 3.2x2.5 mm). Buy, not yet in hand.
- Y2 12 MHz SMD HC49/U crystal (not bought)
- D8, D9, D11 third SS34 (2 of 3 bought)
- Resistors: 10k 0603 (Yageo RC0603JR-0710KL, 11 pieces); R47 10k 0603 1% (Yageo RC0603FR-0710KL)
- Caps: 22 pF 0805 C0G (Yageo CC0805JRNPO9BN220), 2 pieces
- Barrel jack J9, SW1, SW2, JP1 shunt, headers: the user says these are already owned, to be confirmed.
Report these in REPORT.md as "not yet in hand" where relevant. The full BOM with status is in `BOM_rebuild_step1.csv`.

---

## 4. Components and nets: what must connect to what

The spec (`PCB_COMPONENTS.pdf`) section 4 gives the pin-level connections for U1, U2, U3, and the other ICs. Use the spec as the reference. Key points you must respect:

- U1 power pins: 1V1 on pins 20, 29, 38, 66, 83, 130; 2V5 on pins 17, 53, 96, 132; 3V3 on pins 9, 16, 36, 43, 70, 86, 100, 122, 137; GND on pins 8, 15, 21, 32, 42, 65, 75, 85, 87, 101, 123, 129, 131, 138; NC on pins 109, 144. Each GND pin gets its own via to the GND plane.
- U1 configuration: CCLK (pin 54) through R9 100R to U2.6 (CLK), and through R8 1k to 3V3. Master-SPI: pin 46 (MISO) through R11 to U2.2 (DO); pin 47 (MOSI) through R10 to U2.5 (DI); pin 49 (CSSPIN) through R12 to U2.1 (/CS). Pin 51 unused.
- PROGRAMN (pin 57): R2 4.7k to 3V3, SW2 to GND, J1 pin 4, Q1 drain.
- INITN (pin 55): R3 4.7k to 3V3, J1 pin 10, R31 1k to Q4 base.
- DONE (pin 56): R4 4.7k to 3V3, J1 pin 9, R32 10k to Q2 base.
- CFG_0 (pin 62) to R6 1k to GND. CFG_1 (pin 59) to R5 4.7k to 3V3. CFG_2 (pin 58) to R7 1k to GND.
- TCK, TMS, TDI, TDO (pins 63, 64, 61, 60): J1 pins 8, 6, 3, 2, and J2 pins 5, 2, 3, 4.
- clk_25m (pin 133): from Y1 pin OUT (the 25 MHz oscillator output).
- ext_rst_n (pin 134): SW1, R1 10k to 3V3, C1 100 nF to GND.
- uart_rx, uart_tx (pins 73, 74): to U4 (CH340G) or J10, through R21 to R24.
- flash_sck, flash_cs_n, flash_mosi, flash_miso (pins 110, 111, 112, 113): to U3 pins 6, 1, 5, 2.
- spi0_sck, spi0_cs_n, spi0_mosi, spi0_miso (pins 114 to 117): to J3 pins 12, 11, 13, 14.
- led[0..3] (pins 39, 40, 41, 44): through R27 to R30 (470R) to D2 to D5, to 3V3 (active low).
- gpio_a[0..7] (pins 45 to 52): J5 pins 1 to 8. gpio_a[8..15] (pins 97 to 99, 104 to 108): J3 pins 3 to 10. gpio_b[0..15]: J4 pins 3 to 18.
- pwm_out, motor_dir1, motor_dir2, motor_fault_n (pins 88, 89, 102, 103): J6 pins 3 to 6.

For the full 144-pin map, the spec points to `board/TQFP144_PINOUT.md`. It may not be in the folder. If it is not, use the pin numbers above and the LPF names, and say so in REPORT.md.

Power and regulators (spec section 3 and 4.x):
- U5 AP62300TWU-7 (SOT-23-6 / TSOT-26): synchronous buck, VIN from VM_IN, output 3V3 via L1 (10 uH CD54). FB (pin 4) must be connected to 3V3 (spec correction 1). R46 33k and R47 10k form the feedback divider (3.28 V). R48 and R49 are the EN divider from VM_IN (values UNDECIDED, see 3.3). C38 100 nF on BST. C39 (electrolytic), C40 and C41 (electrolytic) on the input and output.
- U6 MP1584EN-LF-Z (SOIC-8 with exposed pad = GND): non-synchronous buck, output 1V1 via L2 (10 uH CD54), catch diode D11 (SS34). R38 12.4k top and R39 33k bottom set the output (1.10 V). R40 100k sets the frequency (FREQ to GND). R41 100k and C31 470 nF set the EN delay. C33 100 nF on BST. The COMP pin needs an RC network to GND for stability (spec correction 3). Use the COMP pin number from the MP1584 datasheet, not from memory. Its values are not given in the spec. Mark the COMP RC as UNDECIDED and do not guess values. The net `U6_COMP_RC` already exists in the file; connect it there and report that the values are missing.
- U7 LP5907MFX-2.5 (SOT-23-5): LDO, 3V3 in, 2V5 out. C30 (10 uF) on the input, C42 (10 uF electrolytic) on the output. R43 100k 3V3 to EN, C32 470 nF EN to GND for the delay.
- The 2V5 rail goes to U1 pins 17, 53, 96, 132. The 1V1 rail to U1 pins 20, 29, 38, 66, 83, 130.
- VM_IN: from J9 barrel jack, with FB1 (600R ferrite, or a solder bridge), D8 and D9 (SS34) for the input OR with the USB VBUS. VM_IN also feeds J6 pin 1.
- U8 USBLC6-2SC6: ESD on USB_DP and USB_DN, VBUS clamp.

If the schematic is present, it overrides this list. Record every difference in REPORT.md.

---

## 5. Net-name decisions

The board uses some net names that differ from the spec. The user has NOT yet decided these. Use the default below, apply it consistently, and list it in REPORT.md as a decision the user must confirm.

| Item | Board currently uses | Spec uses | DEFAULT to apply |
|---|---|---|---|
| USB data pair | USB_DP, USB_DN | USB_D+, USB_D- | Keep USB_DP and USB_DN (the names already in the file) |
| 5 V rail | 5V_USB | 5V (J3 and J4 pins 17, 18) | Keep 5V_USB |

Do not rename any other net. The file already contains these nets: clk_25m, ext_rst_n, uart_rx, uart_tx, flash_sck, flash_cs_n, flash_mosi, flash_miso, spi0_sck, spi0_cs_n, spi0_mosi, spi0_miso, VM_IN, 3V3, 2V5, 1V1, GND, CCLK, DONE, INITN, PROGRAMN, TCK, TMS, TDI, TDO, U2_CLK, U2_CS, U2_DI, U2_DO, U2_HOLD, U2_WP, U3_HOLD, U3_WP, U4_DTR, U4_RXD, U4_TXD, U4_V3, U5_BST, U5_EN, U5_FB, U5_SW, U6_BST, U6_COMP, U6_COMP_RC, U6_EN, U6_FREQ, U6_SW, U7_EN, Y2_XI, Y2_XO, led0 to led3 (with _k variants), motor_dir1, motor_dir2, motor_fault_n, pwm_out, A0 to A15, B0 to B15, CC1, CC2, CFG_0, CFG_1, CFG_2, D1_A, D6_K, D7_A, DTR_F, FB_1V1, J9_VIN, J10_RX, J10_TX, Q1_G, Q2_B, Q2_C, Q4_B, Q4_C, USB_DN_F, USB_DP_F, USB_VBUS, VM_IN_RAW.

Note: nets A0 to A15 and B0 to B15 are the EXP-C and EXP-B header nets. Do not confuse them with the FPGA pin names.

Important: the file may contain more or fewer nets than this list. Run a check and report any net that is not in this list.

---

## 6. Schematic-level fixes (must be recorded, cannot be fixed in the PCB file alone)

These come from the spec section 10 corrections. Apply them only if the schematic is present and you can edit it safely. Otherwise, record them as open items in REPORT.md.

1. U5 (AP62300) pin 4 (FB) must be connected to 3V3. The earlier sheet left it floating. Connect `U5_FB` to `3V3`.
2. U6 (MP1584) needs a COMP RC network to GND. Values are not in the spec. Mark UNDECIDED. Report it.
3. Oscillator Y1 pinout: confirm pad 1 to 4 against the YIC datasheet. The spec lists VCC, GND, OUT, EN. The clock output must go to pin 133 (`clk_25m`). Do not route `clk_25m` until Y1's pinout is confirmed, or route it and flag it in REPORT.md.

---

## 7. Layout and design rules (from spec section 7). Use these as the KiCad design rules.

Board and stackup:
- 100 x 100 mm. Four mounting holes H1-H4, M3, 3 mm from the edges. Keep their keep-outs.
- 4 layers as in section 0. In1.Cu is a solid GND zone. In2.Cu is the split power zone (3V3, 1V1, 2V5 pours). Both zones must be filled.

Track widths and clearances:
- Default signal track width: 0.25 mm.
- Power tracks: 3V3, 1V1, 2V5: 0.8 mm. VM_IN: 1.5 mm. Or use the inner power planes for these rails.
- Switching nodes (U5 SW/OUT to L1, U6 SW to L2, and the catch-diode loops): 0.8 mm, as short as possible.
- Clearance: 0.2 mm minimum everywhere. 0.5 mm between switching nets and any JTAG or flash net.
- Differential pair USB_DP / USB_DN: 90 ohm, 0.2 mm gap, length matched within 0.5 mm.
- Vias: 0.2 mm drill, 0.4 mm pad. Power vias 0.3 mm drill, 0.6 mm pad.

Placement-related routing rules (do not move parts; route to these constraints):
- FPGA decoupling caps C2 to C20 within 3 mm of their matching pin, on the same side, with the via first at the pad.
- Each FPGA GND pin gets its own via to the GND plane. Thermal vias under the FPGA body.
- Oscillator Y1 is within 10 mm of FPGA pin 133. No via in the clock trace. A ground pour under Y1. Y1 is at least 5 mm from the switching nodes.
- Config flash U2 is within 15 mm of FPGA pins 46, 47, 49, 54. R9 to R12 at the FPGA end.
- Motor return: J6 GND returns to the C23 area on its own path, never through the FPGA ground.
- Keep-out: no copper pour under the USB-C shield pads or under the barrel jack body.
- Test points TP1 to TP6 on the top side, with their net names in silkscreen (3V3, 2V5, 1V1, GND, DONE, INITN).
- Silkscreen: name the headers J1 (JTAG), J3 (EXP-A), J4 (EXP-B), J5 (EXP-C), J6 (MOTOR), J10 (CONSOLE). Mark "5V only" at J3 and J4 pins 17 and 18. Mark "CFG FLASH - INPUTS ONLY" at J5 pins 2, 3, 5 and 7.

Net classes (set these in KiCad's net class manager):
- Power: VM_IN, 3V3, 1V1, 2V5 (wide tracks, pours, regulator loops).
- Switching: U5 OUT/L1 node, U6 SW, BST nodes. Short, fat, away from the oscillator and flash.
- USB: USB_DP, USB_DN (90 ohm differential).
- JTAG: TCK, TMS, TDI, TDO, PROGRAMN, INITN, DONE, CCLK (short stubs, series resistors at the FPGA end).
- Default: everything else (0.25 mm).

---

## 8. Steps (do them in this order and log each one)

Step 0. Set up. Create a folder `agent_work/` in the local folder. Keep a `WORKLOG.md` with a line for every step: what you did, the time, and the result. Keep backups of the original unrouted file as `agent_work/backup_<UNROUTED_FILE>`.

Step 1. Inventory. Identify `<UNROUTED_FILE>` using the rule in section 1. Count the footprints, tracks, vias, zones, nets, and check the layer list. Record the counts in WORKLOG.md. Confirm the unrouted file has 0 tracks and 0 vias. If it has tracks or vias, that is the old routing: delete them in step 4.

Step 2. Check against the to-do. For each item in sections A to G of the to-do PDF and in section 3 of this prompt, record in WORKLOG.md whether it is already applied in the unrouted file. Values: compare with section 3.1. Footprints: compare with section 3.2.

Step 3. Apply footprint changes (section 3.2) and value changes not already set (section 3.1). Replace each footprint in place, keeping the reference, position and rotation. Check that no footprint moved. Apply section 3.3 (J7, D6 DNP, J2 DNP, the J6 keying note). Record every change with before and after in WORKLOG.md.

Step 4. Strip routing. Delete all tracks and vias from the board. Do not delete footprints, zones, graphic lines or text. Confirm 0 tracks and 0 vias. Do NOT import any routing from the old files.

Step 5. Set up the board. Set the stackup (section 0). Set In1.Cu as a solid GND zone (net GND). Set In2.Cu as the power zone with 3V3, 1V1 and 2V5 pours. Set the net classes (section 7). Set the design rules (section 7). Set the Edge.Cuts board outline 100 x 100 mm if it is not already. Keep the four mounting holes.

Step 6. Net-name decisions. Apply the defaults in section 5. Compare the net list with the schematic if present, and with section 4. Report every difference.

Step 7. Schematic-level fixes (section 6). Apply them if the schematic is present. Otherwise record them as open.

Step 8. Y1 check. Confirm the pinout of the YIC OSC25M-3.3I/S3-25T against the datasheet and map pads 1 to 4. If the footprint pads do not match the YIC part, record it and do not route `clk_25m` until it is fixed.

Step 9. Routing order. Route in this order, checking DRC after each group:
  a. Power and ground: VM_IN, 3V3, 1V1, 2V5, and GND. Use the planes for GND and the power pours. Route the regulator loops (U5, U6, U7) first, with the switching node short and fat.
  b. FPGA power and decoupling vias (one via per GND pin to the GND plane).
  c. USB pair USB_DP / USB_DN, 90 ohm, length matched within 0.5 mm, ESD device U8 close to the connector J8.
  d. Y1 clock (`clk_25m`) with the rules in section 7 (no via in the clock trace, ground pour under Y1).
  e. Config flash (U2, U3) and the Master-SPI nets (R9 to R12, 100R).
  f. JTAG, PROGRAMN, INITN, DONE, CCLK, TCK, TMS, TDI, TDO.
  g. UART (uart_rx, uart_tx, U4, J10), the CH340G (Y2 at 12 MHz, C36 and C37 at 22 pF).
  h. Everything else: GPIO, LEDs, expansion headers, motor interface, reset, test points.
  Do NOT route a net by widening clearances. If a net fails, record it in REPORT.md and move on.

Step 10. Zones. Fill all zones. Confirm each zone is filled. Check that copper is kept out from under the USB shield pads and the barrel jack body.

Step 11. DRC. Run KiCad's design rule check. If `kicad-cli` is available, use `kicad-cli pcb drc`. Save the JSON or text output to `agent_work/drc_report.json` (or .txt). Record in REPORT.md: the number of unconnected items, shorts, clearance errors, edge errors, courtyard errors, silkscreen errors, and whether all zones are filled. Fix every error. Re-run DRC until the counts are zero or each remaining item has a documented reason.

Step 12. Write outputs. Save the routed board as `sv16_board_revA.kicad_pcb` in the local folder. Write `REPORT.md` (section 10). If and only if the acceptance checks in section 9 all pass, generate the release files (Gerber, drill, BOM, position). Otherwise, do not.

---

## 9. Acceptance checks (all must pass for the board to count as done)

1. Footprints: every footprint from section 3.2 is applied with the new library name. J7 is added (not fitted). D6 and J2 are DNP. No footprint moved from its original position.
2. Values: every value in section 3.1 is set. The UNDECIDED items (R44, R45, R48, R49, C34, C35) are unchanged and reported.
3. Routing: 0 tracks and 0 vias from the old routing. Every net in the board is connected. DRC reports 0 unconnected items.
4. DRC: 0 shorts, 0 clearance errors, 0 edge errors, 0 courtyard errors, 0 silkscreen errors. All zones filled. If any error remains, it is listed in REPORT.md with the reason and is not hidden.
5. Power: VM_IN, 3V3, 1V1 and 2V5 are routed with the widths in section 7 or on the planes. The decoupling caps are placed as in section 7.
6. Clock: Y1 pinout confirmed against the datasheet. `clk_25m` routed to pin 133 within the rules.
7. USB: USB_DP and USB_DN routed as a 90 ohm pair with 0.2 mm gap and length matched within 0.5 mm.
8. Nets: no net was deleted. Every net name is either the original or the decision in section 5.
9. Routing source: no routing was copied from the old files.
10. Report: REPORT.md is complete, and every item in sections A to G of the to-do PDF is either done or listed as not done.

If any of 1 to 10 is not met, the board is NOT done. Say so in REPORT.md and in your final message. Do not generate release files.

---

## 10. REPORT.md (required content)

Write REPORT.md with these sections, in this order:

1. Summary. One paragraph: the input file used, the output file, whether the board passes all acceptance checks, and the one biggest open issue.
2. Input inventory. The file names used, the counts (footprints, tracks, vias, zones, nets), and the choice of unrouted file if more than one candidate existed.
3. Footprint changes. Table: reference, old footprint, new footprint, status (done, failed, not done) and reason.
4. Value changes. Table: reference, old value, new value, status, reason. Include the UNDECIDED items left unchanged.
5. Net-name decisions. The defaults used (section 5), and the differences found against the schematic or the spec.
6. Schematic-level items. Done, or open, for each item in section 6.
7. Y1 check. The pinout result and what was mapped.
8. Routing summary. Number of nets routed, nets not routed (with the reason for each), the length-matched USB pair result, and the routing order used.
9. DRC summary. The counts from section 8 step 11, copied from the DRC output file.
10. Open decisions for the user. Each one, with the default that was used:
    - C39 to C42: electrolytic (user decision, already applied).
    - R44, R45, R48, R49, C34, C35: values not decided.
    - U6 COMP RC values not in the spec.
    - USB and 5 V net names (defaults applied).
    - C23 voltage rating (16 V on 12 V input, derated 1.33x, kept).
    - Parts not yet in hand: FPGA, second W25Q64, active oscillator Y1, 12 MHz crystal Y2, third SS34, 10k resistors, 22 pF caps.
11. Release status. Whether release files were generated, and why or why not.
12. File list. Every file written, with its path.

---

## 11. Final message

When finished, your final message must say, in plain words:
- whether `sv16_board_revA.kicad_pcb` passes all acceptance checks in section 9;
- the DRC counts;
- the number of nets routed and the nets left unrouted, if any;
- which decisions you made by default and which the user must confirm;
- that the board is NOT ready for fabrication while the parts in section 3.5 are not in hand and any section 9 check is failing.

Do not describe the board as complete unless section 9 is fully met.
