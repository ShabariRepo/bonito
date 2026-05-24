const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
};

module.exports = withSentryConfig(nextConfig, {
  org: "bonito-ai",
  project: "bonito-frontend",
  silent: true,
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
  sourcemaps: {
    disable: true,
  },
});
