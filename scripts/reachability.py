#!/usr/bin/env python3
import argparse
import numpy as np

def rpy(r, p, y):
    cr, sr = np.cos(r), np.sin(r); cp, sp = np.cos(p), np.sin(p)
    cy, sy = np.cos(y), np.sin(y)
    return (np.array([[cy,-sy,0],[sy,cy,0],[0,0,1]]) @
            np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]]) @
            np.array([[1,0,0],[0,cr,-sr],[0,sr,cr]]))

def T(xyz, r):
    M = np.eye(4); M[:3,:3] = rpy(*r); M[:3,3] = xyz; return M

def Rz(t):
    M = np.eye(4); c, s = np.cos(t), np.sin(t)
    M[0,0]=c; M[0,1]=-s; M[1,0]=s; M[1,1]=c; return M

pi = np.pi
JOINTS = [
    ([0,0,0.244],     [0,0,0],            -pi,   pi),
    ([-0.27,0,0.0],   [-pi/2,-pi/2,pi/2], -2.09, 2.09),
    ([0.686,0,-0.27], [0,pi,pi+pi/2],     -2.62, 2.62),
    ([0.519,0,0],     [0,pi,pi],          -pi,   pi),
    ([0.0,0,0.188],   [pi/2,pi,pi/2],     -2.09, 2.09),
    ([0.0,0,0.246],   [0,-pi/2,0],        -pi,   pi),
]
TAIL = [([0,0,0.086],[0,0,0]), ([0,0,0.185],[0,0,0])]

def fk(q):
    M = np.eye(4)
    for (xyz, r, _, _), t in zip(JOINTS, q):
        M = M @ T(xyz, r) @ Rz(t)
    for xyz, r in TAIL:
        M = M @ T(xyz, r)
    return M

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=200000)
    ap.add_argument("--out", default="reach.png")
    a = ap.parse_args()

    rng = np.random.default_rng(0)
    lo = np.array([j[2] for j in JOINTS])
    hi = np.array([j[3] for j in JOINTS])
    Q = rng.uniform(lo, hi, size=(a.samples, 6))

    P = np.empty((a.samples, 3))
    for i in range(a.samples):
        P[i] = fk(Q[i])[:3, 3]

    r = np.linalg.norm(P, axis=1)
    print(f"samples         : {a.samples}")
    print(f"max reach (m)   : {r.max():.3f}")
    print(f"X range (m)     : {P[:,0].min():.3f} .. {P[:,0].max():.3f}")
    print(f"Y range (m)     : {P[:,1].min():.3f} .. {P[:,1].max():.3f}")
    print(f"Z range (m)     : {P[:,2].min():.3f} .. {P[:,2].max():.3f}")
    for z in (0.2, 0.4, 0.6, 0.8):
        band = np.abs(P[:,2] - z) < 0.05
        if band.sum():
            rad = np.linalg.norm(P[band][:,:2], axis=1)
            print(f"  at z={z:.1f}m  radial {rad.min():.2f}..{rad.max():.2f} m")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        idx = rng.choice(a.samples, min(20000, a.samples), replace=False)
        S = P[idx]
        fig, ax = plt.subplots(1, 2, figsize=(13, 6))
        ax[0].scatter(S[:,0], S[:,1], s=0.4, alpha=0.25)
        ax[0].set_title("Top view (XY)"); ax[0].set_xlabel("x (m)")
        ax[0].set_ylabel("y (m)"); ax[0].axis("equal"); ax[0].grid(alpha=0.3)
        ax[1].scatter(np.linalg.norm(S[:,:2],axis=1), S[:,2], s=0.4, alpha=0.25)
        ax[1].axhline(0, color="k", lw=1)
        ax[1].set_title("Side view (radial vs Z)")
        ax[1].set_xlabel("radial distance (m)"); ax[1].set_ylabel("z (m)")
        ax[1].axis("equal"); ax[1].grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(a.out, dpi=110)
        print(f"\nsaved {a.out}")
    except ImportError:
        print("\nmatplotlib not installed")

if __name__ == "__main__":
    main()
