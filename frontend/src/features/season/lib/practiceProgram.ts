import type {
  PracticeProgram,
  PracticeSegment,
  PracticeSegmentStatus,
  StageSessionProgress
} from "@/entities";

export const practiceSegments: PracticeSegment[] = ["fp1", "fp2", "fp3"];

export const practiceSegmentLabels: Record<PracticeSegment, string> = {
  fp1: "П1",
  fp2: "П2",
  fp3: "П3"
};

type PracticeStep =
  | { kind: "segment"; segment: PracticeSegment; label: string }
  | { kind: "final"; label: string }
  | { kind: "completed"; label: string };

const defaultLockedProgram = (stageId: string): PracticeProgram => ({
  stageId,
  fp1Status: "locked",
  fp2Status: "locked",
  fp3Status: "locked",
  practiceCompletionStatus: "locked"
});

const defaultAvailableProgram = (stageId: string): PracticeProgram => ({
  stageId,
  fp1Status: "available",
  fp2Status: "locked",
  fp3Status: "locked",
  practiceCompletionStatus: "locked"
});

export function getPracticeProgram(
  stageId: string,
  progress: StageSessionProgress | undefined
): PracticeProgram {
  if (progress?.practiceProgram) {
    return progress.practiceProgram;
  }

  if (progress?.practiceStatus === "completed") {
    return {
      stageId,
      fp1Status: "completed",
      fp2Status: "completed",
      fp3Status: "completed",
      practiceCompletionStatus: "completed"
    };
  }

  if (!progress || progress.practiceStatus === "available") {
    return defaultAvailableProgram(stageId);
  }

  return defaultLockedProgram(stageId);
}

export function getPracticeSegmentStatus(
  program: PracticeProgram,
  segment: PracticeSegment
): PracticeSegmentStatus {
  if (segment === "fp1") return program.fp1Status;
  if (segment === "fp2") return program.fp2Status;
  return program.fp3Status;
}

export function isPracticeSegmentResolved(status: PracticeSegmentStatus) {
  return status === "completed";
}

export function hasCompletedPracticeSegment(program: PracticeProgram) {
  return practiceSegments.some(
    (segment) => getPracticeSegmentStatus(program, segment) === "completed"
  );
}

export function getNextPracticeStep(program: PracticeProgram): PracticeStep {
  if (program.practiceCompletionStatus === "completed") {
    return { kind: "completed", label: "Практика закрыта" };
  }

  const availableSegment = practiceSegments.find(
    (segment) => getPracticeSegmentStatus(program, segment) === "available"
  );

  if (availableSegment) {
    return {
      kind: "segment",
      segment: availableSegment,
      label: practiceSegmentLabels[availableSegment]
    };
  }

  if (program.practiceCompletionStatus === "available") {
    return { kind: "final", label: "Завершение практики" };
  }

  return { kind: "segment", segment: "fp1", label: practiceSegmentLabels.fp1 };
}

export function getPracticeStatusLabel(
  status: PracticeSegmentStatus | PracticeProgram["practiceCompletionStatus"]
) {
  const labels = {
    locked: "Закрыто",
    available: "Доступно",
    completed: "Готово"
  };

  return labels[status];
}

export function getPracticeStatusVariant(
  status: PracticeSegmentStatus | PracticeProgram["practiceCompletionStatus"]
) {
  if (status === "completed") return "completed" as const;
  if (status === "available") return "live" as const;
  return "neutral" as const;
}

export function getPracticeCompletionLabel(program: PracticeProgram) {
  if (program.practiceCompletionStatus === "completed") return "Практика завершена";
  if (program.practiceCompletionStatus === "available") return "Можно завершить";

  const completedCount = practiceSegments.filter(
    (segment) => getPracticeSegmentStatus(program, segment) === "completed"
  ).length;

  return completedCount ? `${completedCount}/3 П` : "П1 требуется";
}
