import { useCallback, useEffect, useState } from "react";

import { apiGetUsageToday, ApiError } from "../lib/api";
import type { UsageTodayResponse } from "../types/api";

type UseUsageResult = {
  usage: UsageTodayResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

export function useUsage(token: string | null): UseUsageResult {
  const [usage, setUsage] = useState<UsageTodayResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!token) {
      setUsage(null);
      setError("Missing auth token");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await apiGetUsageToday(token);
      setUsage(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`${err.status}: ${err.message}`);
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { usage, loading, error, refresh };
}
