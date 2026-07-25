---
title: Modulus
emoji: 🔩
colorFrom: blue
colorTo: gray
sdk: static
pinned: false
license: mit
short_description: Structural design optimization for beams and brackets
---

# Modulus

Structural design optimization engine — sweeps materials, cross-sections, and
dimensions to size beams and brackets by factor of safety, weight, and cost,
validated against an independent finite-element solver.

This **static** Space hosts the React frontend; it calls the Modulus API
(FastAPI) hosted separately. The frontend build here is produced with
`VITE_API_URL` pointing at that API. Free HF Spaces only run static sites — Docker
and Gradio Spaces require a PRO plan — which is why the Python API lives elsewhere.

**Source & docs:** https://github.com/Aaditya-Gupta24/Modulus
