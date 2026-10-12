# SV16 rebuild - step 1 (value-level only)

- `SBSV-16_rebuild_step1_values.kicad_pcb`: copy of the uploaded `SBSV-16.kicad_pcb`
  with 46 `Value` fields changed (Q2/Q4 -> MMBT3904/3906, C36/C37 -> 22pF,
  resistor values from the spec). Components, footprints, tracks, vias and zones
  are unchanged (141 footprints, 1783 segments, 179 vias).
- `BOM_rebuild_step1.csv`: parts list with bought/needed status.

Not yet done: footprint changes (C25/C30 electrolytic, C32 0603, R9-R12 0805, L1/L2
MWSA0518, J7 added, D6 DNP, FB1/R21-R24 as solder bridges), undecided values
(R44, R45, R48, R49, C34, C35), placement review and re-routing with DRC.
These need KiCad footprint libraries, which are not installed in this sandbox.
