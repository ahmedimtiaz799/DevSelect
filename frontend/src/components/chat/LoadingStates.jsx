import { Check, Circle, LoaderCircle } from 'lucide-react';

const STEPS = [
  'Analyzing CV',
  'Checking Github Repository',
  'Generating Recommendation',
];

const STATUS_TO_STEP = {
  'Checking Github Repository...': 1,
  'Generating Recommendation...': 2,
};

export function LoadingStates({ isLoading, statuses = [] }) {
  if (!isLoading) return null;

  const activeStep = statuses.reduce(
    (highest, status) => Math.max(highest, STATUS_TO_STEP[status] ?? 0),
    0
  );

  return (
    <div className="w-full max-w-ai-msg py-1" aria-live="polite">
      {STEPS.map((step, index) => (
        <div
          key={step}
          className="flex min-h-8 items-center gap-3 text-msg"
        >
          {index < activeStep ? (
            <>
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-green-50 text-green-600">
                <Check size={15} strokeWidth={2.4} />
              </span>
              <span className="text-brand-dark">
                {step}
              </span>
            </>
          ) : index === activeStep ? (
            <>
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-dark/10 text-brand-dark">
                <LoaderCircle size={15} className="animate-spin" strokeWidth={2.4} />
              </span>
              <span className="font-medium text-brand-dark">
                {step}
              </span>
            </>
          ) : (
            <>
              <span className="flex h-6 w-6 shrink-0 items-center justify-center text-brand-muted/40">
                <Circle size={13} strokeWidth={2.2} />
              </span>
              <span className="text-brand-muted/50">
                {step}
              </span>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
