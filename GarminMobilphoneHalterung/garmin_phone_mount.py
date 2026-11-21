"""Parametric 3D-printable Garmin Quarter-Turn Smartphone Clamp Mount.

Generates:
  - Mittelteil_Garmin.stl       (Center body with Garmin male quarter-turn mount & dovetail rail)
  - Klemmbacke_Links.stl        (Left clamping jaw with elastic hooks & M4 screw bore)
  - Klemmbacke_Rechts.stl       (Right clamping jaw with elastic hooks & M4 screw bore)
  - Garmin_Mobilphone_Halterung.FCStd (Full FreeCAD assembly project)
  - Garmin_Mobilphone_Halterung.step  (STEP assembly)

Run with FreeCAD:
  "C:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe" garmin_phone_mount.py
"""

import math
import os
import FreeCAD
import Part
import Mesh
import MeshPart
import TechDraw

# ==============================================================================
# PARAMETRIC CONFIGURATION (all dimensions in mm)
# ==============================================================================
PHONE_WIDTH_MIN = 62.0        # Minimum inner clamping width (jaws closed)
PHONE_THICKNESS = 12.0        # Max phone + case thickness inside jaw
JAW_WALL_THICKNESS = 6.0      # Outer wall thickness of each jaw
FRONT_LIP_OVERHANG = 3.5      # How far the front lip wraps over phone bezel
FRONT_LIP_THICKNESS = 2.6     # Thickness of the front retention lip

CENTER_WIDTH = 60.0           # Width of center body (must be <= PHONE_WIDTH_MIN)
CENTER_HEIGHT = 48.0          # Height of center body (Y)
CENTER_THICKNESS = 10.0       # Thickness of center body (Z)

# Sliding dovetail rail (with 3D-printing clearance)
RAIL_CLEARANCE = 0.25         # Per-side clearance for smooth sliding
RAIL_NECK_WIDTH = 14.0        # Narrowest width at Z = 0
RAIL_INNER_WIDTH = 22.0       # Widest width inside center body
RAIL_DEPTH = 6.5              # Depth of rail into center body (Z)
TONGUE_LENGTH = 28.0          # How far each jaw tongue extends into center body

# Clamping Screw (M4)
SCREW_HOLE_DIA = 4.5          # M4 clearance hole
SCREW_HEAD_DIA = 8.2          # M4 socket head / thumbscrew counterbore
SCREW_HEAD_DEPTH = 4.0        # Counterbore depth
NUT_AF = 7.2                  # M4 hex nut across flats (7.0 mm + 0.2 mm tolerance)
NUT_THICKNESS = 3.5           # M4 hex nut pocket width

# Garmin Quarter-Turn Male Bayonet (on back of center body, Z < 0)
GARMIN_BASE_DIA = 34.0        # Base standoff disc diameter
GARMIN_BASE_HEIGHT = 1.2      # Standoff height from center body back
GARMIN_NECK_DIA = 26.8        # Inner neck cylinder diameter
GARMIN_NECK_HEIGHT = 2.2      # Gap for female mount retaining lip
GARMIN_WING_DIA = 33.4        # Outer diameter of locking tabs
GARMIN_WING_THICK = 2.0       # Thickness of locking tabs
GARMIN_WING_WIDTH = 10.5      # Width of each locking tab

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def make_dovetail_profile(neck_w, inner_w, depth, x_start, x_len):
    """Create a 3D prism with a trapezoidal+rectangular dovetail cross-section in Y-Z."""
    # Y-Z profile points (closed wire), extruded along +X
    chamfer_z = (inner_w - neck_w) / 2.0  # 45-degree slope
    pts = [
        FreeCAD.Vector(x_start, -neck_w / 2.0, 0.0),
        FreeCAD.Vector(x_start, -inner_w / 2.0, -chamfer_z),
        FreeCAD.Vector(x_start, -inner_w / 2.0, -depth),
        FreeCAD.Vector(x_start, inner_w / 2.0, -depth),
        FreeCAD.Vector(x_start, inner_w / 2.0, -chamfer_z),
        FreeCAD.Vector(x_start, neck_w / 2.0, 0.0),
        FreeCAD.Vector(x_start, -neck_w / 2.0, 0.0),
    ]
    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    return face.extrude(FreeCAD.Vector(x_len, 0, 0))


def make_hex_prism(af, length, center_y, center_z, x_start):
    """Create a hexagonal prism along X for a captive hex nut."""
    r = (af / 2.0) / math.cos(math.radians(30))
    pts = []
    for i in range(7):
        ang = math.radians(60 * i)
        y = center_y + r * math.cos(ang)
        z = center_z + r * math.sin(ang)
        pts.append(FreeCAD.Vector(x_start, y, z))
    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    return face.extrude(FreeCAD.Vector(length, 0, 0))


def build_garmin_bayonet(z_back):
    """Build the male Garmin quarter-turn bayonet protruding in -Z from z_back."""
    # 1. Base standoff disc
    base = Part.makeCylinder(
        GARMIN_BASE_DIA / 2.0,
        GARMIN_BASE_HEIGHT,
        FreeCAD.Vector(0, 0, z_back),
        FreeCAD.Vector(0, 0, -1),
    )

    # 2. Inner neck cylinder
    z_neck = z_back - GARMIN_BASE_HEIGHT
    neck = Part.makeCylinder(
        GARMIN_NECK_DIA / 2.0,
        GARMIN_NECK_HEIGHT,
        FreeCAD.Vector(0, 0, z_neck),
        FreeCAD.Vector(0, 0, -1),
    )

    # 3. Locking wings (cylinder intersected with cross-bar)
    z_wing = z_neck - GARMIN_NECK_HEIGHT
    wing_disc = Part.makeCylinder(
        GARMIN_WING_DIA / 2.0,
        GARMIN_WING_THICK,
        FreeCAD.Vector(0, 0, z_wing),
        FreeCAD.Vector(0, 0, -1),
    )
    wing_bar = Part.makeBox(
        GARMIN_WING_DIA + 2.0,
        GARMIN_WING_WIDTH,
        GARMIN_WING_THICK,
        FreeCAD.Vector(-(GARMIN_WING_DIA + 2.0) / 2.0, -GARMIN_WING_WIDTH / 2.0, z_wing - GARMIN_WING_THICK),
    )
    wings = wing_disc.common(wing_bar)

    # Add central boss connecting wings cleanly
    center_boss = Part.makeCylinder(
        GARMIN_NECK_DIA / 2.0,
        GARMIN_WING_THICK,
        FreeCAD.Vector(0, 0, z_wing),
        FreeCAD.Vector(0, 0, -1),
    )

    bayonet = base.fuse(neck).fuse(wings).fuse(center_boss)
    return bayonet


def build_center_body():
    """Build the Center Body (Mittelteil) with dovetail slot, nut pockets, and Garmin mount."""
    body = Part.makeBox(
        CENTER_WIDTH,
        CENTER_HEIGHT,
        CENTER_THICKNESS,
        FreeCAD.Vector(-CENTER_WIDTH / 2.0, -CENTER_HEIGHT / 2.0, -CENTER_THICKNESS),
    )

    # Cut full-width dovetail slot
    slot = make_dovetail_profile(
        RAIL_NECK_WIDTH,
        RAIL_INNER_WIDTH,
        RAIL_DEPTH,
        -CENTER_WIDTH / 2.0 - 1.0,
        CENTER_WIDTH + 2.0,
    )
    body = body.cut(slot)

    # Cut central M4 screw through-bore along X (at Y=0, Z=-RAIL_DEPTH/2)
    z_screw = -RAIL_DEPTH / 2.0
    screw_bore = Part.makeCylinder(
        SCREW_HOLE_DIA / 2.0,
        CENTER_WIDTH + 2.0,
        FreeCAD.Vector(-CENTER_WIDTH / 2.0 - 1.0, 0, z_screw),
        FreeCAD.Vector(1, 0, 0),
    )
    body = body.cut(screw_bore)

    # Cut two captive M4 hex nut pockets (accessible from the front slot)
    # Placed at X = -18 mm and X = +18 mm, with a top access slot from Z = 0
    for x_nut in (-18.0, 18.0):
        nut_hex = make_hex_prism(NUT_AF, NUT_THICKNESS, 0.0, z_screw, x_nut - NUT_THICKNESS / 2.0)
        nut_drop = Part.makeBox(
            NUT_THICKNESS,
            NUT_AF,
            abs(z_screw) + 1.0,
            FreeCAD.Vector(x_nut - NUT_THICKNESS / 2.0, -NUT_AF / 2.0, z_screw),
        )
        body = body.cut(nut_hex).cut(nut_drop)

    # Fuse Garmin Male Quarter-Turn Bayonet onto back face (Z = -CENTER_THICKNESS)
    bayonet = build_garmin_bayonet(-CENTER_THICKNESS)
    body = body.fuse(bayonet)

    return body


def build_jaw(side=1):
    """Build Left (side=-1) or Right (side=+1) Clamping Jaw.

    Positioned at the closed width (PHONE_WIDTH_MIN / 2.0).
    """
    x_inner = side * (PHONE_WIDTH_MIN / 2.0)
    jaw_height = CENTER_HEIGHT

    # 1. Main vertical wall outside the phone edge
    if side == 1:
        wall_x0 = x_inner
        tongue_x0 = x_inner - TONGUE_LENGTH
        lip_x0 = x_inner - FRONT_LIP_OVERHANG
    else:
        wall_x0 = x_inner - JAW_WALL_THICKNESS
        tongue_x0 = x_inner
        lip_x0 = x_inner

    wall_z0 = -CENTER_THICKNESS
    wall_z_total = CENTER_THICKNESS + PHONE_THICKNESS + FRONT_LIP_THICKNESS

    wall = Part.makeBox(
        JAW_WALL_THICKNESS,
        jaw_height,
        wall_z_total,
        FreeCAD.Vector(wall_x0, -jaw_height / 2.0, wall_z0),
    )

    # 2. Front retention lip (wraps over phone bezel)
    lip = Part.makeBox(
        FRONT_LIP_OVERHANG + 0.5,
        jaw_height,
        FRONT_LIP_THICKNESS,
        FreeCAD.Vector(lip_x0 if side == 1 else lip_x0 - 0.5, -jaw_height / 2.0, PHONE_THICKNESS),
    )

    # 3. Sliding dovetail tongue (with clearance)
    tongue = make_dovetail_profile(
        RAIL_NECK_WIDTH - 2 * RAIL_CLEARANCE,
        RAIL_INNER_WIDTH - 2 * RAIL_CLEARANCE,
        RAIL_DEPTH - RAIL_CLEARANCE,
        tongue_x0,
        TONGUE_LENGTH + (1.0 if side == 1 else 1.0),
    )
    if side == -1:
        tongue = make_dovetail_profile(
            RAIL_NECK_WIDTH - 2 * RAIL_CLEARANCE,
            RAIL_INNER_WIDTH - 2 * RAIL_CLEARANCE,
            RAIL_DEPTH - RAIL_CLEARANCE,
            x_inner - 1.0,
            TONGUE_LENGTH + 1.0,
        )

    # 4. Elastic band (Gummizug) hook posts on top & bottom of outer wall (Z < 0)
    #    Positioned at Y = +/- 19.5 mm (clear of the 34 mm Garmin circle)
    hook_posts = []
    for y_sign in (-1, 1):
        y_center = y_sign * (jaw_height / 2.0 - 4.5)
        post_x = wall_x0 + (JAW_WALL_THICKNESS / 2.0)
        post = Part.makeCylinder(
            2.6,
            3.5,
            FreeCAD.Vector(post_x, y_center, -CENTER_THICKNESS),
            FreeCAD.Vector(0, 0, -1),
        )
        cap = Part.makeCylinder(
            3.4,
            1.2,
            FreeCAD.Vector(post_x, y_center, -CENTER_THICKNESS - 3.5),
            FreeCAD.Vector(0, 0, -1),
        )
        hook_posts.extend([post, cap])

    jaw = wall.fuse(lip).fuse(tongue)
    for hp in hook_posts:
        jaw = jaw.fuse(hp)

    # 5. Cut M4 screw clearance hole + counterbore through outer wall & tongue
    z_screw = -RAIL_DEPTH / 2.0
    bore_x0 = (x_inner - TONGUE_LENGTH - 1.0) if side == 1 else (x_inner - JAW_WALL_THICKNESS - 1.0)
    bore_len = TONGUE_LENGTH + JAW_WALL_THICKNESS + 2.0
    screw_hole = Part.makeCylinder(
        SCREW_HOLE_DIA / 2.0,
        bore_len,
        FreeCAD.Vector(bore_x0, 0, z_screw),
        FreeCAD.Vector(1, 0, 0),
    )
    jaw = jaw.cut(screw_hole)

    # Counterbore from outside
    if side == 1:
        cb_x0 = x_inner + JAW_WALL_THICKNESS - SCREW_HEAD_DEPTH
    else:
        cb_x0 = x_inner - JAW_WALL_THICKNESS - 1.0
    counterbore = Part.makeCylinder(
        SCREW_HEAD_DIA / 2.0,
        SCREW_HEAD_DEPTH + 1.0,
        FreeCAD.Vector(cb_x0, 0, z_screw),
        FreeCAD.Vector(1, 0, 0),
    )
    jaw = jaw.cut(counterbore)

    return jaw


def export_stl(shape, filename):
    """Tessellate shape cleanly and export as STL."""
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=0.05,
        AngularDeflection=0.2,
        Relative=False,
    )
    path = os.path.join(OUTPUT_DIR, filename)
    mesh.write(path)
    print(f"Exported STL: {path} (facets={mesh.CountFacets}, points={mesh.CountPoints})")


def find_vertex(shape, x, y, z, tol=0.25):
    """Return 'VertexN' (1-based) closest to (x, y, z) within tol."""
    target = FreeCAD.Vector(x, y, z)
    best_idx = None
    best_dist = tol
    for idx, v in enumerate(shape.Vertexes, start=1):
        d = v.Point.distanceToPoint(target)
        if d < best_dist:
            best_dist = d
            best_idx = idx
    if best_idx is None:
        raise ValueError(f"Vertex near ({x}, {y}, {z}) not found")
    return f"Vertex{best_idx}"


def find_circle_edge(shape, radius, z_val=None, x_val=None, tol=0.15):
    """Return 'EdgeN' (1-based) for a circular/arc edge matching radius and optional Z/X."""
    for idx, e in enumerate(shape.Edges, start=1):
        curve = e.Curve
        if hasattr(curve, "Radius") and abs(curve.Radius - radius) < tol:
            c = curve.Center
            if z_val is not None and abs(c.z - z_val) > tol:
                continue
            if x_val is not None and abs(c.x - x_val) > tol:
                continue
            return f"Edge{idx}"
    raise ValueError(f"Circle edge R={radius} (z={z_val}, x={x_val}) not found")


def add_dim_3d(page, view, name, dim_type, refs_3d, x, y, fmt=""):
    """Create a TechDraw DrawViewDimension linked to 3D geometry."""
    dim = page.Document.addObject("TechDraw::DrawViewDimension", name)
    dim.Type = dim_type
    dim.MeasureType = "True"
    dim.References2D = [(view, ())]
    dim.References3D = refs_3d
    dim.X = x
    dim.Y = y
    if fmt:
        dim.FormatSpec = fmt
    page.addView(dim)
    return dim


def add_techdraw_sheets(doc, obj_center, obj_left, obj_right):
    """Create two A4 Landscape TechDraw sheets with full dimensioning."""
    tmpl_path = os.path.join(
        FreeCAD.getResourceDir(),
        "Mod", "TechDraw", "Templates", "A4_Landscape_ISO5457_minimal.svg",
    )

    s_c = obj_center.Shape
    s_l = obj_left.Shape
    s_r = obj_right.Shape

    # ------------------------------------------------------------------
    # PAGE 1: Baugruppe & Mittelteil (Scale 1:1)
    # ------------------------------------------------------------------
    page1 = doc.addObject("TechDraw::DrawPage", "Zeichnung_Baugruppe")
    tmpl1 = doc.addObject("TechDraw::DrawSVGTemplate", "Template_Baugruppe")
    tmpl1.Template = tmpl_path
    page1.Template = tmpl1

    # 1. Front View (Assembly, looking from +Z toward -Z)
    v_front = doc.addObject("TechDraw::DrawViewPart", "Vorderansicht")
    v_front.Source = [obj_center, obj_left, obj_right]
    v_front.Direction = FreeCAD.Vector(0, 0, 1)
    v_front.XDirection = FreeCAD.Vector(1, 0, 0)
    v_front.Scale = 1.0
    v_front.X = 75.0
    v_front.Y = 130.0
    page1.addView(v_front)

    # Dimensions on Front View
    add_dim_3d(
        page1, v_front, "Dim_Hoehe_Gesamt", "DistanceY",
        [(obj_center, (find_vertex(s_c, -30, -24, 0),)),
         (obj_center, (find_vertex(s_c, -30, 24, 0),))],
        x=-52.0, y=0.0,
    )
    add_dim_3d(
        page1, v_front, "Dim_Breite_Mittelteil", "DistanceX",
        [(obj_center, (find_vertex(s_c, -30, 24, 0),)),
         (obj_center, (find_vertex(s_c, 30, 24, 0),))],
        x=0.0, y=33.0,
    )
    add_dim_3d(
        page1, v_front, "Dim_Klemmbreite_Min", "DistanceX",
        [(obj_left, (find_vertex(s_l, -PHONE_WIDTH_MIN / 2.0, -24, PHONE_THICKNESS),)),
         (obj_right, (find_vertex(s_r, PHONE_WIDTH_MIN / 2.0, -24, PHONE_THICKNESS),))],
        x=0.0, y=-33.0, fmt="%.1f (min)",
    )
    add_dim_3d(
        page1, v_front, "Dim_Gesamtbreite_Geschlossen", "DistanceX",
        [(obj_left, (find_vertex(s_l, -PHONE_WIDTH_MIN / 2.0 - JAW_WALL_THICKNESS, -24, -CENTER_THICKNESS),)),
         (obj_right, (find_vertex(s_r, PHONE_WIDTH_MIN / 2.0 + JAW_WALL_THICKNESS, -24, -CENTER_THICKNESS),))],
        x=0.0, y=-43.0,
    )

    # 2. Back View (Mittelteil Garmin Bajonett, looking from -Z toward +Z)
    v_back = doc.addObject("TechDraw::DrawViewPart", "Rueckansicht_Garmin")
    v_back.Source = [obj_center]
    v_back.Direction = FreeCAD.Vector(0, 0, -1)
    v_back.XDirection = FreeCAD.Vector(-1, 0, 0)
    v_back.Scale = 1.0
    v_back.X = 180.0
    v_back.Y = 130.0
    page1.addView(v_back)

    z_wing_top = -CENTER_THICKNESS - GARMIN_BASE_HEIGHT - GARMIN_NECK_HEIGHT - GARMIN_WING_THICK
    z_neck_bot = -CENTER_THICKNESS - GARMIN_BASE_HEIGHT
    add_dim_3d(
        page1, v_back, "Dim_Garmin_Fluegel_Dia", "Diameter",
        [(obj_center, (find_circle_edge(s_c, GARMIN_WING_DIA / 2.0, z_val=z_wing_top),))],
        x=28.0, y=28.0,
    )
    add_dim_3d(
        page1, v_back, "Dim_Garmin_Hals_Dia", "Diameter",
        [(obj_center, (find_circle_edge(s_c, GARMIN_NECK_DIA / 2.0, z_val=z_neck_bot),))],
        x=-28.0, y=-28.0,
    )
    add_dim_3d(
        page1, v_back, "Dim_Garmin_Fluegelbreite", "DistanceY",
        [(obj_center, (find_vertex(s_c, GARMIN_WING_DIA / 2.0 * math.cos(math.asin(GARMIN_WING_WIDTH / GARMIN_WING_DIA)), -GARMIN_WING_WIDTH / 2.0, z_wing_top, tol=0.5),)),
         (obj_center, (find_vertex(s_c, GARMIN_WING_DIA / 2.0 * math.cos(math.asin(GARMIN_WING_WIDTH / GARMIN_WING_DIA)), GARMIN_WING_WIDTH / 2.0, z_wing_top, tol=0.5),))],
        x=35.0, y=0.0,
    )

    # 3. Top/Bottom View (looking from -Y toward +Y)
    v_top = doc.addObject("TechDraw::DrawViewPart", "Draufsicht")
    v_top.Source = [obj_center, obj_left, obj_right]
    v_top.Direction = FreeCAD.Vector(0, -1, 0)
    v_top.XDirection = FreeCAD.Vector(1, 0, 0)
    v_top.Scale = 1.0
    v_top.X = 75.0
    v_top.Y = 55.0
    page1.addView(v_top)

    add_dim_3d(
        page1, v_top, "Dim_Handy_Dicke_Max", "Distance",
        [(obj_left, (find_vertex(s_l, -PHONE_WIDTH_MIN / 2.0, -24, -CENTER_THICKNESS),)),
         (obj_left, (find_vertex(s_l, -PHONE_WIDTH_MIN / 2.0, -24, PHONE_THICKNESS),))],
        x=-48.0, y=6.0,
    )
    add_dim_3d(
        page1, v_top, "Dim_Mittelteil_Dicke", "Distance",
        [(obj_center, (find_vertex(s_c, 30, -24, -CENTER_THICKNESS),)),
         (obj_center, (find_vertex(s_c, 30, -24, 0),))],
        x=48.0, y=-5.0,
    )

    # 4. Isometric View
    v_iso = doc.addObject("TechDraw::DrawViewPart", "Isometrie")
    v_iso.Source = [obj_center, obj_left, obj_right]
    v_iso.Direction = FreeCAD.Vector(1, -1, 1)
    v_iso.Scale = 0.85
    v_iso.X = 248.0
    v_iso.Y = 140.0
    page1.addView(v_iso)

    # ------------------------------------------------------------------
    # PAGE 2: Detail Klemmbacke Links (Scale 1.5:1)
    # ------------------------------------------------------------------
    page2 = doc.addObject("TechDraw::DrawPage", "Zeichnung_Klemmbacke")
    tmpl2 = doc.addObject("TechDraw::DrawSVGTemplate", "Template_Klemmbacke")
    tmpl2.Template = tmpl_path
    page2.Template = tmpl2

    v_jaw_side = doc.addObject("TechDraw::DrawViewPart", "Backe_Seitenansicht")
    v_jaw_side.Source = [obj_left]
    v_jaw_side.Direction = FreeCAD.Vector(-1, 0, 0)
    v_jaw_side.XDirection = FreeCAD.Vector(0, 1, 0)
    v_jaw_side.Scale = 1.5
    v_jaw_side.X = 85.0
    v_jaw_side.Y = 125.0
    page2.addView(v_jaw_side)

    z_screw = -RAIL_DEPTH / 2.0
    x_outer = -PHONE_WIDTH_MIN / 2.0 - JAW_WALL_THICKNESS
    add_dim_3d(
        page2, v_jaw_side, "Dim_Backe_Hoehe", "DistanceY",
        [(obj_left, (find_vertex(s_l, x_outer, -24, -CENTER_THICKNESS),)),
         (obj_left, (find_vertex(s_l, x_outer, 24, -CENTER_THICKNESS),))],
        x=-52.0, y=0.0,
    )
    add_dim_3d(
        page2, v_jaw_side, "Dim_M4_Senkung", "Diameter",
        [(obj_left, (find_circle_edge(s_l, SCREW_HEAD_DIA / 2.0, x_val=x_outer),))],
        x=25.0, y=18.0,
    )
    add_dim_3d(
        page2, v_jaw_side, "Dim_M4_Durchgang", "Diameter",
        [(obj_left, (find_circle_edge(s_l, SCREW_HOLE_DIA / 2.0, x_val=x_outer + SCREW_HEAD_DEPTH),))],
        x=25.0, y=-18.0,
    )

    v_jaw_top = doc.addObject("TechDraw::DrawViewPart", "Backe_Draufsicht")
    v_jaw_top.Source = [obj_left]
    v_jaw_top.Direction = FreeCAD.Vector(0, -1, 0)
    v_jaw_top.XDirection = FreeCAD.Vector(1, 0, 0)
    v_jaw_top.Scale = 1.5
    v_jaw_top.X = 205.0
    v_jaw_top.Y = 125.0
    page2.addView(v_jaw_top)

    add_dim_3d(
        page2, v_jaw_top, "Dim_Frontlippe_Ueberhang", "DistanceX",
        [(obj_left, (find_vertex(s_l, -PHONE_WIDTH_MIN / 2.0, -24, PHONE_THICKNESS),)),
         (obj_left, (find_vertex(s_l, -PHONE_WIDTH_MIN / 2.0 + FRONT_LIP_OVERHANG, -24, PHONE_THICKNESS),))],
        x=15.0, y=32.0,
    )
    add_dim_3d(
        page2, v_jaw_top, "Dim_Wandstaerke", "DistanceX",
        [(obj_left, (find_vertex(s_l, x_outer, -24, -CENTER_THICKNESS),)),
         (obj_left, (find_vertex(s_l, -PHONE_WIDTH_MIN / 2.0, -24, -CENTER_THICKNESS),))],
        x=-25.0, y=32.0,
    )
    add_dim_3d(
        page2, v_jaw_top, "Dim_Zungenlaenge", "DistanceX",
        [(obj_left, (find_vertex(s_l, -PHONE_WIDTH_MIN / 2.0, -RAIL_NECK_WIDTH / 2.0 + RAIL_CLEARANCE, 0),)),
         (obj_left, (find_vertex(s_l, -PHONE_WIDTH_MIN / 2.0 + TONGUE_LENGTH, -RAIL_NECK_WIDTH / 2.0 + RAIL_CLEARANCE, 0),))],
        x=10.0, y=-30.0,
    )


def main():
    doc = FreeCAD.newDocument("Garmin_Mobilphone_Halterung")

    center_shape = build_center_body()
    left_shape = build_jaw(side=-1)
    right_shape = build_jaw(side=1)

    obj_center = doc.addObject("Part::Feature", "Mittelteil_Garmin")
    obj_center.Shape = center_shape

    obj_left = doc.addObject("Part::Feature", "Klemmbacke_Links")
    obj_left.Shape = left_shape

    obj_right = doc.addObject("Part::Feature", "Klemmbacke_Rechts")
    obj_right.Shape = right_shape

    doc.recompute()

    # Add TechDraw technical drawings (2 A4 Landscape sheets with dimensions)
    add_techdraw_sheets(doc, obj_center, obj_left, obj_right)
    doc.recompute()

    # Save FreeCAD project
    fcstd_path = os.path.join(OUTPUT_DIR, "Garmin_Mobilphone_Halterung.FCStd")
    doc.saveAs(fcstd_path)
    print(f"Saved FreeCAD project: {fcstd_path}")

    # Export STLs for 3D printing
    export_stl(center_shape, "Mittelteil_Garmin.stl")
    export_stl(left_shape, "Klemmbacke_Links.stl")
    export_stl(right_shape, "Klemmbacke_Rechts.stl")

    # Export STEP assembly
    step_path = os.path.join(OUTPUT_DIR, "Garmin_Mobilphone_Halterung.step")
    Part.export([obj_center, obj_left, obj_right], step_path)
    print(f"Exported STEP: {step_path}")

    # Print bounding boxes for verification
    for name, shp in [("Mittelteil", center_shape), ("Links", left_shape), ("Rechts", right_shape)]:
        bb = shp.BoundBox
        print(f"  {name}: X[{bb.XMin:.1f}, {bb.XMax:.1f}] Y[{bb.YMin:.1f}, {bb.YMax:.1f}] Z[{bb.ZMin:.1f}, {bb.ZMax:.1f}] valid={shp.isValid()}")


if __name__ in ("__main__", "garmin_phone_mount"):
    main()
