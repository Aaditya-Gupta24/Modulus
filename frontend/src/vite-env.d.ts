/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Absolute API base for split deploys (e.g. HF static frontend → hosted API).
   *  Unset for same-origin single-service deploys, where the app uses "/api". */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
