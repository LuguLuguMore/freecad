"""3D Linear-Static FEM Analysis (Gmsh + CalculiX) for the Optimized Pixel 6 Garmin Mount.

Load Case (Toddler Pull-Down Test):
  - Material: 3D-printed PETG (E = 2100 MPa, nu = 0.35, conservative yield = 35 MPa)
  - Fixed Support: Garmin quarter-turn bayonet (locked into handlebar mount)
  - Load: 50 N (~5 kg) downward force (-Z) on the top hook / tab ("Lasche nach unten gezogen")

Run with FreeCAD:
  "C:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe" run_fem.py
"""

import math
import os
import subprocess
import FreeCAD
import Part
import Fem
import ObjectsFem
from femmesh import gmshtools
from femtools import ccxtools

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STEP_PATH = os.path.join(SCRIPT_DIR, "Garmin_Pixel6_Halterung_Optimiert.step")
FCSTD_FEM_PATH = os.path.join(SCRIPT_DIR, "Garmin_Pixel6_Halterung_FEM.FCStd")
CCX_WORK_DIR = os.path.join(SCRIPT_DIR, "fem_ccx_tmp")
os.makedirs(CCX_WORK_DIR, exist_ok=True)


def select_faces_by_predicate(part_obj, pred):
    """Return list of face names ('Face1', ...) matching pred(face)."""
    names = []
    for idx, face in enumerate(part_obj.Shape.Faces, start=1):
        if pred(face):
            names.append(f"Face{idx}")
    return names


def main():
    doc = FreeCAD.newDocument("Garmin_Pixel6_FEM")
    shape = Part.Shape()
    shape.read(STEP_PATH)

    part_obj = doc.addObject("Part::Feature", "Mount")
    part_obj.Shape = shape
    doc.recompute()

    # 1. FEM Analysis container
    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")

    # 2. Material: PETG
    mat = ObjectsFem.makeMaterialSolid(doc, "PETG")
    mat.Material = {
        "Name": "PETG-3DPrint",
        "YoungsModulus": "2100 MPa",
        "PoissonRatio": "0.35",
        "Density": "1270 kg/m^3",
    }
    analysis.addObject(mat)

    # 3. Fixed support on Garmin bayonet (Y > 4.05, radius <= 14.5 around X=0, Z=15)
    fixed_faces = select_faces_by_predicate(
        part_obj,
        lambda f: (
            f.CenterOfMass.y > 4.05
            and math.hypot(f.CenterOfMass.x, f.CenterOfMass.z - 15.0) <= 14.5
        ),
    )
    print(f"Fixed Garmin faces ({len(fixed_faces)}):", fixed_faces)
    fixed = ObjectsFem.makeConstraintFixed(doc, "Fixed_Garmin_Bayonet")
    fixed.References = [(part_obj, f) for f in fixed_faces]
    analysis.addObject(fixed)

    # 4. Force on top hook / tab: 50 N downward (-Z) ("Kleinkind zieht Lasche nach unten")
    top_load_faces = select_faces_by_predicate(
        part_obj,
        lambda f: (
            f.CenterOfMass.z >= 87.0
            and f.CenterOfMass.y <= -4.0
        ),
    )
    print(f"Top hook load faces ({len(top_load_faces)}):", top_load_faces)
    force_top = ObjectsFem.makeConstraintForce(doc, "Force_Top_Hook_Down_50N")
    force_top.References = [(part_obj, f) for f in top_load_faces]
    force_top.Force = "50.0 N"
    # Find a flat Z-normal face to set -Z direction
    z_norm_faces = select_faces_by_predicate(
        part_obj,
        lambda f: abs(abs(f.normalAt(0, 0).z) - 1.0) < 0.01 and f.Area > 5.0,
    )
    if z_norm_faces:
        ref_face_name = z_norm_faces[0]
        ref_face = getattr(part_obj.Shape, ref_face_name)
        nz = ref_face.normalAt(0, 0).z
        force_top.Direction = (part_obj, [ref_face_name])
        force_top.Reversed = (nz > 0)  # want -Z (downward)
    analysis.addObject(force_top)

    # 6. Gmsh 3D tetrahedral mesh (2nd order C3D10 for accurate bending)
    mesh_obj = ObjectsFem.makeMeshGmsh(doc, "FEMMeshGmsh")
    mesh_obj.Shape = part_obj
    mesh_obj.CharacteristicLengthMax = 3.0
    mesh_obj.CharacteristicLengthMin = 1.0
    mesh_obj.ElementOrder = "2nd"
    analysis.addObject(mesh_obj)

    doc.recompute()

    print("Running Gmsh...")
    gmsh_runner = gmshtools.GmshTools(mesh_obj)
    err = gmsh_runner.create_mesh()
    if err:
        print("Gmsh message:", err)
    fem_mesh = mesh_obj.FemMesh
    print(f"Mesh: {fem_mesh.NodeCount} nodes, {fem_mesh.VolumeCount} volume elements")

    # 7. CalculiX Solver
    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "CalculiXCcxTools")
    solver.WorkingDir = CCX_WORK_DIR
    solver.AnalysisType = "static"
    solver.GeometricalNonlinearity = "linear"
    solver.ThermoMechSteadyState = False
    solver.MatrixSolverType = "default"
    solver.IterationsControlParameterTimeUse = False
    analysis.addObject(solver)
    doc.recompute()

    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    fea.setup_working_dir(CCX_WORK_DIR)
    fea.setup_ccx()
    msg = fea.check_prerequisites()
    if msg:
        print("Prerequisites warning:", msg)
    fea.write_inp_file()
    print("Wrote INP file:", fea.inp_file_name)

    print("Running CalculiX ccx...")
    fea.run()
    fea.load_results()
    doc.recompute()

    # 8. Extract & print results
    results = None
    for obj in analysis.Group:
        if obj.isDerivedFrom("Fem::FemResultObject"):
            results = obj
            break

    if results is None:
        print("ERROR: No FEM result object found!")
        return

    von_mises = results.vonMises
    disp_lengths = results.DisplacementLengths
    max_vm = max(von_mises)
    max_disp = max(disp_lengths)

    # Find node coordinates of max von Mises stress
    max_idx = von_mises.index(max_vm)
    node_id = results.Mesh.FemMesh.Nodes
    # Result node order matches mesh node IDs (1..N)
    max_node_pos = results.Mesh.FemMesh.getNodeById(max_idx + 1)

    yield_petg = 35.0
    sf_petg = yield_petg / max_vm if max_vm > 0 else float("inf")

    print("\n=== FEM RESULTS (PETG, 50 N Downward / Toddler Pull) ===")
    print(f"Max Displacement:      {max_disp:.3f} mm")
    print(f"Max von Mises Stress:  {max_vm:.2f} MPa")
    print(f"Max Stress Location:   ({max_node_pos.x:.1f}, {max_node_pos.y:.1f}, {max_node_pos.z:.1f}) mm")
    print(f"Safety Factor (PETG 35 MPa): {sf_petg:.2f}")

    # Export node coords + vonMises for plotting
    out_csv = os.path.join(CCX_WORK_DIR, "fem_nodes_stress.csv")
    with open(out_csv, "w") as f:
        f.write("x,y,z,vonMises,disp\n")
        for nid, vm, dl in zip(sorted(node_id.keys()), von_mises, disp_lengths):
            p = node_id[nid]
            f.write(f"{p.x:.4f},{p.y:.4f},{p.z:.4f},{vm:.4f},{dl:.4f}\n")
    print("Saved nodal stress CSV:", out_csv)

    doc.saveAs(FCSTD_FEM_PATH)
    print("Saved FEM FreeCAD document:", FCSTD_FEM_PATH)


main()
