"""Shared design parameters for the ME 2331 Project 2 can flipper.

Everything is SI internally. Values tagged ESTIMATE come from datasheets or
hand calcs and must be replaced with bench system-ID numbers in Phase 2.
"""
import math

IN = 0.0254  # m per inch

# --- Test article (assignment Figure 1) -----------------------------------
CAN_D = 2.4 * IN          # diameter
CAN_H = 4.7 * IN          # height
CAN_M = 0.53 * 0.0283495  # 0.53 oz -> kg (15.0 g)
CAN_RIM_R = 1.05 * IN     # radius of the top chime the inverted can stands on (ESTIMATE, measure a can)

# --- Test layout (assignment Figure 2) ------------------------------------
# Robot origin at the corner, start at +Y, target at +X, both at 5 in.
R_TEST = 5.0 * IN
START = (0.0, R_TEST)
TARGET = (R_TEST, 0.0)

# --- Mirror-flip geometry (Concept D) --------------------------------------
# One horizontal revolute axis along the 45 deg bisector through the origin.
# A 180 deg turn about it maps START -> TARGET and inverts the can.
AXIS_DIR = (math.sqrt(0.5), math.sqrt(0.5), 0.0)
LAND_GAP = 0.04 * IN                     # axis raised so the can hovers 2*gap at 180 deg
AXIS_H = CAN_H / 2 + LAND_GAP            # axis height above table
ARM_R = R_TEST * math.sin(math.radians(45))  # axis-to-can-centre distance (3.54 in)

# --- Moving mass (ESTIMATE until CAD mass properties exist) ----------------
M_GRIPPER = 0.045   # SG90/MG90S + printed jaws + FSR + pads, at ARM_R
M_ARM = 0.020       # printed arm, uniform rod 0..ARM_R
# Counterweight opposite the can. Its radius must stay below AXIS_H minus clearance,
# otherwise it hits the table when it swings underneath the axis (theta = 90 deg).
R_CW = 1.8 * IN
# Balance 90 % of the EMPTY arm, so the net moment stays can-side-heavy with or without
# the can: the arm then rests on its theta = 0 hard stop / home switch when unpowered,
# and the gear train stays preloaded in one direction (no backlash crossover mid-hold).
CW_BALANCE = 0.9
M_CW = CW_BALANCE * (M_GRIPPER * ARM_R + M_ARM * ARM_R / 2) / R_CW

# --- Flip motor: 12 V JGA25-370 class gearmotor, ~1:34, hall encoder (ESTIMATE)
V_SUPPLY = 12.0
MOTOR_STALL_T = 0.45           # N*m at output shaft, 12 V
MOTOR_NOLOAD_W = 200 * 2 * math.pi / 60  # rad/s at output, 12 V
J_ROTOR_REFL = 1.2e-4          # rotor inertia reflected through gearbox, kg*m^2
FRICTION_T = 0.02              # Coulomb friction at output, N*m
ENC_CPR = 11 * 34 * 4          # 11 PPR x 34:1 x quadrature = 1496 counts/rev
PWM_MAX = 255

# --- Grip axis ---------------------------------------------------------------
MU_PAD = 0.6                  # silicone/TPU pad on aluminium (ESTIMATE, measure with a tilt test)
SAFETY_FACTOR = 3.0
F_DENT = 8.0                  # N per finger where an empty can starts to dent (ESTIMATE, test on scrap cans)
PAD_K = 800.0                 # pad + finger contact stiffness, N/m per finger (ESTIMATE)
SERVO_RATE = math.radians(60) / 0.10   # SG90 no-load: 60 deg / 0.10 s
JAW_LEVER = 0.030             # servo horn -> finger contact lever (m)

CONTROL_HZ = 200


def load_inertia():
    """Rotating inertia about the flip axis (kg*m^2), output side."""
    j = (CAN_M + M_GRIPPER) * ARM_R**2 + M_ARM * ARM_R**2 / 3 + M_CW * R_CW**2
    return j + J_ROTOR_REFL


def gravity_unbalance():
    """Net first moment m*r (kg*m) of the rotating assembly; torque = g*this*cos(theta)."""
    return (CAN_M + M_GRIPPER) * ARM_R + M_ARM * ARM_R / 2 - M_CW * R_CW
