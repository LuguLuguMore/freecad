"""Garmin Pixel 6 Mount + Garmin Out-Front Base Mount Assembly (Baugruppe).

Builds the mating Garmin Out-Front female quarter-turn receiver, out-front arm,
and 31.8 mm handlebar clamp in the locked assembly position on the Pixel 6 mount,
and verifies zero geometric interference (collision check).

Run with FreeCAD:
  "C:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe" garmin_assembly.py
"""

import os
import FreeCAD
import Part
import MeshPart

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOUNT_STEP = os.path.join(SCRIPT_DIR, "Garmin_Pixel6_Halterung_Optimiert.step")
FCSTD_ASM = os.path.join(SCRIPT_DIR, "Garmin_Pixel6_Baugruppe.FCStd")
STEP_ASM = os.path.join(SCRIPT_DIR, "Garmin_Pixel6_Baugruppe.step")
BASIS_STL = os.path.join(SCRIPT_DIR, "Garmin_OutFront_Basis.stl")

# Bayonet center on Pixel 6 mount: (X=0, Y_back=4.0, Z=15.0)
GARMIN_CENTER_Z = 15.0
Y_BACKPLATE = 4.0
CLEARANCE = 0.25

# Female Garmin Out-Front Receiver dimensions (matching user's photo)
CUP_OUTER_DIA = 38.0          # Fits inside our 48.0 mm clearance zone
CUP_INNER_LIP_DIA = 25.5      # 25.0 mm core + 0.25 mm/side clearance
CUP_POCKET_DIA = 29.0         # 28.5 mm wings + 0.25 mm/side clearance
CUP_Y_START = Y_BACKPLATE + 0.2  # 0.2 mm axial gap from backplate
CUP_TOTAL_DEPTH = 7.5         # Y from 4.2 to 11.7 mm

# Out-Front Arm + 31.8 mm Handlebar Clamp
ARM_LENGTH = 68.0             # Center-to-center distance along -Z
ARM_WIDTH = 16.0
ARM_THICK = 7.0
CLAMP_INNER_DIA = 31.8        # Standard 31.8 mm bike handlebar
CLAMP_OUTER_DIA = 41.0
CLAMP_WIDTH = 16.0


def build_garmin_outfront_basis():
    """Build the Garmin Out-Front female quarter-turn mount & handlebar clamp."""
    axis_y = FreeCAD.Vector(0, 1, 0)
    cup_center = FreeCAD.Vector(0, CUP_Y_START, GARMIN_CENTER_Z)

    # 1. Outer cylindrical housing of the female Garmin cup
    cup_outer = Part.makeCylinder(CUP_OUTER_DIA / 2.0, CUP_TOTAL_DEPTH, cup_center, axis_y)

    # 2. Inner bore for the 25.0 mm core (through the front retaining lip)
    bore_core = Part.makeCylinder(
        CUP_INNER_LIP_DIA / 2.0,
        4.2,
        FreeCAD.Vector(0, CUP_Y_START - 0.5, GARMIN_CENTER_Z),
        axis_y,
    )

    # 3. Internal undercut pocket for the locking wings (Y = Y_BACKPLATE + 1.5 .. 3.5)
    #    Wing is at Y = 5.5 .. 7.2, so pocket spans Y = 5.25 .. 7.55
    pocket = Part.makeCylinder(
        CUP_POCKET_DIA / 2.0,
        2.3,
        FreeCAD.Vector(0, Y_BACKPLATE + 1.25, GARMIN_CENTER_Z),
        axis_y,
    )

    # 4. Two vertical entry slots in the front lip (along Z, 90 deg from locked X wings)
    #    Width = 12.0 mm (11.5 mm wing + clearance)
    slot = Part.makeBox(
        12.0,
        2.5,
        CUP_POCKET_DIA + 1.0,
        FreeCAD.Vector(-6.0, CUP_Y_START - 0.5, GARMIN_CENTER_Z - (CUP_POCKET_DIA + 1.0) / 2.0),
    )

    # 5. Out-Front Arm extending downward (-Z) from the cup toward the handlebar clamp
    z_clamp = GARMIN_CENTER_Z - ARM_LENGTH
    y_arm = CUP_Y_START + CUP_TOTAL_DEPTH - ARM_THICK
    arm = Part.makeBox(
        ARM_WIDTH,
        ARM_THICK,
        ARM_LENGTH - CLAMP_OUTER_DIA / 2.0 + 12.0,
        FreeCAD.Vector(-ARM_WIDTH / 2.0, y_arm, z_clamp + CLAMP_OUTER_DIA / 2.0 - 8.0),
    )

    # 6. 31.8 mm Handlebar Clamp Ring (axis along X)
    clamp_center = FreeCAD.Vector(-CLAMP_WIDTH / 2.0, y_arm + ARM_THICK / 2.0, z_clamp)
    axis_x = FreeCAD.Vector(1, 0, 0)
    clamp_outer = Part.makeCylinder(CLAMP_OUTER_DIA / 2.0, CLAMP_WIDTH, clamp_center, axis_x)
    clamp_inner = Part.makeCylinder(
        CLAMP_INNER_DIA / 2.0,
        CLAMP_WIDTH + 2.0,
        FreeCAD.Vector(-CLAMP_WIDTH / 2.0 - 1.0, y_arm + ARM_THICK / 2.0, z_clamp),
        axis_x,
    )
    clamp_slit = Part.makeBox(
        CLAMP_WIDTH + 2.0,
        2.0,
        10.0,
        FreeCAD.Vector(-CLAMP_WIDTH / 2.0 - 1.0, y_arm + ARM_THICK / 2.0 - 1.0, z_clamp - CLAMP_OUTER_DIA / 2.0 - 1.0),
    )
    clamp = clamp_outer.cut(clamp_inner).cut(clamp_slit)

    # Combine solid housings FIRST, then cut internal receiver bore, pocket & slots
    raw_basis = cup_outer.fuse(arm).fuse(clamp)
    basis = raw_basis.cut(bore_core).cut(pocket).cut(slot).removeSplitter()
    return basis


def main():
    doc = FreeCAD.newDocument("Garmin_Pixel6_Baugruppe")

    # Part 1: Pixel 6 Mount
    mount_shape = Part.Shape()
    mount_shape.read(MOUNT_STEP)
    obj_mount = doc.addObject("Part::Feature", "Pixel6_Halterung")
    obj_mount.Shape = mount_shape

    # Part 2: Garmin Out-Front Base Mount
    basis_shape = build_garmin_outfront_basis()
    obj_basis = doc.addObject("Part::Feature", "Garmin_OutFront_Basis")
    obj_basis.Shape = basis_shape

    doc.recompute()

    # Collision / Interference Check
    overlap = mount_shape.common(basis_shape)
    print(f"Basis valid: {basis_shape.isValid()}, Solids: {len(basis_shape.Solids)}")
    print(f"Collision volume (Mount vs. Basis): {overlap.Volume:.4f} mm^3")

    doc.saveAs(FCSTD_ASM)
    Part.export([obj_mount, obj_basis], STEP_ASM)
    mesh = MeshPart.meshFromShape(Shape=basis_shape, LinearDeflection=0.05, AngularDeflection=0.2, Relative=False)
    mesh.write(BASIS_STL)

    print("Exported Assembly:")
    print(" ", FCSTD_ASM)
    print(" ", STEP_ASM)
    print(" ", BASIS_STL)


main()
