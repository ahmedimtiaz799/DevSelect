import ReactMarkdown from 'react-markdown';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';
import {
  FOLLOW_UP_ANSWER_MESSAGE_TYPE,
  isEvaluationReportMessage,
  isStoppedResponseMessage,
} from '../../lib/messagePersistence';
import { markdownToPlainText } from '../../lib/markdownToPlainText';

const ALLOWED_MARKDOWN_URL_PROTOCOLS = new Set(['http:', 'https:', 'mailto:']);

function isSafeMarkdownUrl(href) {
  if (typeof href !== 'string') return false;

  const trimmedHref = href.trim();
  if (!trimmedHref) return false;

  try {
    const url = new URL(trimmedHref);
    return ALLOWED_MARKDOWN_URL_PROTOCOLS.has(url.protocol);
  } catch {
    return false;
  }
}

function MarkdownLink({ children, href }) {
  const trimmedHref = typeof href === 'string' ? href.trim() : '';

  if (!isSafeMarkdownUrl(trimmedHref)) {
    return <span className="text-brand-dark underline underline-offset-2">{children}</span>;
  }

  return (
    <a
      href={trimmedHref}
      target="_blank"
      rel="noopener noreferrer"
      className="rounded-sm text-brand-dark underline underline-offset-2 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-focusRing/70"
    >
      {children}
    </a>
  );
}

const reportMarkdownComponents = {
  h2: ({ children }) => (
    <h2 className="text-brand-dark font-bold text-lg mb-3 mt-5 break-words [overflow-wrap:anywhere]">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-brand-dark font-semibold text-base mb-2 mt-4 break-words [overflow-wrap:anywhere]">{children}</h3>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-outside pl-5 text-brand-body text-msg mb-3 space-y-2 break-words [overflow-wrap:anywhere]">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside pl-5 text-brand-body text-msg mb-3 space-y-3 break-words [overflow-wrap:anywhere]">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="pl-1 break-words [overflow-wrap:anywhere]">{children}</li>
  ),
  p: ({ children }) => (
    <p className="text-brand-body text-msg mb-3 whitespace-pre-line break-words [overflow-wrap:anywhere]">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="text-brand-dark font-semibold">{children}</strong>
  ),
  a: MarkdownLink,
  hr: () => null,
};

const followUpMarkdownComponents = {
  h2: ({ children }) => (
    <h2 className="text-brand-dark font-bold text-lg mb-3 mt-4 break-words [overflow-wrap:anywhere]">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-brand-dark/90 font-medium text-sm mb-2 mt-3 break-words [overflow-wrap:anywhere]">{children}</h3>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-outside pl-5 text-brand-body text-msg mb-3 space-y-2 break-words [overflow-wrap:anywhere]">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside pl-5 text-brand-body text-msg mb-4 space-y-4 break-words [overflow-wrap:anywhere]">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="pl-1 break-words [overflow-wrap:anywhere]">{children}</li>
  ),
  p: ({ children }) => (
    <p className="text-brand-body text-msg mb-3 whitespace-pre-line break-words [overflow-wrap:anywhere]">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="text-brand-dark font-semibold">{children}</strong>
  ),
  a: MarkdownLink,
  hr: () => null,
};

function getAssistantMessageRenderMode(message) {
  if (message.role === 'status') return 'status';
  if (message.role === 'system' || isStoppedResponseMessage(message)) return 'stopped';

  const messageType = message.message_type || message.kind || '';
  if (messageType === FOLLOW_UP_ANSWER_MESSAGE_TYPE) return 'follow_up';
  if (isEvaluationReportMessage(message)) return 'report';

  return 'simple';
}

export function AIMessage({ message }) {
  const [copied, setCopied] = useState(false);
  const renderMode = getAssistantMessageRenderMode(message);

  function handleCopy() {
    const copyText =
      renderMode === 'report' || renderMode === 'follow_up'
        ? markdownToPlainText(message.content)
        : message.content;

    navigator.clipboard.writeText(copyText);
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
        <p className="text-sm text-brand-systemText break-words [overflow-wrap:anywhere]">{message.content}</p>
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

      {message.content && !message.isStreaming && (
        <button
          onClick={handleCopy}
          aria-label="Copy message"
          className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity mt-1 flex items-center gap-1 rounded-md text-brand-iconGray hover:text-brand-dark focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-focusRing/70"
        >
          {copied ? (
            <Check size={14} className="text-brand-systemText" />
          ) : (
            <Copy size={14} />
          )}
          <span className="text-xs">{copied ? 'Copied' : 'Copy'}</span>
        </button>
      )}
    </div>
  );
}
