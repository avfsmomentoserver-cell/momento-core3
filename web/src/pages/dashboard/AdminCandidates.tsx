import { AppShell } from "@/components/layout/AppShell";
import { VocabularyCandidates } from "@/components/admin/VocabularyCandidates";

export default function AdminCandidates() {
  return (
    <AppShell
      title="Vocabulary Candidates"
      subtitle="Evaluate and manage vocabulary candidates for formalization"
    >
      <VocabularyCandidates />
    </AppShell>
  );
}