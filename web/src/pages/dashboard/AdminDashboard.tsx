import { AppShell } from "@/components/layout/AppShell";
import { VocabularyDashboard } from "@/components/admin/VocabularyDashboard";

export default function AdminDashboard() {
  return (
    <AppShell
      title="Vocabulary Learning System"
      subtitle="Admin dashboard for vocabulary learning management"
    >
      <VocabularyDashboard />
    </AppShell>
  );
}