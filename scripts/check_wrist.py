#!/usr/bin/env python3
"""Check whether joints 4,5,6 axes intersect (spherical wrist)."""
import numpy as np

def rpy(r, p, y):
    cr, sr = np.cos(r), np.sin(r); cp, sp = np.cos(p), np.sin(p)
    cy, sy = np.cos(y), np.sin(y)
    return (np.array([[cy,-sy,0],[sy,cy,0],[0,0,1]]) @
            np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]]) @
            np.array([[1,0,0],[0,cr,-sr],[0,sr,cr]]))

def T(xyz, r):
    M = np.eye(4); M[:3,:3] = rpy(*r); M[:3,3] = xyz; return M

pi = np.pi
joints = [
    ("joint_1", [0,0,0.244],      [0,0,0]),
    ("joint_2", [-0.27,0,0.0],    [-pi/2,-pi/2,pi/2]),
    ("joint_3", [0.686,0,-0.27],  [0,pi,pi+pi/2]),
    ("joint_4", [0.519,0,0],      [0,pi,pi]),
    ("joint_5", [0.0,0,0.188],    [pi/2,pi,pi/2]),
    ("joint_6", [0.0,0,0.246],    [0,-pi/2,0]),
]

M = np.eye(4)
origins, axes = [], []
for name, xyz, r in joints:
    M = M @ T(xyz, r)
    origins.append(M[:3,3].copy())
    axes.append(M[:3,2].copy())          # joint axis is local Z
    print(f"{name}: origin={M[:3,3].round(4)}  axis={M[:3,2].round(4)}")

def dist(p1,d1,p2,d2):
    n = np.cross(d1,d2); nn = np.linalg.norm(n)
    if nn < 1e-9:
        return np.linalg.norm(np.cross(p2-p1,d1))    # parallel
    return abs(np.dot(p2-p1, n/nn))

print("\nPairwise axis distances (wrist joints):")
for (i,j) in [(3,4),(4,5),(3,5)]:
    d = dist(origins[i],axes[i],origins[j],axes[j])
    print(f"  joint_{i+1} <-> joint_{j+1}: {d*1000:.3f} mm")

d45 = dist(origins[3],axes[3],origins[4],axes[4])
d56 = dist(origins[4],axes[4],origins[5],axes[5])
d46 = dist(origins[3],axes[3],origins[5],axes[5])
print("\nSPHERICAL WRIST" if max(d45,d56,d46) < 1e-4 else "\nNOT a spherical wrist")
