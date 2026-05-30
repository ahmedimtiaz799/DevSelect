import ReactMarkdown from 'react-markdown';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';

const markdownComponents = {
  h2: ({ children }) => (
    <h2 className="text-brand-dark font-bold text-lg mb-2 mt-4">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-brand-dark font-semibold text-base mb-1 mt-3">{children}</h3>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-inside text-brand-body text-msg mb-2">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-inside text-brand-body text-msg mb-2">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="mb-1">{children}</li>
  ),
  p: ({ children }) => (
    <p className="text-brand-body text-msg mb-2 whitespace-pre-line">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="text-brand-dark font-semibold">{children}</strong>
  ),
  hr: () => null,
};

export function AIMessage({ message }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (message.role === 'status') {
    return (
      <div className="w-full py-1">
        <p className="text-brand-muted text-msg italic">{message.content}</p>
      </div>
    );
  }

  return (
    <div className="group relative w-full">
      <div className="prose-none">
        <ReactMarkdown components={markdownComponents}>
          {message.content}
        </ReactMarkdown>
      </div>

      {message.content && (
        <button
          onClick={handleCopy}
          className="opacity-0 group-hover:opacity-100 transition-opacity mt-1 flex items-center gap-1 text-brand-iconGray hover:text-brand-dark"
        >
          {copied ? (
            <Check size={14} className="text-green-500" />
          ) : (
            <Copy size={14} />
          )}
          <span className="text-xs">{copied ? 'Copied' : 'Copy'}</span>
        </button>
      )}
    </div>
  );
}
