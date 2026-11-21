"""Generate QR Code + A4 Landscape Technical Drawing (TechDraw in FCStd + PDF)
for the Statically Optimized Garmin Pixel 6 Mount.

Run with FreeCAD:
  "C:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe" make_drawing.py
"""

import os
import math
import subprocess
import FreeCAD
import Part
import TechDraw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FCSTD_PATH = os.path.join(SCRIPT_DIR, "Garmin_Pixel6_Halterung_Optimiert.FCStd")
STEP_PATH = os.path.join(SCRIPT_DIR, "Garmin_Pixel6_Halterung_Optimiert.step")
QR_PNG_PATH = os.path.join(SCRIPT_DIR, "qr_ar_fem.png")
PDF_OUT_PATH = os.path.join(SCRIPT_DIR, "Zeichnung_Garmin_Pixel6_Optimiert.pdf")
AR_URL = "https://lugulugumore.github.io/freecad/"


SYS_PYTHON = r"C:\Users\lmorett\AppData\Local\Microsoft\WindowsApps\python.exe"


def generate_qr():
    """Generate QR code PNG using system python (where qrcode is installed)."""
    cmd = [
        SYS_PYTHON, "-c",
        (
            "import qrcode; "
            f"qr = qrcode.QRCode(version=2, box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M); "
            f"qr.add_data('{AR_URL}'); qr.make(fit=True); "
            f"img = qr.make_image(fill_color='black', back_color='white'); "
            f"img.save(r'{QR_PNG_PATH}')"
        ),
    ]
    subprocess.check_call(cmd)
    print("Generated QR code:", QR_PNG_PATH)


def add_techdraw_page(doc, part_obj):
    """Add an A4 Landscape TechDraw page with views and QR code into FCStd."""
    existing = doc.getObject("Zeichnung_Halterung")
    if existing:
        doc.removeObject("Zeichnung_Halterung")

    tmpl_path = os.path.join(
        FreeCAD.getResourceDir(),
        "Mod", "TechDraw", "Templates", "A4_Landscape_ISO5457_minimal.svg",
    )
    page = doc.addObject("TechDraw::DrawPage", "Zeichnung_Halterung")
    tmpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template_Halterung")
    tmpl.Template = tmpl_path
    page.Template = tmpl

    # Front View (-Y -> +Y)
    v_front = doc.addObject("TechDraw::DrawViewPart", "Vorderansicht")
    v_front.Source = [part_obj]
    v_front.Direction = FreeCAD.Vector(0, -1, 0)
    v_front.XDirection = FreeCAD.Vector(1, 0, 0)
    v_front.Scale = 1.0
    v_front.X = 65.0
    v_front.Y = 120.0
    page.addView(v_front)

    # Back View (+Y -> -Y, Garmin Bayonet + Ribs)
    v_back = doc.addObject("TechDraw::DrawViewPart", "Rueckansicht")
    v_back.Source = [part_obj]
    v_back.Direction = FreeCAD.Vector(0, 1, 0)
    v_back.XDirection = FreeCAD.Vector(-1, 0, 0)
    v_back.Scale = 1.0
    v_back.X = 165.0
    v_back.Y = 120.0
    page.addView(v_back)

    # Side View (+X -> -X)
    v_side = doc.addObject("TechDraw::DrawViewPart", "Seitenansicht")
    v_side.Source = [part_obj]
    v_side.Direction = FreeCAD.Vector(1, 0, 0)
    v_side.XDirection = FreeCAD.Vector(0, 1, 0)
    v_side.Scale = 1.0
    v_side.X = 245.0
    v_side.Y = 120.0
    page.addView(v_side)

    # QR Code Image on TechDraw sheet
    qr_view = doc.addObject("TechDraw::DrawViewImage", "QR_Code_AR")
    qr_view.ImageFile = QR_PNG_PATH
    qr_view.Width = 34.0
    qr_view.Height = 34.0
    qr_view.X = 262.0
    qr_view.Y = 48.0
    page.addView(qr_view)

    doc.recompute()
    doc.save()
    print("Updated TechDraw sheet in:", FCSTD_PATH)


def project_edges_to_2d(shape, direction, x_dir):
    """Use FreeCAD TechDraw.projectEx (OpenCASCADE HLR) to get 2D visible & hidden polylines."""
    # projectEx returns [V, V1, VOut, H, H1, HOut] compounds
    res = TechDraw.projectEx(shape, direction)
    # Build orthonormal basis (u = x_dir, w = direction, v = w x u)
    w = direction.normalize()
    u = x_dir.normalize()
    v = w.cross(u).normalize()

    def edges_to_pts(compound):
        polylines = []
        if compound is None or compound.isNull():
            return polylines
        for e in compound.Edges:
            pts = e.discretize(Deflection=0.05)
            polylines.append([(p.x, p.y) for p in pts])
        return polylines

    # TechDraw.projectEx already projects into X-Y plane oriented to Z=direction,
    # Wait: projectEx uses standard Z-up unless we rotate shape or use projectToSVG.
    # Let's check: projectToSVG gives exact SVG paths in (u, v) plane!
    return res


def render_pdf_drawing():
    """Render an A4 Landscape vector PDF with CAD projections, dimensions, title block & QR code."""
    import json
    shape = Part.Shape()
    shape.read(STEP_PATH)

    def project_view_polylines(shp, rot1_axis, rot1_deg, rot2_axis=None, rot2_deg=0):
        s_copy = shp.copy()
        if rot1_deg != 0:
            s_copy.rotate(FreeCAD.Vector(0, 0, 0), rot1_axis, rot1_deg)
        if rot2_axis is not None and rot2_deg != 0:
            s_copy.rotate(FreeCAD.Vector(0, 0, 0), rot2_axis, rot2_deg)
        res = TechDraw.projectEx(s_copy, FreeCAD.Vector(0, 0, 1))
        # res = [V, V1, VOut, H, H1, HOut]
        def extract(compounds):
            out = []
            for comp in compounds:
                if comp is None or comp.isNull():
                    continue
                for e in comp.Edges:
                    pts = e.discretize(Deflection=0.05)
                    out.append([[round(p.x, 3), round(p.y, 3)] for p in pts])
            return out
        vis = extract(res[0:3])
        hid = extract(res[3:6])
        return {"vis": vis, "hid": hid}

    # Back (+Y toward camera): rotate +90 around X -> +Y maps to +Z, +Z maps to -Y (flip_y in plot)
    v_back = project_view_polylines(shape, FreeCAD.Vector(1, 0, 0), 90)
    # Front (-Y toward camera): rotate -90 around X -> -Y maps to +Z, +Z maps to +Y
    v_front = project_view_polylines(shape, FreeCAD.Vector(1, 0, 0), -90)
    # Side (+X toward camera, Z vertical): rotate -90 around Z, then -90 around X
    v_side = project_view_polylines(shape, FreeCAD.Vector(0, 0, 1), -90, FreeCAD.Vector(1, 0, 0), -90)

    views_json = os.path.join(SCRIPT_DIR, "fem_ccx_tmp", "views_poly.json")
    with open(views_json, "w") as f:
        json.dump({"front": v_front, "back": v_back, "side": v_side}, f)

    plot_script = os.path.join(SCRIPT_DIR, "fem_ccx_tmp", "_build_pdf.py")
    with open(plot_script, "w", encoding="utf-8") as f:
        f.write(f'''
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image

with open(r"{views_json}") as f:
    views = json.load(f)

# A4 Landscape: 297 x 210 mm
fig = plt.figure(figsize=(297/25.4, 210/25.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 297)
ax.set_ylim(0, 210)
ax.set_aspect('equal')
ax.axis('off')

# Outer ISO border
ax.add_patch(patches.Rectangle((10, 10), 277, 190, fill=False, lw=1.2, ec='black'))

def draw_view(vdata, cx, cy, label, flip_y=False):
    vis = [np.array(p) for p in vdata["vis"] if len(p) >= 2]
    hid = [np.array(p) for p in vdata["hid"] if len(p) >= 2]
    if flip_y:
        vis = [np.column_stack([p[:,0], -p[:,1]]) for p in vis]
        hid = [np.column_stack([p[:,0], -p[:,1]]) for p in hid]
    all_pts = np.vstack(vis)
    mx = (all_pts[:,0].min() + all_pts[:,0].max()) / 2
    my = (all_pts[:,1].min() + all_pts[:,1].max()) / 2
    for p in hid:
        ax.plot(p[:,0] - mx + cx, p[:,1] - my + cy, color='#94a3b8', lw=0.4, ls='--')
    for p in vis:
        ax.plot(p[:,0] - mx + cx, p[:,1] - my + cy, color='black', lw=0.85)
    ax.text(cx, cy + (all_pts[:,1].max() - all_pts[:,1].min()) / 2 + 12, label,
            ha='center', va='bottom', fontsize=9, fontweight='bold')
    return (
        all_pts[:,0].min() - mx + cx, all_pts[:,0].max() - mx + cx,
        all_pts[:,1].min() - my + cy, all_pts[:,1].max() - my + cy,
    )

b_front = draw_view(views['front'], 62, 118, "VORDERANSICHT (1:1)")
b_back  = draw_view(views['back'], 162, 118, "RÜCKANSICHT – GARMIN & RIPPEN (1:1)", flip_y=True)
b_side  = draw_view(views['side'], 245, 118, "SEITENANSICHT (1:1)")

def dim_h(x1, x2, y_line, y_ext1, text):
    ax.plot([x1, x1], [y_ext1, y_line + (2 if y_line > y_ext1 else -2)], 'k-', lw=0.4)
    ax.plot([x2, x2], [y_ext1, y_line + (2 if y_line > y_ext1 else -2)], 'k-', lw=0.4)
    ax.annotate('', xy=(x1, y_line), xytext=(x2, y_line),
                arrowprops=dict(arrowstyle='<->', lw=0.6, color='black'))
    ax.text((x1+x2)/2, y_line + 1.5, text, ha='center', va='bottom', fontsize=8)

def dim_v(y1, y2, x_line, x_ext1, text):
    ax.plot([x_ext1, x_line + (2 if x_line > x_ext1 else -2)], [y1, y1], 'k-', lw=0.4)
    ax.plot([x_ext1, x_line + (2 if x_line > x_ext1 else -2)], [y2, y2], 'k-', lw=0.4)
    ax.annotate('', xy=(x_line, y1), xytext=(x_line, y2),
                arrowprops=dict(arrowstyle='<->', lw=0.6, color='black'))
    ax.text(x_line - 2, (y1+y2)/2, text, ha='right', va='center', rotation=90, fontsize=8)

# Dimensions on Front View
dim_h(b_front[0], b_front[1], b_front[2] - 10, b_front[2], "87,0 mm (Außen)")
dim_h(b_front[0] + 3.5, b_front[1] - 3.5, b_front[2] - 19, b_front[2] + 5, "80,0 mm (Innen)")
dim_v(b_front[2], b_front[3], b_front[0] - 8, b_front[0], "93,5 mm")
dim_v(b_front[2], b_front[2] + 16.0, b_front[1] + 8, b_front[1], "16,0 mm")

# Dimensions on Back View
dim_h(162 - 19.0, 162 + 19.0, b_back[3] + 5, b_back[3], "38,0 mm (Steg)")
dim_h(162 - 14.25, 162 + 14.25, b_back[2] - 10, b_back[2] + 15, "Ø 28,5 mm (Garmin)")

# Dimensions on Side View
dim_h(b_side[0], b_side[1], b_side[2] - 10, b_side[2], "24,7 mm (Gesamt)")
dim_h(b_side[0] + 3.0, b_side[0] + 16.2, b_side[3] + 5, b_side[3], "13,2 mm (Tiefe)")

# Title Block (bottom right)
ax.add_patch(patches.Rectangle((150, 10), 137, 36, fill=False, lw=0.9, ec='black'))
ax.plot([150, 287], [22, 22], 'k-', lw=0.5)
ax.plot([150, 287], [34, 34], 'k-', lw=0.5)
ax.plot([243, 243], [10, 46], 'k-', lw=0.5)
ax.text(153, 40, "Garmin Pixel 6 Halterung – Statisch Optimiert", fontsize=8.5, fontweight='bold', va='center')
ax.text(153, 28, "Material: PETG (FEM: 50 N / 20g -> Max 36,7 MPa)", fontsize=7.5, va='center')
ax.text(153, 16, "Maßstab: 1:1   |   Einheit: mm   |   Blatt: A4 Quer", fontsize=7.5, va='center')
ax.text(265, 40, "AR FEM-Ansicht", fontsize=8, fontweight='bold', ha='center', va='center')
ax.text(265, 28, "QR-Code scannen:", fontsize=7, ha='center', va='center')
ax.text(265, 16, "lugulugumore.github.io", fontsize=6.5, ha='center', va='center')

# Embed QR code inside dedicated box
qr_box = patches.Rectangle((112, 10), 38, 36, fill=False, lw=0.9, ec='black')
ax.add_patch(qr_box)
qr_img = np.array(Image.open(r"{QR_PNG_PATH}").convert("RGB"))
imagebox = OffsetImage(qr_img, zoom=0.28)
ab = AnnotationBbox(imagebox, (131, 30), frameon=False)
ax.add_artist(ab)
ax.text(131, 12.5, "3D FEM in AR", ha='center', va='center', fontsize=7, fontweight='bold')

fig.savefig(r"{PDF_OUT_PATH}")
print("Saved PDF:", r"{PDF_OUT_PATH}")
''')
    subprocess.check_call([SYS_PYTHON, plot_script])


def main():
    generate_qr()
    doc = FreeCAD.openDocument(FCSTD_PATH)
    part_obj = doc.getObject("Garmin_Pixel6_Halterung")
    if part_obj:
        add_techdraw_page(doc, part_obj)
    render_pdf_drawing()


main()
