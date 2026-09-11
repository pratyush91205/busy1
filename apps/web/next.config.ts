import path from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // This app is one workspace inside apps/, so pin the bundler root here.
  // Otherwise Turbopack walks up past the repository looking for a lockfile.
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
