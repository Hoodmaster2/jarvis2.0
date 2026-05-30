import React, { useState, useEffect } from 'react';

export default function Voice() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');

  const toggleListening = () => {
    if (!isListening) {
      setIsListening(true);
      setTranscript('Listening...');
      // In production, this would call the backend STT endpoint
      setTimeout(() => {
        setTranscript('Speech recognition ready. Press F4 or click to speak.');
        setIsListening(false);
      }, 2000);
    } else {
      setIsListening(false);
      setTranscript('');
    }
  };

  // Wake word listener would be implemented here in production
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'F4') {
        e.preventDefault();
        toggleListening();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isListening]);

  return (
    <div className="voice-container">
      <div className="glowing-sphere" style={{
        width: 120, height: 120,
        animation: isListening ? 'pulse 0.5s ease-in-out infinite' : 'pulse 2s ease-in-out infinite',
      }} />

      <div className="voice-status">
        {isListening ? 'Listening...' : 'Press F4 or click to speak'}
      </div>

      {transcript && (
        <div className="card" style={{ maxWidth: 500, width: '100%', textAlign: 'center' }}>
          <p style={{ fontSize: 16, marginBottom: 8 }}>{transcript}</p>
        </div>
      )}

      {response && (
        <div className="card" style={{ maxWidth: 500, width: '100%' }}>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>Response:</p>
          <p style={{ fontSize: 16 }}>{response}</p>
        </div>
      )}

      <button
        className={`btn ${isListening ? 'btn-danger' : 'btn-primary'}`}
        onClick={toggleListening}
        style={{ padding: '12px 32px', fontSize: 16 }}
      >
        {isListening ? 'Stop Listening' : 'Start Listening'}
      </button>

      <div className="card" style={{ maxWidth: 500, width: '100%' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Voice Settings</h3>
        <div className="setting-row">
          <span className="label">Push-to-talk key</span>
          <code style={{ color: 'var(--accent-primary)' }}>F4</code>
        </div>
        <div className="setting-row">
          <span className="label">Wake word</span>
          <span>"Jarvis" (disabled)</span>
        </div>
        <div className="setting-row">
          <span className="label">Speech-to-text</span>
          <span>Whisper (local)</span>
        </div>
        <div className="setting-row">
          <span className="label">Text-to-speech</span>
          <span>Windows SAPI</span>
        </div>
      </div>
    </div>
  );
}
