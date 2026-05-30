import React from 'react';

export default function ChatBubble({ message, isStreaming }) {
  const isUser = message.role === 'user';
  const isToolCall = message.role === 'tool_call';

  if (isToolCall) {
    return (
      <div className="chat-message" style={{ alignSelf: 'center', opacity: 0.7 }}>
        <div className="chat-bubble" style={{
          background: 'var(--bg-tertiary)',
          fontSize: 12,
          padding: '6px 14px',
          borderRadius: 'var(--radius)',
        }}>
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`chat-message ${isUser ? 'user' : 'assistant'}`}>
      <div className={`chat-avatar ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? '👤' : '◆'}
      </div>
      <div className="chat-bubble">
        {message.content}
        {isStreaming && <span className="cursor-blink" style={{ animation: 'blink 1s step-end infinite' }}>▌</span>}
      </div>
    </div>
  );
}
