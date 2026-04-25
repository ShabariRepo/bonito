'use client';

import { useEffect } from 'react';
import { installGlobalHandlers } from '@/lib/helios';

/**
 * Installs Helios global error handlers (window.onerror, unhandledrejection).
 * Mount once in the root layout.
 */
export function HeliosInit() {
  useEffect(() => {
    installGlobalHandlers();
  }, []);

  return null;
}
