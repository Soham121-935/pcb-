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
  'C32: change footprint from C_0805 to C_0603 (470 nF).',
  'R9, R10, R11, R12 (100 ohm): change footprint from R_1206 to R_0805 (bought 100 ohm pack is 0805).',
  'L1, L2 (10 uH CD54): change footprint from L_Sunlord_SWPA6045S to L_Sunlord_MWSA0518 (5.4x5.2 mm). Check pads against the bought part datasheet.',
  'Y1 (oscillator, ECS-3225MV-250): change footprint from Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm to the ECS land pattern: 4 pads, 1.4 x 1.2 mm, centres at (+-1.10, +-0.80) mm. Dimensions read from the ECS datasheet figure labels: check against the ECS drawing before use. Pad 1 = tri-state, 2 = GND, 3 = OUT, 4 = VDD.',
  'Y2 (12 MHz): change footprint from Crystal_HC49-4H (through-hole) to the SMD HC49/US footprint for the bought surface-mount crystal.',
  'FB1 (600 ohm ferrite): change footprint from 0603 to 0805 (Inductor_SMD:L_0805_2012Metric). Part in cart: TDK MPZ2012S601ATD25, 0805, qty 2.',
  'C36, C37 (22 pF): change footprint from C_0603 to C_0805 (YAGEO CC0805JRNPO9BN220, C0G 50 V 5%).',
  'R5 and R25 (4.7k): change footprint from R_0603 to R_0805 (use the 4.7k 0805 pack you bought).',
  'R6, R7, R8 (1k): change footprint from R_0603 to R_1206 (use the 1k 1206 pack you bought).',
  'R47 (10k): change footprint from R_1206 to R_0603. Use the 5% 0603 part (YAGEO RC0603JR-0710KL), already in cart.',
  'J7 (2x25 spare header): add Connector_PinHeader_2.54mm:PinHeader_2x25_P2.54mm_Vertical and mark it DNP (not fitted).',
  'D6 (red LED, INITN): mark DNP. J2 (JTAG_ALT): mark DNP (spec: unpopulated).',
  'J6 (motor header): shrouded, keyed 1x6 header. Footprint stays 1x6.',
  'R21, R22, R23, R24 (0 ohm): keep the 0603 footprint. Use as solder-bridge links, populate one pair only (R21/R23 or R22/R24). No 0 ohm bought.',
 ]),
 ('B. Schematic edits (you make these in the schematic, then update the board from it)', [
  'U6 COMP network: change R45 from 10k to 150k, and C35 from 100 nF to 100 pF. Calculated with the MP1584EN datasheet method: fsw 911 kHz (R40 = 100k), crossover about 91 kHz, output C21 = 100 uF, Vout 1.1 V. At 10k the crossover would be about 6 kHz, far below the expected range.',
  'U6 COMP second capacitor (C6 on COMP): do NOT fit. The datasheet table lists no second COMP capacitor for low output voltages. Verify loop stability on the bench.',
  'C23 (470 uF input bulk): change the voltage to 25 V (electrolytic, CP_Elec_8x10.5). 16 V on a 12 V rail is 75% of rated voltage, too close to the limit.',
  '5V_USB: connect this net to USB_VBUS in the schematic. The spec says the 5 V pins on J3 (17, 18) and J4 (20) are USB VBUS only. Right now 5V_USB has no source, so those pins are unpowered.',
  'U5 (AP62300) FB: keep the divider, R46 = 33k from 3V3 to U5_FB and R47 = 10k from U5_FB to GND. Do NOT connect U5_FB to 3V3. Output = 0.763 x (1 + 33/10) = 3.28 V. The spec correction that said to tie FB to 3V3 is wrong for this part.',
 ]),
 ('C. Values to set (check these in KiCad after the schematic is updated)', [
  'R44 = 1k (LED D7 current limit, 3V3 to D7). Keep.',
  'R48 = 100k (EN top, VM_IN to U5_EN), R49 = 33k (EN bottom). Keep. At 12 V, EN = 2.98 V, under the 6 V EN pin limit. EN threshold 1.2 V typ (Diodes DS41958), so the buck starts at about 4.7 to 4.9 V VIN.',
  'C34 = 100 nF (CH340G V3 decoupling). Keep.',
  'R38 = 12.4k, R39 = 33k: U6 feedback. Output = 0.8 x (1 + 12.4/33) = 1.10 V. Keep.',
  'Q2 = MMBT3904 and Q4 = MMBT3906 (SOT-23, pinout per spec). C36, C37 = 22 pF.',
  'Resistors: R1, R13-R19, R26, R32, R47 = 10k 5%. R2-R5, R25 = 4.7k. R6-R8, R31, R33, R34 = 1k. R9-R12 = 100 ohm. R27-R30 = 470 ohm. R36, R37 = 5.1k. R40, R41, R43 = 100k. R46 = 33k.',
  'Check the file opens with all 141 footprints. Confirm the component positions are unchanged.',
 ]),
 ('D. Circuit verification (from sv16_board.kicad_sch, checked against the spec)', [
  'PASS: FPGA power pins match the spec. 9 VCCIO pins on 3V3, 4 VCCAUX pins on 2V5, 6 VCC pins on 1V1, 14 GND.',
  'PASS: decoupling per rail. 3V3: C12-C20 plus C25, C26-C30, C40, C41. 2V5: C8-C11, C22, C42. 1V1: C2-C7, C21.',
  'PASS: AP62300 (U5): EN divider 100k/33k, BST cap C38, SW to L1 (10 uH) to 3V3, VIN bulk C39 plus C23.',
  'PASS: MP1584 (U6): FB divider 12.4k/33k gives 1.10 V, FREQ resistor R40 = 100k gives 911 kHz, EN delay R41 + C31, BST cap C33, catch diode D11 (SS34, cathode on SW), L2 10 uH to 1V1.',
  'PASS: LP5907 (U7): EN delay R43 100k + C32 470 nF. The 2V5 switch matches the spec correction 4 (Q3 and R42 removed).',
  'PASS: USB-C (J8): CC1/CC2 each have a 5.1k pull-down (R36, R37). VBUS to VM_IN_RAW through D9 and FB1. D+/D- through the USBLC6 array (U8) to the CH340G.',
  'PASS: CH340G (U4, keep this part): VCC on 3V3, 12 MHz crystal Y2 with 22 pF C36/C37, V3 decoupling C34, USB D+/D- on pins 5/6.',
  'PASS: Y1 pinout matches the ECS-3225MV (1 enable tied to 3V3, 2 GND, 3 clk_25m, 4 VDD on 3V3).',
  'PASS: flash U2/U3 WP and HOLD pins have pull-ups to 3V3 (R14, R15, R17, R18).',
  'ACTION: 5V_USB is not tied to USB_VBUS. See B.',
  'ACTION: R45 = 10k and C35 = 100 nF in the schematic. See B.',
  'ACTION: U5 FB must stay on the divider (not 3V3). See B. This corrects the spec correction 1 that I passed on earlier.',
  'ACTION: C23 voltage is 16 V. See B.',
  'VERIFY: CH340G pin 15 (R232) and pins 9-12, 14 (modem control, unused). Check the CH340G datasheet for the required state of pin 15.',
  'VERIFY: LP5907 pin 4 is unconnected in the schematic. Check the LP5907 datasheet (BYP, optional noise cap).',
  'VERIFY: J1 (JTAG) pin 5 is unconnected in the schematic. Check it against the JTAG connector standard for your programmer.',
  'VERIFY: the FPGA has 48 unlabelled pins. The spec lists 46 unassigned I/O pins. Check the 2 extra are NC or spare, not power.',
  'RISK: the spec says the AP62300 and LP5907 want ceramic output caps (spec correction 6). You chose electrolytic for C39-C42. Check the LP5907 stability on the bench. Consider ceramics if it is unstable.',
 ]),
 ('E. Purchases still needed (not in any cart screenshot)', [
  'U1: FPGA LFE5U-12F-6TG144C (not bought).',
  'U3: W25Q64JVSSIQ, 1 in cart. With the 1 you have, that makes 2 flash chips (U2, U3). Covered.',
  'Y1: ECS-3225MV-250, active 25 MHz XO 3.2x2.5 4-pad. The 3 bought 2-pin 25 MHz crystals cannot be used here.',
  'Y2: 12 MHz SMD crystal HC49/U (surface mount, 2-pin). In cart (qty 2).',
  'D8/D9/D11: 1 more SS34 (you have 2, need 3). SS34 is in cart (qty 1).',
  '10k 0603 5% resistors: YAGEO RC0603JR-0710KL, 12 pieces (R1, R13-R19, R26, R32, R47). In cart (qty 110).',
  '22 pF 0805 C0G caps: YAGEO CC0805JRNPO9BN220, 2 pieces (C36, C37). In cart (qty 4).',
  'FB1: TDK MPZ2012S601ATD25, 0805, 600 ohm. In cart (qty 2).',
  'R44 (1k 0603): check stock. Buy if you have none.',
  'R45 (150k 0603): buy. Not in any cart.',
  'C35 (100 pF 0603 C0G): check stock. Buy if you have none.',
  '4.7k (R5, R25) and 1k (R6-R8): use the 0805 and 1206 packs already bought. No purchase needed.',
  'Headers: standard 2.54 mm straight male pin headers (1x10, 2x10, 1x6, 1x4, 1x2). J6 is the exception: shrouded, keyed 1x6.',
  'Connectors and switches (barrel jack J9, SW1/SW2, JP1 shunt): you already have these. Confirm the parts and footprints match the board.',
 ]),
 ('F. Handoff notes', [
  'Starting file: SBSV-16_rebuild_step1_values.kicad_pcb (in this folder). It has 141 footprints, the same positions and a 4-layer stackup. 37 values changed. Do not move components. Do not change pad numbers or net names.',
  'Pin 1 of U6 = SW, 2 = EN, 3 = COMP, 4 = FB, 5 = GND, 6 = FREQ, 7 = VIN, 8 = BST. Confirmed against the schematic.',
  'Net names: the file keeps USB_DP/USB_DN and 5V_USB. The spec names are USB_D+/USB_D- and 5V. Record this in REPORT.md.',
  'Logo footprint G*** is removed in the step-1 file. Leave it removed and record it in REPORT.md. J3 must stay at its original position (194.65, 120.24 mm).',
  'Design rules (spec section 7): signal track 0.25 mm; 3V3, 1V1, 2V5 power tracks 0.8 mm; VM_IN 1.5 mm; switching nodes 0.8 mm and short. Clearance 0.2 mm minimum.',
 ]),
 ('G. Routing and checks (later step, not part of this netted board)', [
  'Strip the old routing first: the step-1 file still has 1,783 tracks and 179 vias. Delete all tracks and vias. Keep every footprint in place. Do not merge or copy old routing.',
  'Re-route from the updated placement, then run DRC: 0 unconnected, 0 shorts, 0 clearance, 0 edge or courtyard errors. Zones filled.',
  'Only after clean DRC: generate Gerber, drill, BOM and position files.',
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
