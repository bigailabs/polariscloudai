"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";
import { api } from "./api";

/**
 * Hook that returns API methods pre-loaded with the current Clerk JWT.
 */
export function useApi() {
  const { getToken } = useAuth();

  const get = useCallback(
    async <T = unknown>(path: string): Promise<T> => {
      const token = await getToken();
      return api.get<T>(path, token);
    },
    [getToken]
  );

  const post = useCallback(
    async <T = unknown>(path: string, body?: unknown): Promise<T> => {
      const token = await getToken();
      return api.post<T>(path, body, token);
    },
    [getToken]
  );

  const put = useCallback(
    async <T = unknown>(path: string, body?: unknown): Promise<T> => {
      const token = await getToken();
      return api.put<T>(path, body, token);
    },
    [getToken]
  );

  const del = useCallback(
    async <T = unknown>(path: string): Promise<T> => {
      const token = await getToken();
      return api.delete<T>(path, token);
    },
    [getToken]
  );

  return { get, post, put, del, getToken };
}
