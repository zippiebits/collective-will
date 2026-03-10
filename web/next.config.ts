import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin();

const cspDirectives = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  "connect-src 'self'",
  "frame-src 'none'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "upgrade-insecure-requests",
].join("; ");

export default withNextIntl({
  reactStrictMode: true,
  output: "standalone",
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {key: "Content-Security-Policy", value: cspDirectives},
        ],
      },
    ];
  },
});
