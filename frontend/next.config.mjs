/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      {
        source: '/scenarios',
        destination: '/practice',
        permanent: true,
      },
      {
        source: '/history',
        destination: '/practice',
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
