# SV16 rebuild folder (self-contained)

This folder is the complete input set for the PCB agent. Work only inside it.

Files:
- `MASTER_PROMPT.md`: the full task for the agent (netted, footprint-based board, no routing).
- `PCB_COMPONENTS.pdf`: the spec (values, pinouts, net names, design rules).
- `SV16_TODO_rebuild_step1.pdf`: the checklist (sections A to G). Section F is routing and is out of scope.
- `SV16_BOM_rebuild_step1.pdf` and `BOM_rebuild_step1.csv`: parts list with footprints, values and bought/needed status.
- `SBSV-16_rebuild_step1_values.kicad_pcb`: copy of the uploaded board with 37 values changed. Reference only. It still contains the OLD tracks and vias, which must be deleted.
- `make_pdfs.py`: regenerates the to-do and BOM PDFs (needs reportlab).

To be added by the user before the agent runs:
- The UNROUTED KiCad PCB (`.kicad_pcb`), placed in this folder. The agent uses it as the starting board.

Output (created by the agent):
- `sv16_board_netted.kicad_pcb`: netted footprint-based board, no tracks, no vias.
- `REPORT.md`: what changed, what was not done, and the decisions the user must confirm.
- `agent_work/`: backups and the worklog.

Not included on purpose: the old routed draft and the old routing files. Do not copy routing from anywhere.

Not yet in hand (see the BOM): FPGA, second W25Q64, active 25 MHz oscillator Y1, 12 MHz crystal Y2, third SS34, 10k resistors, 22 pF caps.
