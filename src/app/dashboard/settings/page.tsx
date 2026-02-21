import { SettingsPanel } from "@/components/llm/SettingsPanel";
import { RiskSettingsEditor } from "@/components/dashboard/RiskSettingsEditor";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Configure OpenRouter API key and risk rules.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SettingsPanel />
        <RiskSettingsEditor />
      </div>
    </div>
  );
}
