import { useCallback, useEffect, useRef, useState } from 'react';

// Read side of the async store for views: runs the fetcher, tracks the
// loading/error pair, and hands back reload() for after a write. `deps`
// name the inputs the fetcher closes over, exactly like an effect's.
export function useStoreQuery(fetcher, deps) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.resolve()
      .then(() => fetcherRef.current())
      .then((result) => {
        if (!active) return;
        setData(result);
        setError('');
      })
      .catch((err) => {
        if (active) setError(err.message || 'Could not load this view.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // The fetcher rides in a ref; its real inputs are the caller's deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  return { data, loading, error, reload };
}
