import { AppShell } from "@/components/layout/AppShell";
import { V5AdminDashboard } from "@/components/admin/V5AdminDashboard";

export default function V5Admin() {
  return (
    <AppShell
      title="V5 Free-Tier Administration"
      subtitle="Admin dashboard for V5 transformation monitoring and management"
    >
      <V5AdminDashboard />
    </AppShell>
  );
}