import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { Providers } from "@/components/layout/providers";
import ErrorBoundary from "@/components/ErrorBoundary";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "Bonito — Enterprise AI Control Plane",
    template: "%s | Bonito — Enterprise AI Control Plane",
  },
  description:
    "Unified multi-cloud AI management platform. Connect OpenAI, Anthropic, AWS Bedrock, and Google Vertex from one control plane. Route intelligently, control costs, ship faster.",
  metadataBase: new URL("https://getbonito.com"),
  icons: {
    icon: [
      { url: "/favicon.png", type: "image/png", sizes: "32x32" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
    ],
    apple: [
      { url: "/icon-512.png", sizes: "512x512" },
    ],
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://getbonito.com",
    siteName: "Bonito",
    title: "Bonito — Enterprise AI Control Plane",
    description:
      "Unified multi-cloud AI management platform. Connect, route, monitor, and optimize your entire AI infrastructure from one dashboard.",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "Bonito — Enterprise AI Control Plane" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Bonito — Enterprise AI Control Plane",
    description:
      "Unified multi-cloud AI management platform. Connect, route, monitor, and optimize your entire AI infrastructure.",
    images: ["/og-image.png"],
  },
  robots: { index: true, follow: true },
  alternates: { canonical: "https://getbonito.com" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "Bonito",
              applicationCategory: "BusinessApplication",
              operatingSystem: "Web",
              url: "https://getbonito.com",
              description:
                "Enterprise AI control plane — unified governance, routing, and cost management across AWS, Azure, and GCP. With Bonobot governed AI agents.",
              offers: {
                "@type": "AggregateOffer",
                lowPrice: "0",
                highPrice: "5000",
                priceCurrency: "USD",
                offerCount: "4",
              },
              creator: {
                "@type": "Organization",
                name: "Bonito",
                url: "https://getbonito.com",
                founder: {
                  "@type": "Person",
                  name: "Shabari",
                  jobTitle: "Founder & CEO",
                },
              },
            }),
          }}
        />
        <Script
          id="microsoft-clarity"
          strategy="afterInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);})(window, document, "clarity", "script", "vewxqe9ey4");`,
          }}
        />
      </head>
      <body className={inter.className}>
        <Providers>
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
