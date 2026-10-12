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
