const STEPS = [
  'Analyzing CV...',
  'Checking Github Repository...',
  'Generating Recommendation...',
];

export function LoadingStates({ isLoading, statuses }) {
  const hasAnyActivity = isLoading || statuses.length > 0;
  if (!hasAnyActivity) return null;

  const completedStatuses = new Set(statuses);

  const analyzingDone = statuses.length > 0;
  const lines = [
    { label: 'Analyzing CV...', done: analyzingDone },
    ...STEPS.slice(1).map((step) => ({
      label: step,
      done: completedStatuses.has(step),
      visible: statuses.some((s) => s === step) || analyzingDone,
    })),
  ];

  const visibleLines = lines.filter((l, i) => i === 0 || l.visible);

  return (
    <div className="flex flex-col gap-2 px-4 md:px-12 py-2">
      {visibleLines.map((line) => (
        <div key={line.label} className="flex items-center gap-2 text-msg">
          {line.done ? (
            <>
              <span className="text-green-500">✓</span>
              <span className="text-brand-dark/40">
                {line.label.replace('...', '')}
              </span>
            </>
          ) : (
            <span className="text-brand-textLoading animate-pulse">
              {line.label}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}