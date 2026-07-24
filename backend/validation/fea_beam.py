"""Independent 1-D finite-element beam solver (Euler-Bernoulli).

Direct-stiffness method with 2-node Hermite cubic elements (DOFs: transverse
deflection w and rotation theta at each node). This module deliberately shares
NO code with modulus.beam -- it solves K d = F from first principles so it can
serve as an INDEPENDENT cross-check of the closed-form analytical model.
"""
import numpy as np


def _element_stiffness(EI, le):
    c = EI / le**3
    return c * np.array([
        [12,    6*le,   -12,    6*le],
        [6*le,  4*le*le, -6*le, 2*le*le],
        [-12,  -6*le,    12,   -6*le],
        [6*le,  2*le*le, -6*le, 4*le*le],
    ], dtype=float)


def solve(P, L, E, I, load_case, ne=200):
    """Return (max_deflection [m], max_moment [N*m]) from FE.

    load_case: 'cantilever_end' (fixed at x=0, point load P at x=L)
               'simply_center'  (pinned both ends, point load P at mid-span)
    """
    if load_case == "simply_center" and ne % 2:
        ne += 1                      # guarantee a node at mid-span
    nn = ne + 1
    le = L / ne
    EI = E * I
    ndof = 2 * nn

    K = np.zeros((ndof, ndof))
    ke = _element_stiffness(EI, le)
    for e in range(ne):
        d = [2*e, 2*e+1, 2*e+2, 2*e+3]
        K[np.ix_(d, d)] += ke

    F = np.zeros(ndof)
    if load_case == "cantilever_end":
        F[2*(nn-1)] = -P                      # downward load at free-end node
        fixed = [0, 1]                        # w and theta clamped at root
    elif load_case == "simply_center":
        mid = nn // 2
        F[2*mid] = -P
        fixed = [0, 2*(nn-1)]                 # w pinned at both ends
    else:
        raise ValueError(load_case)

    free = [i for i in range(ndof) if i not in fixed]
    d = np.zeros(ndof)
    d[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])

    max_defl = np.abs(d[0::2]).max()

    # Internal moments from element nodal forces f_e = ke @ d_e -> [V1,M1,V2,M2]
    max_moment = 0.0
    for e in range(ne):
        dofs = [2*e, 2*e+1, 2*e+2, 2*e+3]
        fe = ke @ d[dofs]
        max_moment = max(max_moment, abs(fe[1]), abs(fe[3]))
    return max_defl, max_moment
