import { AppShell } from "@/components/layout/AppShell";
import { FeatureIntegrationManager } from "@/components/admin/FeatureIntegrationManager";

export default function AdminFeatures() {
  return (
    <AppShell
      title="Feature Integration Manager"
      subtitle="Manage vocabulary-to-feature integration and mapping"
    >
      <FeatureIntegrationManager />
    </AppShell>
  );
}