#!/usr/bin/env python3
"""Shaded solid render of a GLB in its declared glTF Y-up pose (rotated to Z-up for display), for scorecard thumbnails.
Usage: python3 scripts/render_thumb.py gens/<gen>/T01.glb out.png  (needs fast_simplification for decimation)."""
import sys, numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
def render(path, out, elev=20, azim=-60, size=4, maxf=60000, rot_yup=True):
    s=trimesh.load(path); m=s.to_geometry() if hasattr(s,'to_geometry') else s
    m.update_faces(m.nondegenerate_faces()) if hasattr(m,'nondegenerate_faces') else None
    m.remove_unreferenced_vertices()
    if len(m.faces)>maxf:
        try: m=m.simplify_quadric_decimation(face_count=maxf)
        except Exception as e:
            print("simplify failed", e, file=sys.stderr)
            idx=np.random.default_rng(0).choice(len(m.faces),maxf,replace=False); m=trimesh.Trimesh(m.vertices,m.faces[idx])
    v=m.vertices.copy()
    if rot_yup: v=np.c_[v[:,0],-v[:,2],v[:,1]]  # Y-up -> Z-up
    v-=v.mean(0); tri=v[m.faces]
    n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); n/=np.linalg.norm(n,axis=1,keepdims=True)+1e-12
    L=np.array([0.4,-0.6,0.7]); L/=np.linalg.norm(L)
    sh=0.25+0.75*np.abs(n@L)
    base=np.array([0.23,0.45,0.85])
    col=np.clip(base[None]*sh[:,None]+0.08,0,1)
    fig=plt.figure(figsize=(size,size),dpi=100); ax=fig.add_subplot(111,projection='3d')
    pc=Poly3DCollection(tri,facecolors=col,edgecolors='none',linewidths=0); ax.add_collection3d(pc)
    r=np.abs(v).max(); ax.set_xlim(-r,r); ax.set_ylim(-r,r); ax.set_zlim(-r,r); ax.set_box_aspect((1,1,1))
    ax.view_init(elev=elev,azim=azim); ax.set_axis_off(); fig.subplots_adjust(0,0,1,1)
    fig.savefig(out,transparent=False,facecolor='white'); plt.close(fig)
if __name__=="__main__":
    render(sys.argv[1],sys.argv[2])
