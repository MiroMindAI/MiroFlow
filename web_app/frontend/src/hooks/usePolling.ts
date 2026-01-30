import { useState, useEffect, useCallback, useRef } from 'react';

interface UsePollingOptions<T> {
  fetcher: () => Promise<T>;
  interval?: number;
  enabled?: boolean;
  shouldStop?: (data: T) => boolean;
  onUpdate?: (data: T) => void;
}

export function usePolling<T>({
  fetcher,
  interval = 2000,
  enabled = true,
  shouldStop,
  onUpdate,
}: UsePollingOptions<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timeoutRef = useRef<number | null>(null);
  const mountedRef = useRef(true);

  const poll = useCallback(async () => {
    if (!mountedRef.current || !enabled) return;

    try {
      const result = await fetcher();
      if (!mountedRef.current) return;

      setData(result);
      setError(null);
      onUpdate?.(result);

      if (shouldStop?.(result)) {
        setIsPolling(false);
        return;
      }

      timeoutRef.current = window.setTimeout(poll, interval);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err as Error);
      timeoutRef.current = window.setTimeout(poll, interval);
    }
  }, [fetcher, interval, enabled, shouldStop, onUpdate]);

  useEffect(() => {
    mountedRef.current = true;

    if (enabled) {
      setIsPolling(true);
      poll();
    }

    return () => {
      mountedRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [enabled, poll]);

  const stopPolling = useCallback(() => {
    setIsPolling(false);
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  }, []);

  return { data, error, isPolling, stopPolling };
}
