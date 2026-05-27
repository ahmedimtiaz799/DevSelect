import { useRef, useState, useEffect } from 'react';
import { Plus, ArrowUp, Square, FileText, X } from 'lucide-react';

export function InputBar({ onSend, onStop, onFileSelect, onFileClear, isLoading, isStreaming, file }) {
  const [text, setText] = useState('');
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  const hasContent = text.trim().length > 0 || !!file;
  const canSend = hasContent && !isLoading && !isStreaming;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${textarea.scrollHeight}px`;
  }, [text]);

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canSend) handleSend();
    }
  }

  function handleSend() {
    if (!canSend) return;
    onSend(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }

  function handleFileChange(e) {
    const selected = e.target.files?.[0];
    if (selected) {
      onFileSelect(selected);
      e.target.value = '';
    }
  }

  return (
    <div className="mx-4 md:mx-12 mt-2">
      <div className="flex flex-col bg-white ring-1 ring-gray-300 shadow-lg rounded-input px-3 pt-2 pb-2">

        {file && (
          <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-lg px-2 py-1.5 mb-2 self-start max-w-[220px]">
            <FileText size={13} className="text-brand-iconGray shrink-0" />
            <span className="truncate text-xs text-brand-body max-w-[130px]">
              {file.name}
            </span>
            <button
              onClick={onFileClear}
              className="flex items-center justify-center min-w-[20px] min-h-[20px] ml-0.5 text-brand-iconGray hover:text-red-500 transition-colors shrink-0"
            >
              <X size={12} />
            </button>
          </div>
        )}

        <div className="flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={handleFileChange}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center min-w-[44px] min-h-[44px] text-brand-iconGray hover:text-brand-dark transition-colors cursor-pointer shrink-0"
          >
            <Plus size={20} />
          </button>

          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Upload a CV to evaluate a candidate"
            rows={1}
            className="flex-1 bg-transparent outline-none text-base text-brand-body placeholder:text-brand-muted resize-none overflow-hidden leading-6 py-[9px]"
          />

          {isStreaming ? (
            <button
              onClick={onStop}
              className="flex items-center justify-center min-w-[44px] min-h-[44px] bg-brand-dark text-white rounded-full transition-colors shrink-0"
            >
              <Square size={14} fill="white" />
            </button>
          ) : canSend ? (
            <button
              onClick={handleSend}
              className="flex items-center justify-center min-w-[44px] min-h-[44px] bg-brand-dark text-white rounded-lg transition-colors shrink-0"
            >
              <ArrowUp size={16} />
            </button>
          ) : null}
        </div>

      </div>
    </div>
  );
}