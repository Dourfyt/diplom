/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MODULE_API_URL?: string;
  readonly VITE_MODULE_PLANNING_URL?: string;
  readonly VITE_MODULE_ECO_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
