import type { Metadata } from "next";
import { LlmPage } from "@/components/llm/LlmPage";

export const metadata: Metadata = {
  title: "AI Assistant — PSX Investment",
  description: "Chat with LLMs via OpenRouter for investment insights",
};

export default function LlmRoute() {
  return <LlmPage />;
}
