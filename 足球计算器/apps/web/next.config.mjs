/** @type {import('next').NextConfig} */
const nextConfig = {
  // Avoid dev/build clobbering each other (both write to distDir).
  // Our agent often runs `next build` while `next dev` is running, which can
  // corrupt `.next/server` and cause missing chunk errors like "./833.js".
  distDir: process.env.NEXT_DIST_DIR ?? ".next",

  experimental: {
    // Work around occasional RSC manifest / next-devtools Segment Explorer crashes:
    // "Could not find the module ... SegmentViewNode in the React Client Manifest"
    // which can cascade into "__webpack_modules__[moduleId] is not a function".
    devtoolSegmentExplorer: false,
  },

  // We often open dev from LAN IP (phone testing). Next 15 warns that in future
  // we must explicitly allow dev origins for cross-origin /_next requests.
  allowedDevOrigins: ["http://localhost:3000", "http://127.0.0.1:3000"],
};

export default nextConfig;

