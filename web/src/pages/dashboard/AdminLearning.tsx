import { AppShell } from "@/components/layout/AppShell";
import { LearningProgressTracker } from "@/components/admin/LearningProgressTracker";

export default function AdminLearning() {
  return (
    <AppShell
      title="Learning Progress Tracker"
      subtitle="Monitor and optimize vocabulary learning progress"
    >
      <LearningProgressTracker />
    </AppShell>
  );
}