export interface OpenRouterModel {
  id: string;
  name: string;
  description: string;
}

export const OPENROUTER_MODELS: OpenRouterModel[] = [
  {
    id: "openai/gpt-4o-mini",
    name: "GPT-4o Mini",
    description: "Fast, affordable OpenAI model — great for most tasks",
  },
  {
    id: "openai/gpt-4o",
    name: "GPT-4o",
    description: "OpenAI flagship — strongest reasoning and analysis",
  },
  {
    id: "anthropic/claude-3.5-haiku",
    name: "Claude 3.5 Haiku",
    description: "Fast Anthropic model with 200K context window",
  },
  {
    id: "anthropic/claude-sonnet-4-5",
    name: "Claude Sonnet 4.5",
    description: "Balanced Anthropic model — strong reasoning and speed",
  },
  {
    id: "google/gemini-2.0-flash-001",
    name: "Gemini 2.0 Flash",
    description: "Fast Google model with 1M token context",
  },
  {
    id: "google/gemini-flash-1.5",
    name: "Gemini 1.5 Flash",
    description: "Long-context Google model — great for large documents",
  },
  {
    id: "meta-llama/llama-3.3-70b-instruct",
    name: "Llama 3.3 70B",
    description: "Open-source Meta model — strong general reasoning",
  },
  {
    id: "deepseek/deepseek-r1",
    name: "DeepSeek R1",
    description: "Strong reasoning model, often free tier available",
  },
  {
    id: "mistralai/mistral-small-3.1-24b-instruct",
    name: "Mistral Small 3.1",
    description: "Efficient European model — good for structured tasks",
  },
  {
    id: "qwen/qwq-32b",
    name: "QwQ 32B",
    description: "Strong reasoning model with free tier",
  },
];

export const DEFAULT_MODEL_ID = "openai/gpt-4o-mini";

export function isValidModelId(id: string): boolean {
  return OPENROUTER_MODELS.some((m) => m.id === id);
}
