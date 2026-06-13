import { Check, LoaderCircle } from 'lucide-react';

const DEFAULT_STATUS = 'Analyzing CV...';

export function LoadingStates({ isLoading, statuses = [] }) {
  if (!isLoading) return null;

  const visibleStatuses = [...new Set(
    (statuses.length > 0 ? statuses : [DEFAULT_STATUS]).filter(Boolean)
  )];

  return (
    <div className="w-full max-w-ai-msg py-1" aria-live="polite">
      {visibleStatuses.map((step, index) => (
        <div
          key={step}
          className="flex min-h-8 items-center gap-3 text-msg"
        >
          {index < visibleStatuses.length - 1 ? (
            <>
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ds-border-subtle text-ds-text-subtle">
                <Check size={15} strokeWidth={2.4} />
              </span>
              <span className="text-ds-text-strong">
                {step}
              </span>
            </>
          ) : (
            <>
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-dsAlpha-accent/10 text-ds-text-strong">
                <LoaderCircle size={15} className="animate-spin" strokeWidth={2.4} />
              </span>
              <span className="font-medium text-ds-text-strong">
                {step}
              </span>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
