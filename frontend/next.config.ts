import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // -------------- temp --------------
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'www.telegraph.co.uk',
      },
      {
        protocol: 'https',
        hostname: 'photo.coolenjoy.co.kr',
      },
      {
        protocol: 'https',
        hostname: 'afremov.com',
      },
      {
        protocol: 'https',
        hostname: 'cdn.mos.cms.futurecdn.net',
      },
      {
        protocol: 'https',
        hostname: 'images.squarespace-cdn.com',
      },
      // -------------- temp --------------
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
      },
    ],
  },
};

export default nextConfig;
