import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  env: {
    REASONING_ENGINE_ID: process.env.REASONING_ENGINE_ID,
    SERVICE_ACCOUNT_EMAIL: process.env.SERVICE_ACCOUNT_EMAIL,
  },
};

export default nextConfig;
