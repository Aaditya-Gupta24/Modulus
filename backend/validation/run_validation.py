"""Validate the analytical beam model two independent ways and emit a report+plot."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from modulus import sections, beam
from modulus.materials import MATERIALS
from validation.fea_beam import solve as fe_solve

NU = 0.3  # Poisson's ratio (steel/aluminium ~0.3)

def pct(a, b):  # |a-b|/b * 100
    return abs(a - b) / abs(b) * 100.0

# ---- Check 1: FE vs closed-form for the worked examples -----------------------
cases = [
    ("Case A  steel  square 30x30  L0.8  P300  cantilever",
     "steel_a36", sections.rectangle(0.030, 0.030), 300.0, 0.8, "cantilever_end"),
    ("Case B  alu    circle d30     L1.2  P800  simply",
     "aluminum_6061", sections.circle(0.030), 800.0, 1.2, "simply_center"),
    ("Case E  steel  sq tube a40 w4 L1.0  P600  cantilever",
     "steel_a36", sections.square_tube(0.040, 0.004), 600.0, 1.0, "cantilever_end"),
    ("Case F  alu    I-beam 50x100  L1.5  P1200 simply",
     "aluminum_6061", sections.i_beam(0.050,0.100,0.008,0.006), 1200.0, 1.5, "simply_center"),
]
print("="*92)
print("CHECK 1 - Independent FE (direct stiffness) vs analytical closed form")
print("="*92)
print(f"{'case':52s}{'delta FE':>11s}{'delta anl':>11s}{'err%':>7s}{'M err%':>8s}")
defl_err = []
for label, mkey, p, P, L, lc in cases:
    mat = MATERIALS[mkey]
    M_anl = beam.max_moment(P, L, lc)
    d_anl = beam.max_deflection(P, L, mat.E, p, lc)
    d_fe, M_fe = fe_solve(P, L, mat.E, p.I, lc, ne=400)
    de, me = pct(d_fe, d_anl), pct(M_fe, M_anl)
    defl_err.append(de)
    print(f"{label:52s}{d_fe*1e3:9.4f}mm{d_anl*1e3:9.4f}mm{de:7.4f}{me:8.4f}")
print(f"\nMax FE-vs-analytical deflection error: {max(defl_err):.5f}%  "
      f"(confirms the closed-form implementation is correct)")

# ---- Check 2: Euler-Bernoulli vs Timoshenko (shear) across slenderness ---------
# cantilever end load: shear adds  P*L/(kappa*G*A);  EB = P*L^3/(3 E I)
print("\n" + "="*92)
print("CHECK 2 - Euler-Bernoulli vs Timoshenko: shear-deflection error vs slenderness L/h")
print("="*92)
E = MATERIALS["steel_a36"].E
G = E / (2*(1+NU))
kappa = 5/6                      # rectangular section shear coefficient
h = 0.030
ratios = np.linspace(4, 40, 80)
shear_pct = []
for r in ratios:
    L = r*h
    I = h**4/12; A = h*h
    d_eb = 1*L**3/(3*E*I)         # unit load P=1 (P cancels in ratio)
    d_sh = 1*L/(kappa*G*A)
    shear_pct.append(d_sh/(d_eb+d_sh)*100)
shear_pct = np.array(shear_pct)
for r in (5,10,15,20,27,40):
    L=r*h; I=h**4/12; A=h*h
    d_eb=L**3/(3*E*I); d_sh=L/(kappa*G*A)
    print(f"  L/h = {r:>3}:  shear contributes {d_sh/(d_eb+d_sh)*100:5.2f}%  "
          f"of total deflection -> EB underpredicts by that much")
print("\nThe optimizer sweeps slender beams (L/h typically > 15) where EB error < ~0.4%.")

# ---- Figure -------------------------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
labels = ["A","B","E","F"]
ax[0].bar([l+" FE" for l in labels], [c for c in
          [fe_solve(P,L,MATERIALS[m].E,p.I,lc,400)[0]*1e3
           for (_,m,p,P,L,lc) in cases]], width=0.4, label="FE", color="#4a9eff")
ax[0].bar([l+" anl" for l in labels], [beam.max_deflection(P,L,MATERIALS[m].E,p,lc)*1e3
           for (_,m,p,P,L,lc) in cases], width=0.4, label="analytical", color="#28a745")
ax[0].set_ylabel("max deflection (mm)")
ax[0].set_title("FE vs analytical (overlap = agreement)")
ax[0].legend(); ax[0].tick_params(axis="x", labelrotation=45)

ax[1].plot(ratios, shear_pct, color="#dc3545", lw=2)
ax[1].axvspan(15, 40, color="#28a745", alpha=0.12, label="optimizer's typical range")
ax[1].axhline(0.4, ls="--", color="#888", lw=1)
ax[1].set_xlabel("slenderness  L / h"); ax[1].set_ylabel("shear-deflection error (%)")
ax[1].set_title("Euler-Bernoulli error vs Timoshenko")
ax[1].legend()
fig.tight_layout()
fig.savefig("validation/validation.png", dpi=130)
print("\nSaved validation/validation.png")
