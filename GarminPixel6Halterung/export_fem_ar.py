"""Export exterior surface mesh + nodal von Mises stress & displacement vectors
from Garmin_Pixel6_Halterung_FEM.FCStd into a compact JSON for Three.js / WebXR AR.

Run with FreeCAD:
  "C:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe" export_fem_ar.py
"""

import collections
import json
import os
import FreeCAD

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FCSTD_FEM_PATH = os.path.join(SCRIPT_DIR, "Garmin_Pixel6_Halterung_FEM.FCStd")
OUT_JSON = os.path.join(SCRIPT_DIR, "fem_ar_data.json")


def main():
    doc = FreeCAD.openDocument(FCSTD_FEM_PATH)
    analysis = doc.getObject("Analysis")
    results = None
    mesh_obj = None
    for obj in analysis.Group:
        if obj.isDerivedFrom("Fem::FemResultObject") and obj.Name == "CCX_Results":
            results = obj
        elif obj.isDerivedFrom("Fem::FemMeshObject"):
            mesh_obj = obj

    if results is None or mesh_obj is None:
        raise RuntimeError("Could not find CCX_Results or FEMMeshGmsh in FEM document")

    fmesh = mesh_obj.FemMesh
    nodes = fmesh.Nodes  # dict: node_id -> Vector
    volumes = fmesh.Volumes  # tuple of volume element IDs

    # Extract all triangular faces of 1st-order corner nodes of each tetrahedron.
    # Corner nodes of C3D10 / C3D4 are the first 4 nodes of getElementNodes(vid).
    face_count = collections.Counter()
    face_oriented = {}
    for vid in volumes:
        en = fmesh.getElementNodes(vid)
        n0, n1, n2, n3 = en[0], en[1], en[2], en[3]
        # 4 faces of tetrahedron (with consistent outward/inward winding)
        tet_faces = [
            (n0, n2, n1),
            (n0, n1, n3),
            (n1, n2, n3),
            (n2, n0, n3),
        ]
        for tri in tet_faces:
            key = tuple(sorted(tri))
            face_count[key] += 1
            face_oriented[key] = tri

    boundary_tris = [face_oriented[k] for k, cnt in face_count.items() if cnt == 1]
    print(f"Total volumes: {len(volumes)}, Boundary surface triangles: {len(boundary_tris)}")

    # Map used node IDs to compact 0..M-1 indices
    used_nids = sorted({nid for tri in boundary_tris for nid in tri})
    nid_to_idx = {nid: i for i, nid in enumerate(used_nids)}

    # Results arrays are ordered by sorted node IDs (1..N)
    # Build lookup from node_id -> (vonMises, dispVec, dispLen)
    all_nids = sorted(nodes.keys())
    vm_map = {nid: float(vm) for nid, vm in zip(all_nids, results.vonMises)}
    dv_map = {nid: dv for nid, dv in zip(all_nids, results.DisplacementVectors)}
    dl_map = {nid: float(dl) for nid, dl in zip(all_nids, results.DisplacementLengths)}

    # Center the geometry around (0, 0, 0) for clean AR placement (in meters or mm)
    xs = [nodes[nid].x for nid in used_nids]
    ys = [nodes[nid].y for nid in used_nids]
    zs = [nodes[nid].z for nid in used_nids]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    cz = min(zs)  # place bottom on Z=0 (or Y=0 in Three.js)

    positions = []
    displacements = []
    von_mises = []
    disp_mags = []

    for nid in used_nids:
        p = nodes[nid]
        dv = dv_map[nid]
        # Convert FreeCAD (X, Y, Z_up) -> Three.js (X, Y_up=Z, Z=-Y) in mm
        positions.extend([round(p.x - cx, 3), round(p.z - cz, 3), round(-(p.y - cy), 3)])
        displacements.extend([round(dv.x, 4), round(dv.z, 4), round(-dv.y, 4)])
        von_mises.append(round(vm_map[nid], 3))
        disp_mags.append(round(dl_map[nid], 4))

    indices = []
    for a, b, c in boundary_tris:
        indices.extend([nid_to_idx[a], nid_to_idx[b], nid_to_idx[c]])

    payload = {
        "meta": {
            "part": "Garmin Pixel 6 Halterung (Statisch Optimiert)",
            "material": "PETG (E = 2100 MPa, nu = 0.35)",
            "loadCase": "50 N Zug nach unten (-Z, Kleinkind-Lastfall), Garmin fixiert",
            "maxVonMisesMPa": round(max(von_mises), 2),
            "maxDispMm": round(max(disp_mags), 3),
            "safetyFactorPetg35": round(35.0 / max(von_mises), 2),
            "nodeCount": len(used_nids),
            "triCount": len(boundary_tris),
            "unit": "mm",
        },
        "positions": positions,
        "displacements": displacements,
        "vonMises": von_mises,
        "dispMag": disp_mags,
        "indices": indices,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))

    size_kb = os.path.getsize(OUT_JSON) / 1024.0
    print(f"Exported {OUT_JSON} ({size_kb:.1f} KB)")


main()
