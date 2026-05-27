export function GitHubProfileSelector({ profiles, onSelect }) {
  if (!profiles || profiles.length === 0) return null;

  return (
    <div className="w-full md:max-w-chat bg-brand-userBubble rounded-chat px-4 py-3 mx-4 md:mx-12 mb-2">
      <p className="text-brand-body text-msg font-medium mb-3">
        Multiple GitHub profiles found. Which profile belongs to this candidate?
      </p>

      {profiles.map((url) => (
        <button
          key={url}
          onClick={() => onSelect(url)}
          className="block w-full text-left px-3 py-2 mb-2 min-h-[44px] rounded-input border border-gray-200 text-ui text-brand-secondary hover:bg-brand-inputBg hover:border-brand-dark transition-colors truncate overflow-hidden"
        >
          {url}
        </button>
      ))}
    </div>
  );
}