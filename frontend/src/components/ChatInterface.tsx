import { useEffect, useRef, useMemo } from 'react';
import { TranscriptMessage } from '../hooks/useWebRTC';

interface ChatInterfaceProps {
  messages: TranscriptMessage[];
  isConnected: boolean;
}

export function ChatInterface({ messages, isConnected }: ChatInterfaceProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Sort messages by timestamp to ensure correct ordering
  const sortedMessages = useMemo(() => {
    return [...messages].sort((a, b) => a.timestamp - b.timestamp);
  }, [messages]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <h3 className="text-lg font-semibold mb-3 text-gray-200">Conversation</h3>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto chat-container bg-gray-800 rounded-lg p-4 space-y-4"
      >
        {!isConnected && sortedMessages.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <p className="text-gray-500 text-center">
              Connect to start a conversation
            </p>
          </div>
        )}

        {isConnected && sortedMessages.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <p className="text-gray-500 text-center">
              Start speaking to begin...
            </p>
          </div>
        )}

        {sortedMessages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`
                max-w-[80%] rounded-lg px-4 py-2
                ${message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-100'
                }
                ${!message.final ? 'opacity-80' : ''}
              `}
            >
              <p className="text-sm">
                {message.text}
                {!message.final && (
                  <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
                )}
              </p>
              <p
                className={`
                  text-xs mt-1
                  ${message.role === 'user' ? 'text-blue-200' : 'text-gray-400'}
                `}
              >
                {message.final
                  ? new Date(message.timestamp).toLocaleTimeString()
                  : 'typing...'
                }
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
