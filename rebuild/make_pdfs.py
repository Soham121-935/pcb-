import csv
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

OUT='/home/user/pcb-/rebuild/'
ss=getSampleStyleSheet()
H1=ss['Heading1']; H2=ss['Heading2']
body=ParagraphStyle('b',parent=ss['BodyText'],fontSize=9,leading=11.5)
cell=ParagraphStyle('c',parent=ss['BodyText'],fontSize=7.5,leading=9)
cellb=ParagraphStyle('cb',parent=cell,fontName='Helvetica-Bold')

def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

# ---------- BOM PDF ----------
rows=list(csv.reader(open(OUT+'BOM_rebuild_step1.csv',encoding='utf-8')))
hdr=rows[0]; data=rows[1:]
doc=SimpleDocTemplate(OUT+'SV16_BOM_rebuild_step1.pdf',pagesize=landscape(A4),
    leftMargin=10*mm,rightMargin=10*mm,topMargin=10*mm,bottomMargin=10*mm,
    title='SV16 BOM - rebuild step 1')
els=[Paragraph('SV16 BOM - rebuild step 1 (value-level changes applied)',H1),
     Paragraph('Source: SBSV-16.kicad_pcb (uploaded), PCB_COMPONENTS.pdf (spec), cart screenshots. '
               'Status column: BUY = not in cart, OK = covered by cart, UNDECIDED = needs a decision, '
               'PENDING = PCB footprint/value change still to do. Shared parts are listed once in the cart column.',body),
     Spacer(1,4*mm)]
t=[[Paragraph(esc(h),cellb) for h in hdr]]
for r in data:
    t.append([Paragraph(esc(c),cell) for c in r])
widths=[22,58,52,50,48,56]
tbl=Table(t,colWidths=[w*mm for w in widths],repeatRows=1)
st=[('GRID',(0,0),(-1,-1),0.3,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dde6f0')),
    ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2)]
for i,r in enumerate(data,1):
    s=r[-1].upper()
    if s.startswith('BUY'): st.append(('BACKGROUND',(0,i),(-1,i),colors.HexColor('#fde2e2')))
    elif 'UNDECIDED' in s or 'PENDING' in s or 'ADD' in s or 'CHANGE' in s: st.append(('BACKGROUND',(0,i),(-1,i),colors.HexColor('#fff4cc')))
tbl.setStyle(TableStyle(st))
els.append(tbl)
doc.build(els)

# ---------- TO-DO PDF ----------
todo=[
 ('A. Footprint changes in KiCad (Footprint Editor / Change Footprint)', [
  'C25, C30: change footprint from C_0805 (ceramic) to CP_Elec_4x5.4 (electrolytic), value 10 uF 35 V.',
  'C32: change footprint from C_0805 to C_0603 (470 nF, spec: 0603).',
  'R9, R10, R11, R12 (100 ohm): change footprint from R_1206 to R_0805 (bought 100 ohm pack is 0805).',
  'L1, L2 (10 uH CD54): footprint is L_Sunlord_SWPA6045S. Spec says L_Sunlord_MWSA0518 (5.4x5.2 mm). Confirm the footprint against the bought part datasheet and update.',
  'J7 (2x25 spare header): add footprint Connector_PinHeader_2.54mm:PinHeader_2x25_P2.54mm_Vertical, mark DNP / not fitted.',
  'D6 (red LED, INITN): mark DNP (spec: do not fit by default).',
  'FB1 (600 ohm ferrite, 0603): no ferrite bought. Either buy one, or replace the footprint with a solder bridge (0 ohm jumper pads).',
  'R21, R22, R23, R24 (0 ohm): no 0 ohm bought. Use solder-bridge pads. Spec: populate one pair only (R21/R23 OR R22/R24).',
  'R5 and R25 (4.7k): change footprint from R_0603 to R_0805, and use the 4.7k 0805 pack you bought.',
  'R6, R7, R8 (1k): change footprint from R_0603 to R_1206, and use the 1k 1206 pack you bought.',
  'Y2 (12 MHz): change footprint from Crystal_HC49-4H (through-hole) to the SMD HC49/US footprint for the bought 12 MHz surface-mount crystal (2-pin, passive, OK for CH340G).',
  'C36, C37 (22 pF): change footprint from C_0603 to C_0805, to match the YAGEO CC0805JRNPO9BN220 (22 pF C0G 0805 50 V 5%) you are buying.',
  'R47 (10k, 1%): change footprint from R_1206 to R_0603, and buy the 1% 0603 part (YAGEO RC0603FR-0710KL).',
 ]),
 ('B. Value decisions still open (you decide, then set the value in KiCad)', [
  'R44: no value in spec. Set the value, or leave DNP.',
  'R45: 100k on board, not in spec. Keep or remove.',
  'R48, R49: AP62300 EN divider from VM_IN. Spec gives no values. Board has 100k (R48) and 33k (R49). Confirm against the AP62300 datasheet.',
  'C34: 100 nF on board, not in spec. Keep or remove.',
  'C35: 100 pF on board, not in spec. Keep or remove.',
 ]),
 ('C. Values already changed in the step-1 copy (verify in KiCad)', [
  'Q2: BC817 changed to MMBT3904. Q4: BC807 changed to MMBT3906 (SOT-23, same pinout per spec).',
  'C36, C37: 100 nF changed to 22 pF (CH340G crystal load caps, spec).',
  'Resistors: values set per spec (see BOM). R1, R13-R19, R26, R32, R47 = 10k; R2-R5, R25 = 4.7k; R6-R8, R31, R33, R34 = 1k; R9-R12 = 100 ohm; R27-R30 = 470 ohm; R36, R37 = 5.1k; R38 = 12.4k; R39, R46 = 33k; R40, R41, R43 = 100k.',
  'Check the file opens with all 141 footprints and that the tracks are unchanged (this copy was checked: 141 footprints, 1,783 segments, 179 vias).',
 ]),
 ('D. Schematic / design checks from the spec (must be fixed in the schematic)', [
  'U5 (AP62300) pin 4 (FB) must be connected to 3V3. Spec says the earlier sheet left it floating.',
  'U6 (MP1584): add the COMP RC compensation network, values from the datasheet.',
  'U6 feedback divider: R38 = 12.4k top, R39 = 33k bottom (already set). Keep R39 below 40k.',
  'C23 (470 uF 16 V) on a 12 V input: 16 V is 1.33x derated. Consider a 25-35 V part if you can still change the order.',
  'Oscillator Y1: active 25 MHz XO (spec). Confirm the pinout (VCC, GND, OUT, EN) against the bought part before routing.',
  'Y2 (12 MHz): check the footprint against the bought crystal (HC49-4H vs 3225 SMD).',
  'LP5907 output cap (C42): electrolytic is used here, spec wants low-ESR ceramic. Check stability on the bench.',
 ]),
 ('E. Purchases still needed (not in any cart screenshot)', [
  'U1: FPGA LFE5U-12F-6TG144C (not bought).',
  'U3: 1 more W25Q64JVSSIQ (you have 1, need 2).',
  'Y1: active 25 MHz XO 3.2x2.5 4-pad (YIC OSC25M-3.3I/S3-25T or equivalent). The 3 bought 2-pin 25 MHz crystals cannot be used here.',
  'Y2: 12 MHz SMD crystal HC49/U (surface mount, 2-pin). To buy. Footprint change needed (see A).',
  'D8/D9/D11: 1 more SS34 (you have 2, need 3).',
  '10k 0603 5% resistors: YAGEO RC0603JR-0710KL, 11 pieces (R1, R13-R19, R26, R32). To buy.',
  '10k 0603 1% resistor: YAGEO RC0603FR-0710KL (1%, 0603), 1 piece for R47. To buy. Use this 1% part, not the 5% RC0603JR part, because the spec asks for 1%.',
  '22 pF 0805 C0G caps: YAGEO CC0805JRNPO9BN220 (22 pF, 50 V, 0805, 5%), 2 pieces (C36, C37). To buy.',
  '4.7k (R5, R25) and 1k (R6-R8): use the 0805 and 1206 packs you already bought, with the footprint changes in section A. No purchase needed.',
  'Headers: use the most available part, standard 2.54 mm straight male pin headers (1x10, 2x10, 1x6, 1x4, 1x2). Footprints on the board already match, so no change. J2 (1.27 mm 2x5) left unpopulated per spec. J6 keyed: add keying notch or use a shrouded header.',
  'Connectors and switches (barrel jack J9, SW1/SW2, JP1 shunt): you already have these. Not in the cart screenshots, so confirm the parts and footprints match the board.',
 ]),
 ('G. Agent handoff (for whoever makes the PCB changes)', [
  'Starting file: rebuild/SBSV-16_rebuild_step1_values.kicad_pcb. It has the same 141 footprints, positions and 4-layer stackup as SBSV-16.kicad_pcb, with 37 values changed. Do not move components. Do not change pad numbers or net names without the decision in G3.',
  'G1 Exact KiCad footprint names (verify each exists in your library before use): Y1 current Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm. Bought part is YIC OSC25M-3.3I/S3-25T, a 4-SMD 3.2x2.5 mm XO. Check pad pitch against the YIC datasheet and keep this footprint only if the pads match. Y2 change to Crystal:Crystal_SMD_HC49-SD (or the footprint for the bought SMD HC49/U crystal). L1, L2 change to Inductor_SMD:L_Sunlord_MWSA0518_5.4x5.2mm (name from spec; confirm pads against the bought CD54 datasheet). C25, C30 Capacitor_SMD:CP_Elec_4x5.4. C32 Capacitor_SMD:C_0603_1608Metric. C36, C37 Capacitor_SMD:C_0805_2012Metric. R5, R25 Resistor_SMD:R_0805_2012Metric. R6, R7, R8 Resistor_SMD:R_1206_3216Metric. R9-R12 Resistor_SMD:R_0805_2012Metric. R47 Resistor_SMD:R_0603_1608Metric. R21-R24 solder-bridge pads (or R_0603 footprint with 0 ohm). J7 Connector_PinHeader_2.54mm:PinHeader_2x25_P2.54mm_Vertical, not fitted. D6 mark DNP.',
  'G2 Y1 pinout: the bought part has 4 pads (VCC, GND, OUT, EN per spec). The YIC pin numbers are not in the search results. Check the YIC datasheet and map pad 1-4 before routing. Lead time: DigiKey lists 26 weeks, so check stock before finalising the design.',
  'G3 Net-name decisions (choose one per row before routing): USB pair: board uses USB_DP/USB_DN, spec uses USB_D+/USB_D-. Recommended: keep spec names. 5 V rail: board uses 5V_USB, spec uses 5V (J3/J4 pins 17/18). Recommended: keep 5V_USB and note it in silkscreen. All other spec nets (clk_25m, ext_rst_n, uart_rx/tx, flash_*, spi0_*, VM_IN, 3V3, 2V5, 1V1, GND) are already in the file.',
  'G4 Design rules (spec section 7): signal track 0.25 mm; 3V3, 1V1, 2V5 power tracks 0.8 mm; VM_IN 1.5 mm; switching nodes (U5 OUT-L1, U6 SW-L2) 0.8 mm and short. Clearance 0.2 mm minimum, 0.5 mm between switching nets and JTAG/flash nets. Vias 0.2 mm drill / 0.4 mm pad; power vias 0.3 / 0.6 mm. USB_D+/USB_D- 90 ohm differential, 0.2 mm gap, length matched within 0.5 mm. FPGA decoupling caps C2-C20 within 3 mm of their pin, via first at the pad. Each FPGA GND pin gets its own via to the GND plane. Y1 within 10 mm of pin 133, no via in the clock trace, ground pour under it, 5 mm or more from switching nodes. U2 within 15 mm of FPGA pins 46/47/49/54; R9-R12 at the FPGA end. J6 GND return separate from FPGA ground. No copper pour under USB-C shield pads or barrel jack body. TP1-TP6 on top side.',
  'G5 Strip the old routing first: the uploaded file still has 1,783 tracks and 179 vias from the old routing. Delete all tracks and vias in KiCad (select all, filter to tracks and vias, delete). Keep every footprint in place. Do not merge or copy old routing (routing_state.json, routing.kicad_pcb.txt, sv16_board_working.kicad_pcb). Confirm the board then shows 0 tracks and 0 vias and all nets unconnected.',
  'G6 Acceptance: after routing, DRC shows 0 unconnected, 0 shorts, 0 clearance, 0 edge and courtyard errors. Zones filled. Only then generate Gerber, drill, BOM and position files.',
 ]),
 ('F. Routing and checks (after A-D are done)', [
  'Re-route the board from the updated placement. Tracks in this file are not verified.',
  'Run DRC: 0 unconnected, 0 shorts, 0 clearance, 0 edge or courtyard errors. Zones filled.',
  'Only after clean DRC: generate Gerber, drill, BOM and position files.',
  'Do not send the board to fabrication until all of the above are done.',
 ]),
]
doc2=SimpleDocTemplate(OUT+'SV16_TODO_rebuild_step1.pdf',pagesize=A4,
    leftMargin=15*mm,rightMargin=15*mm,topMargin=15*mm,bottomMargin=15*mm,title='SV16 to-do - rebuild step 1')
els=[Paragraph('SV16 to-do list - rebuild step 1',H1),
     Paragraph('Use the step-1 copy SBSV-16_rebuild_step1_values.kicad_pcb as the starting file. '
               'Tick each item when done. Items marked (not bought) need purchase before the board can work.',body),
     Spacer(1,4*mm)]
for head,items in todo:
    els.append(Paragraph(head,H2))
    for it in items:
        els.append(Paragraph('[  ]  '+esc(it),body))
        els.append(Spacer(1,1.5*mm))
    els.append(Spacer(1,3*mm))
doc2.build(els)
print('ok')
