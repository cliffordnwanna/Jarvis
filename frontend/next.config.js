/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Fixes symlink issues on Windows dev machines
  webpack: (config) => {
    config.resolve.symlinks = false
    return config
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ]
  },
}

module.exports = nextConfig
