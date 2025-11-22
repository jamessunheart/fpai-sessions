/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  experimental: {
    appDir: false, // 👈 disable app directory feature
  },
}

module.exports = nextConfig;
