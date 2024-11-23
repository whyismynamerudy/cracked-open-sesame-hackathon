'use client';

import { useState } from 'react';
import BrowserView from './components/BrowserView';

export default function Home() {
  const [debuggingUrl, setDebuggingUrl] = useState<string>();

  const handleExecute = async () => {
    try {
      const response = await fetch('http://localhost:8000/execute', {
        method: 'POST',
      });
      const data = await response.json();
      setDebuggingUrl(data.debuggingUrl);
    } catch (error) {
      console.error('Error executing browser session:', error);
    }
  };

  return (
    <main className="min-h-screen">
      <div className="p-4 border-b">
        <button
          onClick={handleExecute}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
        >
          Start Browser Session
        </button>
      </div>
      <BrowserView debuggingUrl={debuggingUrl} />
    </main>
  );
}
