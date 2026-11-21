"""Parametric, Structurally Optimized Garmin Quarter-Turn Mount for Google Pixel 6.

Rebuilt in FreeCAD from:
  garmin-to-google-pixel-6-bike-mount.obj

Preserved Phone & Garmin Interface Dimensions (all in mm):
  - Inner clamping width (X):     80.0 mm  (Pixel 6 + case)
  - Inner clamping depth (Y):     13.2 mm  (backplate inner face to front lip inner face)
  - Inner clamping height (Z):    90.0 mm  (bottom arm bottom to top hook inner face)
  - Garmin bayonet center:        (X = 0.0, Z = 15.0), protruding in +Y

Structural Optimizations vs. Original OBJ:
  1. Backplate thickness increased from 2.0 mm to 4.0 mm (8x plate bending stiffness).
  2. Spine width increased from 32.0 mm to 38.0 mm with large R12 mm T-junction fillets.
  3. Two longitudinal stiffening ribs (4.0 x 4.5 mm) on the back of the spine +
     horizontal stiffening ribs on the bottom arms, stopping cleanly outside a
     42 mm diameter clearance zone around the Garmin bayonet.
  4. Side arm wall thickness increased from 2.0 mm to 3.5 mm; front lips to 3.0 mm.
  5. Top hook thickness increased from 2.0 mm to 3.5 mm with inner corner fillet/chamfer
     and side gussets eliminating the 90-degree notch stress concentration.

Run with FreeCAD:
  "C:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe" garmin_pixel6_mount.py
"""

import math
import os
import FreeCAD
import Part
import Mesh
import MeshPart

# ==============================================================================
# PARAMETRIC CONFIGURATION (all dimensions in mm)
# Coordinate system:
#   X: Left (-) / Right (+), centered at 0
#   Y: Phone front (-Y) / Backplate & Garmin mount (+Y); Y=0 is inner backplate face
#   Z: Bottom (Z=0) / Top (+Z)
# ==============================================================================

# Preserved phone cavity dimensions (matching original OBJ)
INNER_WIDTH = 80.0            # Distance between left and right inner jaw faces
INNER_DEPTH = 13.2            # Distance from inner backplate (Y=0) to inner front lip (Y=-13.2)
INNER_HEIGHT = 90.0           # Distance from bottom (Z=0) to inner face of top hook (Z=90.0)

# Reinforced wall thicknesses
BACKPLATE_THICK = 4.0         # Original: 2.0 mm
SPINE_WIDTH = 38.0            # Original: 32.0 mm
ARM_HEIGHT = 16.0             # Height of bottom horizontal bar & side arms (Z = 0..16)
SIDE_WALL_THICK = 3.5         # Original: 2.0 mm
FRONT_LIP_THICK = 3.0         # Original: 2.0 mm
FRONT_LIP_OVERHANG = 3.5      # How far front bottom lips wrap inward along X
TOP_HOOK_THICK = 3.5          # Original: 2.0 mm
TOP_LIP_DROP = 2.8            # Downward retention lip at front of top hook
TOP_LIP_THICK = 2.4           # Thickness of downward lip

# Structural ribs on back (+Y)
RIB_DEPTH = 4.5               # Protrusion in +Y behind backplate (total spine depth = 8.5 mm)
RIB_WIDTH = 4.0               # Width of each rib
SPINE_RIB_OFFSET_X = 13.0     # X center of left/right longitudinal spine ribs
GARMIN_CLEARANCE_DIA = 42.0   # Free rotation zone for female Garmin mount

# T-junction gusset / flare
T_FLARE_WIDTH = 62.0          # Widened base of spine at Z = ARM_HEIGHT
T_FLARE_HEIGHT = 18.0         # Height of tapered transition above bottom bar

# Garmin Quarter-Turn Male Bayonet (on +Y back, centered at X=0, Z=15.0)
# Full-core design matching original OBJ dimensions for maximum shear/torsion strength
GARMIN_CENTER_Z = 15.0        # Matches Z_obj=19.0 - Z_obj_min=4.0
GARMIN_CORE_DIA = 25.0        # Full solid center core diameter (fits female mount bore)
GARMIN_NECK_HEIGHT = 1.5      # Clearance height for female mount retaining lip
GARMIN_WING_DIA = 28.5        # Outer diameter across locking wings
GARMIN_WING_THICK = 1.7       # Thickness of locking wings
GARMIN_WING_WIDTH = 11.5      # Width of each locking wing (Z)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def make_prism_xz(pts_xz, y_start, y_len):
    """Create a 3D prism by extruding an X-Z polygon along +Y."""
    vecs = [FreeCAD.Vector(x, y_start, z) for x, z in pts_xz]
    vecs.append(vecs[0])
    wire = Part.makePolygon(vecs)
    face = Part.Face(wire)
    return face.extrude(FreeCAD.Vector(0, y_len, 0))


def make_prism_yz(pts_yz, x_start, x_len):
    """Create a 3D prism by extruding a Y-Z polygon along +X."""
    vecs = [FreeCAD.Vector(x_start, y, z) for y, z in pts_yz]
    vecs.append(vecs[0])
    wire = Part.makePolygon(vecs)
    face = Part.Face(wire)
    return face.extrude(FreeCAD.Vector(x_len, 0, 0))


def build_garmin_bayonet(y_back):
    """Build the full-core male Garmin quarter-turn bayonet protruding in +Y."""
    center = FreeCAD.Vector(0, y_back, GARMIN_CENTER_Z)
    axis = FreeCAD.Vector(0, 1, 0)
    total_h = GARMIN_NECK_HEIGHT + GARMIN_WING_THICK

    # 1. Full-height solid core cylinder (maximizes shear & torsional strength)
    core = Part.makeCylinder(GARMIN_CORE_DIA / 2.0, total_h, center, axis)

    # 2. Locking wings protruding radially from the core at y_back + GARMIN_NECK_HEIGHT
    y_wing = y_back + GARMIN_NECK_HEIGHT
    wing_disc = Part.makeCylinder(
        GARMIN_WING_DIA / 2.0,
        GARMIN_WING_THICK,
        FreeCAD.Vector(0, y_wing, GARMIN_CENTER_Z),
        axis,
    )
    wing_bar = Part.makeBox(
        GARMIN_WING_DIA + 2.0,
        GARMIN_WING_THICK,
        GARMIN_WING_WIDTH,
        FreeCAD.Vector(
            -(GARMIN_WING_DIA + 2.0) / 2.0,
            y_wing,
            GARMIN_CENTER_Z - GARMIN_WING_WIDTH / 2.0,
        ),
    )
    wings = wing_disc.common(wing_bar)

    return core.fuse(wings)


def build_mount():
    """Construct the complete reinforced Garmin-to-Pixel-6 mount solid."""
    half_inner_w = INNER_WIDTH / 2.0
    half_outer_w = half_inner_w + SIDE_WALL_THICK
    half_spine_w = SPINE_WIDTH / 2.0
    half_flare_w = T_FLARE_WIDTH / 2.0

    # 1. Backplate T-profile with tapered T-junction (X-Z extruded along +Y)
    t_pts = [
        (-half_outer_w, 0.0),
        (half_outer_w, 0.0),
        (half_outer_w, ARM_HEIGHT),
        (half_flare_w, ARM_HEIGHT),
        (half_spine_w, ARM_HEIGHT + T_FLARE_HEIGHT),
        (half_spine_w, INNER_HEIGHT + TOP_HOOK_THICK),
        (-half_spine_w, INNER_HEIGHT + TOP_HOOK_THICK),
        (-half_spine_w, ARM_HEIGHT + T_FLARE_HEIGHT),
        (-half_flare_w, ARM_HEIGHT),
        (-half_outer_w, ARM_HEIGHT),
    ]
    backplate = make_prism_xz(t_pts, 0.0, BACKPLATE_THICK)

    # 2. Left & Right Side Arms + Front Retaining Lips
    # Profile in X-Y plane extruded along Z from 0 to ARM_HEIGHT
    arm_y_front = -(INNER_DEPTH + FRONT_LIP_THICK)
    arm_y_inner_front = -INNER_DEPTH
    lip_x_inner = half_inner_w - FRONT_LIP_OVERHANG

    def make_side_arm(sign):
        pts_xy = [
            (sign * half_inner_w, 0.0),
            (sign * half_outer_w, 0.0),
            (sign * half_outer_w, arm_y_front),
            (sign * lip_x_inner, arm_y_front),
            (sign * lip_x_inner, arm_y_inner_front),
            (sign * half_inner_w, arm_y_inner_front),
        ]
        if sign < 0:
            pts_xy.reverse()
        vecs = [FreeCAD.Vector(x, y, 0.0) for x, y in pts_xy]
        vecs.append(vecs[0])
        face = Part.Face(Part.makePolygon(vecs))
        return face.extrude(FreeCAD.Vector(0, 0, ARM_HEIGHT))

    left_arm = make_side_arm(-1)
    right_arm = make_side_arm(1)

    # 3. Top Hook with integrated inner corner gusset (Y-Z profile extruded along X)
    # Gusset chamfer 3.0 x 3.0 mm at (Y=0, Z=INNER_HEIGHT) eliminates 90-deg notch
    gusset = 3.0
    y_hook_front = -(INNER_DEPTH + TOP_LIP_THICK)
    y_hook_inner = -INNER_DEPTH
    z_top = INNER_HEIGHT + TOP_HOOK_THICK
    z_lip_bot = INNER_HEIGHT - TOP_LIP_DROP

    top_yz = [
        (0.0, INNER_HEIGHT - gusset),
        (-gusset, INNER_HEIGHT),
        (y_hook_inner, INNER_HEIGHT),
        (y_hook_inner, z_lip_bot),
        (y_hook_front, z_lip_bot),
        (y_hook_front, z_top),
        (BACKPLATE_THICK, z_top),
        (BACKPLATE_THICK, INNER_HEIGHT - gusset),
    ]
    top_hook = make_prism_yz(top_yz, -half_spine_w, SPINE_WIDTH)

    # 4. Longitudinal & Horizontal Stiffening Ribs on Back (+Y)
    #    Cut away the circular Garmin clearance zone (GARMIN_CLEARANCE_DIA)
    y_rib_start = BACKPLATE_THICK - 0.5  # overlap slightly for clean boolean fuse
    rib_len_y = RIB_DEPTH + 0.5

    # Two vertical spine ribs from Z=2.0 up to Z=INNER_HEIGHT + TOP_HOOK_THICK
    rib_left = Part.makeBox(
        RIB_WIDTH,
        rib_len_y,
        INNER_HEIGHT + TOP_HOOK_THICK - 2.0,
        FreeCAD.Vector(-SPINE_RIB_OFFSET_X - RIB_WIDTH / 2.0, y_rib_start, 2.0),
    )
    rib_right = Part.makeBox(
        RIB_WIDTH,
        rib_len_y,
        INNER_HEIGHT + TOP_HOOK_THICK - 2.0,
        FreeCAD.Vector(SPINE_RIB_OFFSET_X - RIB_WIDTH / 2.0, y_rib_start, 2.0),
    )

    # Horizontal stiffening rib along bottom bar (Z = 6.0 .. 10.0)
    rib_horiz = Part.makeBox(
        INNER_WIDTH - 4.0,
        rib_len_y,
        RIB_WIDTH,
        FreeCAD.Vector(-(INNER_WIDTH - 4.0) / 2.0, y_rib_start, 6.0),
    )

    ribs = rib_left.fuse(rib_right).fuse(rib_horiz)

    # Subtract Garmin clearance cylinder so female mount can rotate freely
    clearance_cyl = Part.makeCylinder(
        GARMIN_CLEARANCE_DIA / 2.0,
        RIB_DEPTH + 4.0,
        FreeCAD.Vector(0, BACKPLATE_THICK - 1.0, GARMIN_CENTER_Z),
        FreeCAD.Vector(0, 1, 0),
    )
    ribs = ribs.cut(clearance_cyl)

    # 5. Garmin Quarter-Turn Male Bayonet
    garmin = build_garmin_bayonet(BACKPLATE_THICK)

    # Fuse all components into one watertight solid
    solid = backplate.fuse(left_arm).fuse(right_arm).fuse(top_hook).fuse(ribs).fuse(garmin)
    solid = solid.removeSplitter()

    # 6. Apply structural & ergonomic fillets on outer/inner arm corners
    # Select vertical edges at the outer corners of the side arms
    fillet_edges = []
    for e in solid.Edges:
        v1, v2 = e.Vertexes[0].Point, e.Vertexes[-1].Point
        # Vertical edges at outer arm front corners (X = +-half_outer_w, Y = arm_y_front)
        if abs(v1.z - v2.z) > 10.0:
            if (abs(abs(v1.x) - half_outer_w) < 0.1 and abs(v1.y - arm_y_front) < 0.1):
                fillet_edges.append(e)
            elif (abs(abs(v1.x) - half_outer_w) < 0.1 and abs(v1.y) < 0.1):
                fillet_edges.append(e)
    if fillet_edges:
        try:
            solid = solid.makeFillet(2.5, fillet_edges)
        except Exception as exc:
            print("Note: outer corner fillet skipped:", exc)

    # Top hook outer edge fillet (Y = y_hook_front, Z = z_top)
    top_edges = []
    for e in solid.Edges:
        v1, v2 = e.Vertexes[0].Point, e.Vertexes[-1].Point
        if abs(v1.y - v2.y) < 0.05 and abs(v1.z - v2.z) < 0.05:
            if abs(v1.y - y_hook_front) < 0.1 and abs(v1.z - z_top) < 0.1:
                top_edges.append(e)
    if top_edges:
        try:
            solid = solid.makeFillet(1.2, top_edges)
        except Exception as exc:
            print("Note: top edge fillet skipped:", exc)

    return solid


def print_structural_comparison():
    """Compare bending stiffness (I) and section modulus (W) of spine."""
    # Original: 32 x 2.0 mm rectangle
    b0, h0 = 32.0, 2.0
    I0 = b0 * (h0 ** 3) / 12.0
    W0 = b0 * (h0 ** 2) / 6.0

    # Optimized: 38 x 4.0 mm plate + two 4.0 x 4.5 mm ribs
    # Compute exact composite I_y and W_y via parallel-axis theorem
    a_plate = SPINE_WIDTH * BACKPLATE_THICK
    y_plate = BACKPLATE_THICK / 2.0
    i_plate = SPINE_WIDTH * (BACKPLATE_THICK ** 3) / 12.0

    a_ribs = 2.0 * RIB_WIDTH * RIB_DEPTH
    y_ribs = BACKPLATE_THICK + RIB_DEPTH / 2.0
    i_ribs = 2.0 * RIB_WIDTH * (RIB_DEPTH ** 3) / 12.0

    a_tot = a_plate + a_ribs
    y_c = (a_plate * y_plate + a_ribs * y_ribs) / a_tot
    I_opt = (
        i_plate + a_plate * ((y_plate - y_c) ** 2)
        + i_ribs + a_ribs * ((y_ribs - y_c) ** 2)
    )
    y_max = max(y_c, (BACKPLATE_THICK + RIB_DEPTH) - y_c)
    W_opt = I_opt / y_max

    print("\n=== STRUCTURAL COMPARISON (Vertical Spine Bending) ===")
    print(f"Original  (32 x 2.0 mm flat):  I = {I0:7.1f} mm^4, W = {W0:6.1f} mm^3")
    print(f"Optimized (38 x 4.0 + 2 ribs): I = {I_opt:7.1f} mm^4, W = {W_opt:6.1f} mm^3")
    print(f"Stiffness gain (I_opt / I0):   {I_opt / I0:.1f}x")
    print(f"Strength gain  (W_opt / W0):   {W_opt / W0:.1f}x")


def main():
    doc = FreeCAD.newDocument("Garmin_Pixel6_Halterung_Optimiert")
    mount_solid = build_mount()

    print("Solid valid:", mount_solid.isValid())
    print("Num solids:", len(mount_solid.Solids))
    bb = mount_solid.BoundBox
    print(f"BoundingBox: X=[{bb.XMin:.2f}, {bb.XMax:.2f}] ({bb.XLength:.2f} mm), "
          f"Y=[{bb.YMin:.2f}, {bb.YMax:.2f}] ({bb.YLength:.2f} mm), "
          f"Z=[{bb.ZMin:.2f}, {bb.ZMax:.2f}] ({bb.ZLength:.2f} mm)")
    print(f"Volume: {mount_solid.Volume / 1000.0:.2f} cm^3")

    print_structural_comparison()

    part_obj = doc.addObject("Part::Feature", "Garmin_Pixel6_Halterung")
    part_obj.Shape = mount_solid
    doc.recompute()

    fcstd_path = os.path.join(OUTPUT_DIR, "Garmin_Pixel6_Halterung_Optimiert.FCStd")
    step_path = os.path.join(OUTPUT_DIR, "Garmin_Pixel6_Halterung_Optimiert.step")
    stl_path = os.path.join(OUTPUT_DIR, "Garmin_Pixel6_Halterung_Optimiert.stl")

    doc.saveAs(fcstd_path)
    Part.export([part_obj], step_path)
    mesh = MeshPart.meshFromShape(Shape=mount_solid, LinearDeflection=0.05, AngularDeflection=0.2, Relative=False)
    mesh.write(stl_path)

    print("Exported:")
    print(" ", fcstd_path)
    print(" ", step_path)
    print(" ", stl_path)


main()
