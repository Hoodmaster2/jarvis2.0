import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import ChatBubble from '../components/ChatBubble';
import VoiceButton from '../components/VoiceButton';

export default function Chat() {
  const { messages, isLoading, streamingText, sendMessage, clearChat } = useChat();
  const [input, setInput] = useState('');
  const [voiceActive, setVoiceActive] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'F4') {
        e.preventDefault();
        setVoiceActive(v => !v);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h1>Chat</h1>
          <p>Talk to JARVIS</p>
        </div>
        <button className="btn btn-sm" onClick={clearChat}>Clear</button>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', flex: 1, gap: 16, opacity: 0.5,
          }}>
            <div className="glowing-sphere" />
            <p style={{ fontSize: 18, color: 'var(--text-secondary)' }}>How can I help you?</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', maxWidth: 400 }}>
              I can manage files, browse the web, run commands, write code, and more.
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatBubble key={i} message={msg} isStreaming={false} />
        ))}
        {isLoading && streamingText && (
          <ChatBubble
            message={{ role: 'assistant', content: streamingText }}
            isStreaming={true}
          />
        )}
        {isLoading && !streamingText && (
          <div className="chat-message assistant">
            <div className="chat-avatar assistant">◆</div>
            <div className="chat-bubble" style={{ display: 'flex', gap: 4 }}>
              <span style={{ animation: 'blink 1s step-end infinite' }}>●</span>
              <span style={{ animation: 'blink 1s step-end infinite', animationDelay: '0.3s' }}>●</span>
              <span style={{ animation: 'blink 1s step-end infinite', animationDelay: '0.6s' }}>●</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-area" onSubmit={handleSubmit}>
        <div className="chat-input-wrapper">
          <VoiceButton active={voiceActive} onClick={() => setVoiceActive(v => !v)} />
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="Ask JARVIS anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <button type="submit" className="chat-send-btn" disabled={isLoading || !input.trim()}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
