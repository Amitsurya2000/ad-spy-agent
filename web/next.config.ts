import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Lean, self-contained build for the Docker image (see web/Dockerfile).
  output: "standalone",
};

export default nextConfig;
