#!/usr/bin/env python3
"""Compute URDF <inertial> blocks from mesh files."""
import argparse, glob, os, sys
import numpy as np
import trimesh


def analyse(path, density, scale):
    mesh = trimesh.load(path, force="mesh")
    if scale != 1.0:
        mesh.apply_scale(scale)
    watertight = mesh.is_watertight
    if not watertight:
        mesh = mesh.convex_hull
    mesh.density = density
    I = mesh.moment_inertia
    eig = np.linalg.eigvalsh(I)
    a, b, c = sorted(eig)
    ok = bool((eig > 0).all()) and (a + b >= c)
    return {"name": os.path.splitext(os.path.basename(path))[0],
            "watertight": watertight, "volume": mesh.volume,
            "mass": mesh.mass, "com": mesh.center_mass, "I": I, "valid": ok}


def urdf_block(r):
    I, c = r["I"], r["com"]
    return (f'      <inertial>\n'
            f'        <origin xyz="{c[0]:.6f} {c[1]:.6f} {c[2]:.6f}" rpy="0 0 0"/>\n'
            f'        <mass value="{r["mass"]:.4f}"/>\n'
            f'        <inertia ixx="{I[0][0]:.6f}" ixy="{I[0][1]:.6f}" ixz="{I[0][2]:.6f}"\n'
            f'                 iyy="{I[1][1]:.6f}" iyz="{I[1][2]:.6f}" izz="{I[2][2]:.6f}"/>\n'
            f'      </inertial>')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mesh_dir")
    p.add_argument("--density", type=float, default=2700.0,
                   help="kg/m^3. Al=2700, steel=7850, ABS=1040, PLA=1240")
    p.add_argument("--scale", type=float, default=1.0,
                   help="Use 0.001 if meshes are in millimetres")
    a = p.parse_args()

    files = sorted(glob.glob(os.path.join(a.mesh_dir, "*.stl"))
                   + glob.glob(os.path.join(a.mesh_dir, "*.STL"))
                   + glob.glob(os.path.join(a.mesh_dir, "*.dae")))
    if not files:
        sys.exit(f"No meshes found in {a.mesh_dir}")

    print(f"density = {a.density} kg/m^3   scale = {a.scale}\n")
    print(f'{"link":<10} {"tight":<6} {"vol (m^3)":>12} {"mass (kg)":>10}  valid')
    print("-" * 52)
    results, total = [], 0.0
    for f in files:
        r = analyse(f, a.density, a.scale)
        results.append(r); total += r["mass"]
        print(f'{r["name"]:<10} {str(r["watertight"]):<6} '
              f'{r["volume"]:>12.6f} {r["mass"]:>10.4f}  {r["valid"]}')
    print("-" * 52)
    print(f'{"TOTAL":<10} {"":<6} {"":>12} {total:>10.4f}\n')
    print("=" * 52 + "\nURDF inertial blocks\n" + "=" * 52)
    for r in results:
        print(f'\n<!-- {r["name"]} -->')
        print(urdf_block(r))


if __name__ == "__main__":
    main()
