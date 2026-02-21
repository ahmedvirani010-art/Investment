import { SetupSectors } from "@/components/dashboard/SetupSectors";
import { SetupScripts } from "@/components/dashboard/SetupScripts";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function SetupPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Setup</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Manage sectors and scripts (stocks) from PSX. Load reference data or add manually.
        </p>
      </div>
      <Tabs defaultValue="sectors" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="sectors">Sectors</TabsTrigger>
          <TabsTrigger value="scripts">Scripts</TabsTrigger>
        </TabsList>
        <TabsContent value="sectors" className="mt-6">
          <SetupSectors />
        </TabsContent>
        <TabsContent value="scripts" className="mt-6">
          <SetupScripts />
        </TabsContent>
      </Tabs>
    </div>
  );
}
