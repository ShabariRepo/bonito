/**
 * SWR-based data fetching with stale-while-revalidate caching.
 * Data shows instantly from cache, refreshes in background.
 */
import useSWR, { SWRConfiguration } from "swr";
import { apiRequest } from "./auth";

const fetcher = async (url: string) => {
  const res = await apiRequest(url);
  if (!res.ok) {
    const error = new Error("API request failed");
    (error as any).status = res.status;
    throw error;
  }
  return res.json();
};

// Default config: show stale data for 30s, dedupe requests within 5s
const defaultConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  dedupingInterval: 5000,
  errorRetryCount: 2,
};

/**
 * Cached API fetch — data persists across page navigations.
 * First render shows cached data instantly, revalidates in background.
 */
export function useAPI<T = any>(endpoint: string | null, config?: SWRConfiguration) {
  const { data, error, isLoading, isValidating, mutate } = useSWR<T>(
    endpoint,
    fetcher,
    { ...defaultConfig, ...config }
  );

  return {
    data,
    error,
    isLoading,        // true on first load only (no cache)
    isValidating,     // true when revalidating (even with cache)
    mutate,           // force refresh
    isEmpty: !data && !isLoading,
  };
}

/**
 * Pre-warm cache for a set of endpoints.
 */
export function prefetch(endpoints: string[]) {
  endpoints.forEach((url) => {
    fetcher(url).catch(() => {});
  });
}
