import ReactMarkdown from 'react-markdown';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';
import {
  FOLLOW_UP_ANSWER_MESSAGE_TYPE,
  isEvaluationReportMessage,
} from '../../lib/messagePersistence';

const reportMarkdownComponents = {
  h2: ({ children }) => (
    <h2 className="text-brand-dark font-bold text-lg mb-2 mt-4 break-words [overflow-wrap:anywhere]">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-brand-dark font-semibold text-base mb-1 mt-3 break-words [overflow-wrap:anywhere]">{children}</h3>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-inside text-brand-body text-msg mb-2 break-words [overflow-wrap:anywhere]">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-inside text-brand-body text-msg mb-2 break-words [overflow-wrap:anywhere]">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="mb-1 break-words [overflow-wrap:anywhere]">{children}</li>
  ),
  p: ({ children }) => (
    <p className="text-brand-body text-msg mb-2 whitespace-pre-line break-words [overflow-wrap:anywhere]">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="text-brand-dark font-semibold">{children}</strong>
  ),
  hr: () => null,
};

const followUpMarkdownComponents = {
  h2: ({ children }) => (
    <h2 className="text-brand-dark font-semibold text-base mb-2 mt-3 break-words [overflow-wrap:anywhere]">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-brand-dark/90 font-medium text-sm mb-1 mt-2 break-words [overflow-wrap:anywhere]">{children}</h3>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-inside text-brand-body text-msg mb-2 break-words [overflow-wrap:anywhere]">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-inside text-brand-body text-msg mb-2 break-words [overflow-wrap:anywhere]">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="mb-1 break-words [overflow-wrap:anywhere]">{children}</li>
  ),
  p: ({ children }) => (
    <p className="text-brand-body text-msg mb-2 whitespace-pre-line break-words [overflow-wrap:anywhere]">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="text-brand-dark font-medium">{children}</strong>
  ),
  a: ({ children, href }) => (
    <a href={href} className="text-brand-dark underline underline-offset-2">{children}</a>
  ),
  hr: () => null,
};

function getAssistantMessageRenderMode(message) {
  if (message.role === 'status') return 'status';
  if (message.role === 'system') return 'stopped';

  const messageType = message.message_type || message.kind || '';
  if (messageType === FOLLOW_UP_ANSWER_MESSAGE_TYPE) return 'follow_up';
  if (isEvaluationReportMessage(message)) return 'report';

  return 'simple';
}

export function AIMessage({ message }) {
  const [copied, setCopied] = useState(false);
  const renderMode = getAssistantMessageRenderMode(message);

  function handleCopy() {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (renderMode === 'status') {
    return (
      <div className="w-full py-1">
        <p className="text-brand-muted text-msg italic">{message.content}</p>
      </div>
    );
  }

  if (renderMode === 'stopped') {
    return (
      <div className="w-full min-w-0 py-1">
        <p className="text-sm text-gray-500 break-words [overflow-wrap:anywhere]">{message.content}</p>
      </div>
    );
  }

  return (
    <div className="group relative w-full min-w-0 max-w-full">
      <div className="prose-none min-w-0 max-w-full break-words [overflow-wrap:anywhere]">
        {renderMode === 'report' && (
          <ReactMarkdown components={reportMarkdownComponents}>
            {message.content}
          </ReactMarkdown>
        )}

        {renderMode === 'follow_up' && (
          <ReactMarkdown components={followUpMarkdownComponents}>
            {message.content}
          </ReactMarkdown>
        )}

        {renderMode === 'simple' && (
          <p className="text-brand-body text-msg whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
            {message.content}
          </p>
        )}
      </div>

      {message.content && (
        <button
          onClick={handleCopy}
          className="opacity-0 group-hover:opacity-100 transition-opacity mt-1 flex items-center gap-1 text-brand-iconGray hover:text-brand-dark"
        >
          {copied ? (
            <Check size={14} className="text-gray-500" />
          ) : (
            <Copy size={14} />
          )}
          <span className="text-xs">{copied ? 'Copied' : 'Copy'}</span>
        </button>
      )}
    </div>
  );
}
