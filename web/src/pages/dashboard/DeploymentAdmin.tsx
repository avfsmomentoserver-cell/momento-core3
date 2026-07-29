import { AppShell } from "@/components/layout/AppShell";
import { DeploymentManager } from "@/components/admin/DeploymentManager";

export default function DeploymentAdmin() {
  return (
    <AppShell
      title="V5 Deployment Administration"
      subtitle="Admin dashboard for V5 free-tier deployment management"
    >
      <DeploymentManager />
    </AppShell>
  );
}