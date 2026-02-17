"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SettingsPanel } from "./SettingsPanel";
import { ChatPanel } from "./ChatPanel";
import { DEFAULT_MODEL_ID } from "@/lib/openrouter-models";
import { Settings, MessageSquare } from "lucide-react";

export function LlmPage() {
  const [savedModel, setSavedModel] = useState(DEFAULT_MODEL_ID);
  const [activeTab, setActiveTab] = useState("settings");

  function handleModelSaved(model: string) {
    setSavedModel(model);
    setActiveTab("chat");
  }

  return (
    <div className="container mx-auto max-w-4xl py-8 px-4 h-[calc(100vh-2rem)] flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">AI Assistant</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Powered by OpenRouter — chat with any LLM model for investment insights
        </p>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex-1 flex flex-col min-h-0"
      >
        <TabsList className="w-fit">
          <TabsTrigger value="settings" className="gap-1.5">
            <Settings className="size-3.5" />
            Settings
          </TabsTrigger>
          <TabsTrigger value="chat" className="gap-1.5">
            <MessageSquare className="size-3.5" />
            Chat
          </TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="mt-4">
          <SettingsPanel onModelSaved={handleModelSaved} />
        </TabsContent>

        <TabsContent value="chat" className="flex-1 min-h-0 mt-4">
          <ChatPanel savedModel={savedModel} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
