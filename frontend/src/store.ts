// Tiny cross-view store for the most recent Beam Optimizer problem, so the
// Compare view can reflect your latest run. Persisted to localStorage because
// App remounts each view on navigation (key={activeView}) — plain React state
// would be lost. Falls back to sensible defaults until the optimizer is run.

export interface BeamProblem {
  load: number;               // N
  length: number;             // m
  load_case: string;
  fos_target: number;
  deflection_limit: number | null;  // m
  material_keys: string[];
  section_types: string[];
  stock_mode: boolean;
}

export const DEFAULT_PROBLEM: BeamProblem = {
  load: 1000,
  length: 1.0,
  load_case: 'cantilever_end',
  fos_target: 2.0,
  deflection_limit: 0.005,
  material_keys: [
    'aluminum_6061', 'steel_a36', 'pla',
    'titanium_ti6al4v', 'brass_360', 'abs_plastic',
  ],
  section_types: [
    'rectangle', 'circle', 'i_beam',
    'hollow_rectangle', 'square_tube', 'hollow_circle',
  ],
  stock_mode: false,
};

const KEY = 'modulus:lastBeamProblem';

export function saveBeamProblem(problem: BeamProblem): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(problem));
  } catch {
    /* storage unavailable (private mode, etc.) — Compare uses defaults */
  }
}

export function loadBeamProblem(): BeamProblem {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...DEFAULT_PROBLEM, ...(JSON.parse(raw) as Partial<BeamProblem>) };
  } catch {
    /* ignore malformed / unavailable storage */
  }
  return DEFAULT_PROBLEM;
}
