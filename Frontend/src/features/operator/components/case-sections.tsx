import type { CaseFile } from "../types/operator.types";
import { NoticePreviewCard } from "./notice-preview-card";
import { RecipientDecisionCard } from "./recipient-decision-card";
import { SourceEvidenceCard } from "./source-evidence-card";
import { TraceMatchesCard } from "./trace-matches-card";

export function CaseSections({ caseFile }: { caseFile: CaseFile }) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="space-y-6">
        <SourceEvidenceCard evidence={caseFile.evidence} />
        <TraceMatchesCard matches={caseFile.traceMatches} />
      </div>
      <div className="space-y-6">
        <RecipientDecisionCard
          recipient={caseFile.recipient}
          initialRestriction={caseFile.restriction}
        />
        <NoticePreviewCard audience={caseFile.audience} />
      </div>
    </div>
  );
}
