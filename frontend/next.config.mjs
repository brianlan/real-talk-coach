import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: __dirname,
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
