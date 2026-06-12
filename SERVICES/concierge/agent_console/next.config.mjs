const basePath = "/concierge/agents";

/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath,
  reactStrictMode: true,
  experimental: { typedRoutes: true },
  async rewrites() {
    return [
      { source: "/api/concierge/tenant/:path*",     destination: `${process.env.NEXT_PUBLIC_TENANT_API_URL    || "http://localhost:8820"}/:path*` },
      { source: "/api/concierge/handoff/:path*",    destination: `${process.env.NEXT_PUBLIC_HANDOFF_URL       || "http://localhost:8821"}/:path*` },
      { source: "/api/concierge/skills/:path*",     destination: `${process.env.NEXT_PUBLIC_SKILLS_URL        || "http://localhost:8825"}/:path*` },
    ];
  },
};
export default nextConfig;
