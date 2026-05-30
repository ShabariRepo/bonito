"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              document.documentElement.style.setProperty('color-scheme', 'dark');
            `,
          }}
        />
      </head>
      <body style={{ margin: 0, padding: 0, backgroundColor: '#0a0a0a', color: '#f5f0e8', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          textAlign: 'center',
          padding: '1.5rem'
        }}>
          {/* Catastrophic fish ASCII */}
          <pre style={{
            color: '#dc2626',
            fontSize: '0.875rem',
            fontFamily: 'monospace',
            marginBottom: '2rem',
            userSelect: 'none'
          }} aria-hidden="true">
{`    X___X
   /     \\
<°)))><   |
   \\_____/`}
          </pre>

          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#f87171',
            fontSize: '0.875rem',
            fontWeight: 500,
            padding: '0.375rem 1rem',
            borderRadius: '9999px',
            marginBottom: '1.5rem'
          }}>
            ⚠️ Critical error
          </div>

          <h1 style={{
            fontSize: '3rem',
            fontWeight: 'bold',
            marginBottom: '1rem',
            letterSpacing: '-0.025em'
          }}>
            Total system failure
          </h1>

          <p style={{
            color: '#888',
            fontSize: '1.125rem',
            maxWidth: '28rem',
            marginBottom: '2.5rem',
            lineHeight: 1.5
          }}>
            Something catastrophic happened. We&apos;ve been notified. Try refreshing or come back in a few minutes.
          </p>

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
            <button
              onClick={() => reset()}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                backgroundColor: '#7c3aed',
                color: 'white',
                fontWeight: 600,
                padding: '0.75rem 1.5rem',
                borderRadius: '0.75rem',
                border: 'none',
                cursor: 'pointer',
                fontSize: '1rem'
              }}
              onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#6d28d9'}
              onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#7c3aed'}
            >
              ↻ Try again
            </button>
            <a
              href="/"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                backgroundColor: '#111',
                border: '1px solid #1a1a1a',
                color: '#ccc',
                fontWeight: 500,
                padding: '0.75rem 1.5rem',
                borderRadius: '0.75rem',
                textDecoration: 'none',
                fontSize: '1rem'
              }}
              onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#1a1a1a'}
              onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#111'}
            >
              🏠 Back to shore
            </a>
          </div>

          {error.digest && (
            <p style={{
              marginTop: '2rem',
              fontSize: '0.75rem',
              color: '#333',
              fontFamily: 'monospace'
            }}>
              Error ID: {error.digest}
            </p>
          )}
        </div>
      </body>
    </html>
  );
}
