import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // O pnpm-lock vive em web/; evita o Turbopack inferir a raiz a partir de lockfiles em pastas acima.
  turbopack: { root: process.cwd() },
};

export default config;
