'use client';

import { useEffect, useState } from 'react';

interface Step {
  name: string;
  description: string;
  action: 'navigate' | 'click' | 'scroll' | 'type' | 'hover' | 'select' | 'submit';
  target?: string; // CSS selector or URL for navigation
  value?: string; // For type/select actions
  status: 'pending' | 'completed' | 'failed';
  timestamp?: number;
}

interface BrowserViewProps {
  debuggingUrl?: string;
}


export default function BrowserView({ debuggingUrl }: BrowserViewProps) {
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response = await fetch('http://localhost:8000/session/');
        const data = await response.json();
        setSessions(data.sessions);
      } catch (error) {
        console.error('Error fetching sessions:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
    // Poll for sessions every 5 seconds
    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen">
      {/* Main browser view */}
      <div className="flex-grow">
        {debuggingUrl ? (
          <iframe
            src={debuggingUrl}
            className="w-full h-full border-0"
            allow="fullscreen"
          />
        ) : (
          <div className="flex items-center justify-center h-full bg-gray-100">
            <p className="text-gray-500">No active browser session</p>
          </div>
        )}
      </div>

      {/* Sessions sidebar */}
      <div className="w-80 bg-white border-l border-gray-200 p-4 overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Active Sessions</h2>
        {loading ? (
          <p className="text-gray-500">Loading sessions...</p>
        ) : (
          <ul className="space-y-3">
            {steps.map((step) => (
              <li
                key={step.timestamp}
                className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium truncate">
                    {step.name}
                  </span>
                  <span
                    className={`px-2 py-1 text-xs rounded-full ${
                      step.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {step.status}
                  </span>
                </div>
                <p className="text-sm text-gray-500 truncate mt-1">
                  {step.description}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
} 