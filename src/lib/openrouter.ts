export const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";

export function buildOpenRouterHeaders(apiKey: string): Record<string, string> {
  return {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:3000",
    "X-Title": "PSX Investment Assistant",
  };
}
