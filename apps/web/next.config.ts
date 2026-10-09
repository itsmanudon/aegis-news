import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  output: "standalone",
  // Keep the isolated real-backend build separate from the mock regression build.
  distDir:
    process.env.AEGIS_COMPLETION_BUILD === "1" ? ".next-completion" : ".next",
  poweredByHeader: false,
};
export default nextConfig;
