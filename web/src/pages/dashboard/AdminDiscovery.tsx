import { AppShell } from "@/components/layout/AppShell";
import { PatternDiscoveryMonitor } from "@/components/admin/PatternDiscoveryMonitor";

export default function AdminDiscovery() {
  return (
    <AppShell
      title="Pattern Discovery Monitor"
      subtitle="Trigger and monitor pattern discovery cycles"
    >
      <PatternDiscoveryMonitor />
    </AppShell>
  );
}