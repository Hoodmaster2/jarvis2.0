import { useState, useCallback, useRef } from 'react';
import { api } from '../utils/api';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const abortRef = useRef(null);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isLoading) return;

    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setStreamingText('');

    try {
      const history = messages.slice(-20).map(m => ({ role: m.role, content: m.content }));
      const response = await api.sendMessage(text, history);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(Boolean);

        for (const line of lines) {
          try {
            const data = JSON.parse(line);

            if (data.message?.content) {
              fullContent += data.message.content;
              setStreamingText(fullContent);
            }

            if (data.type === 'tool_calls' && data.tool_calls) {
              const toolMsg = {
                role: 'tool_call',
                content: `🔧 Using tool: ${data.tool_calls.map(tc =>
                  tc.function?.name || 'unknown'
                ).join(', ')}`
              };
              setMessages(prev => [...prev, toolMsg]);
            }

            if (data.error) {
              console.error('Chat error:', data.error);
            }
          } catch {
            // partial line, skip
          }
        }
      }

      if (fullContent) {
        setMessages(prev => [...prev, { role: 'assistant', content: fullContent }]);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message || 'Failed to connect to backend'}`
      }]);
    } finally {
      setIsLoading(false);
      setStreamingText('');
    }
  }, [messages, isLoading]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setStreamingText('');
  }, []);

  return { messages, isLoading, streamingText, sendMessage, clearChat };
}
