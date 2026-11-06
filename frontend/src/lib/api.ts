// Central place for talking to the DataGuard backend.
// Components never call fetch() directly, so URL handling and error handling live here.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { signal, cache: "no-store" });
  } catch (error) {
    if (isAbortError(error)) throw error; // the caller cancelled the request on purpose
    throw new ApiError("Cannot reach the DataGuard API");
  }

  if (!response.ok) {
    throw new ApiError(`Request failed (HTTP ${response.status})`, response.status);
  }
  return (await response.json()) as T;
}