import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The on-screen Next.js badge is a development tool; hidden so dev screenshots match production.
  devIndicators: false,
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
