"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { OPENROUTER_MODELS, isValidModelId } from "@/lib/openrouter-models";
import { Loader2, KeyRound, Bot } from "lucide-react";

const SettingsSchema = z.object({
  apiKey: z.string().min(1, "API key is required"),
  model: z.string().refine(isValidModelId, "Please select a valid model"),
});

type SettingsValues = z.infer<typeof SettingsSchema>;

interface SettingsPanelProps {
  onModelSaved: (model: string) => void;
}

export function SettingsPanel({ onModelSaved }: SettingsPanelProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);

  const form = useForm<SettingsValues>({
    resolver: zodResolver(SettingsSchema),
    defaultValues: {
      apiKey: "",
      model: "openai/gpt-4o-mini",
    },
  });

  // Load current settings on mount
  useEffect(() => {
    async function loadSettings() {
      try {
        const res = await fetch("/api/llm/settings");
        if (res.ok) {
          const data = await res.json();
          form.setValue("model", data.model);
          setHasApiKey(data.hasApiKey);
        }
      } catch {
        // silently ignore on initial load
      }
    }
    loadSettings();
  }, [form]);

  async function onSubmit(values: SettingsValues) {
    setIsSaving(true);
    try {
      const res = await fetch("/api/llm/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });

      if (!res.ok) {
        const error = await res.json();
        toast.error(error.error ?? "Failed to save settings");
        return;
      }

      const data = await res.json();
      setHasApiKey(true);
      form.setValue("apiKey", ""); // clear field after save
      toast.success("Settings saved successfully");
      onModelSaved(data.model);
    } catch {
      toast.error("Failed to save settings. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card className="max-w-xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="size-5" />
          OpenRouter Configuration
        </CardTitle>
        <CardDescription>
          Enter your{" "}
          <a
            href="https://openrouter.ai/keys"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-foreground"
          >
            OpenRouter API key
          </a>{" "}
          and select which LLM model to use for chat and analysis.
        </CardDescription>
      </CardHeader>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <CardContent className="flex flex-col gap-5">
            {/* API Key */}
            <FormField
              control={form.control}
              name="apiKey"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-1.5">
                    <KeyRound className="size-3.5" />
                    API Key
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="password"
                      placeholder={
                        hasApiKey
                          ? "Key saved — enter a new key to replace it"
                          : "sk-or-v1-..."
                      }
                      autoComplete="off"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Model Selector */}
            <FormField
              control={form.control}
              name="model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select a model" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {OPENROUTER_MODELS.map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          <span className="font-medium">{model.name}</span>
                          <span className="ml-2 text-muted-foreground text-xs">
                            {model.description}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>

          <CardFooter>
            <Button type="submit" disabled={isSaving} className="w-full">
              {isSaving ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Saving…
                </>
              ) : (
                "Save Settings"
              )}
            </Button>
          </CardFooter>
        </form>
      </Form>
    </Card>
  );
}
