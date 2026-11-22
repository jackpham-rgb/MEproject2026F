; E-steps check. Mark the filament 120 mm above the extruder inlet first.
; Heats to 220 C, extrudes 100 mm slowly. Then measure the mark: 20 mm left = correct.
M104 S220
M109 S220
M503
M83
G1 E100 F100
M400
M104 S0
M117 Measure the mark now
