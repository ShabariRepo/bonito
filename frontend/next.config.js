const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
};

module.exports = withSentryConfig(nextConfig, {
  org: "bonito-ai",
  project: "bonito-frontend",
  silent: !process.env.CI,
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
  authToken: process.env.SENTRY_AUTH_TOKEN,
});
