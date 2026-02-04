// frontend/app/page.js

'use client';

import { useState, useRef, useEffect } from 'react';

export default function Home() {
  // State
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [subject, setSubject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [message, setMessage] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(true);
  
  // Refs
  const chatEndRef = useRef(null);
  const messageInputRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // Focus input after sending message
  useEffect(() => {
    if (!loading && sessionId) {
      messageInputRef.current?.focus();
    }
  }, [loading, sessionId]);

  const analyzeContent = async () => {
    if (!youtubeUrl) return;
    
    setLoading(true);
    setChatHistory([]);
    setSuggestions([]);
    setSubject(null);
    
    try {
      const response = await fetch('http://localhost:8000/api/analyze-content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: youtubeUrl }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSessionId(data.session_id);
        setSubject(data.subject);
        setSuggestions(data.suggested_questions || []);
        setShowSuggestions(true);
        
        // Add welcome message to chat
        setChatHistory([{
          role: 'assistant',
          content: `Great! I've analyzed this ${data.subject.subject} tutorial about "${data.subject.topic}". I'm ready to help you learn! Ask me anything or use the suggestions below. 🚀`
        }]);
      } else {
        alert('Error: ' + (data.detail || 'Unknown error'));
      }
    } catch (error) {
      alert('Error connecting to API: ' + error.message);
    }
    
    setLoading(false);
  };

  const sendMessage = async (messageText) => {
    const textToSend = messageText || message;
    if (!textToSend.trim() || !sessionId) return;
    
    // Add user message to chat immediately
    const userMessage = { role: 'user', content: textToSend };
    setChatHistory(prev => [...prev, userMessage]);
    setMessage('');
    setLoading(true);
    setShowSuggestions(false);
    
    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: textToSend,
          screenshot: '', // We'll add screenshot feature later
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Add assistant response
        const assistantMessage = { role: 'assistant', content: data.response };
        setChatHistory(prev => [...prev, assistantMessage]);
      } else {
        alert('Error getting response');
      }
    } catch (error) {
      alert('Error: ' + error.message);
    }
    
    setLoading(false);
  };

  const refreshSuggestions = async () => {
    if (!sessionId) return;
    
    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/generate-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuggestions(data.suggestions);
        setShowSuggestions(true);
      }
    } catch (error) {
      console.error('Error refreshing suggestions:', error);
    }
    
    setLoading(false);
  };

  const useSuggestion = (suggestion) => {
    setMessage(suggestion);
    messageInputRef.current?.focus();
  };

  const clearChat = () => {
    if (confirm('Start a new learning session?')) {
      setSessionId('');
      setSubject(null);
      setChatHistory([]);
      setSuggestions([]);
      setYoutubeUrl('');
      setShowSuggestions(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 text-black">
      {/* Header */}
      <div className="bg-white shadow-md">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-indigo-900">SHOWDESK</h1>
              <p className="text-sm text-gray-600">Chat with any educational video</p>
            </div>
            {sessionId && (
              <button
                onClick={clearChat}
                className="px-4 py-2 text-sm bg-gray-200 hover:bg-gray-300 rounded-lg transition"
              >
                ↻ New Session
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Video Analysis Section */}
        {!sessionId && (
          <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
            <h2 className="text-2xl font-semibold mb-4 text-gray-800">
              🎥 Start Learning
            </h2>
            <p className="text-gray-600 mb-6">
              Paste any YouTube video URL and I'll help you understand it through conversation
            </p>
            <div className="flex gap-3">
              <input
                type="text"
                placeholder="https://youtube.com/watch?v=..."
                className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-lg"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && analyzeContent()}
              />
              <button
                onClick={analyzeContent}
                disabled={loading || !youtubeUrl}
                className="px-8 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition text-lg"
              >
                {loading ? 'Analyzing...' : 'Start Chat'}
              </button>
            </div>
            
            {/* Example URLs */}
            <div className="mt-6 text-sm">
              <p className="text-gray-600 mb-2">Try these examples:</p>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => setYoutubeUrl('https://www.youtube.com/watch?v=kqtD5dpn9C8')}
                  className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
                >
                  Python Tutorial
                </button>
                <button
                  onClick={() => setYoutubeUrl('https://www.youtube.com/watch?v=yKm4YXMPVYM')}
                  className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
                >
                  React Basics
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Subject Info Bar */}
        {subject && (
          <div className="bg-white rounded-lg shadow-md p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-2xl">
                  {subject.subject === 'coding' && '💻'}
                  {subject.subject === 'history' && '📚'}
                  {subject.subject === 'science' && '🔬'}
                  {subject.subject === 'language' && '🗣️'}
                  {subject.subject === 'math' && '🔢'}
                  {!['coding', 'history', 'science', 'language', 'math'].includes(subject.subject) && '📖'}
                </div>
                <div>
                  <p className="font-semibold text-gray-800">{subject.topic}</p>
                  <p className="text-sm text-gray-600">
                    {subject.subject} • {subject.level} • {chatHistory.filter(m => m.role === 'user').length} questions asked
                  </p>
                </div>
              </div>
              <button
                onClick={refreshSuggestions}
                disabled={loading}
                className="px-4 py-2 text-sm bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded-lg transition"
              >
                💡 New Suggestions
              </button>
            </div>
          </div>
        )}

        {/* Chat Interface */}
        {sessionId && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Chat Area */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-xl shadow-lg overflow-hidden flex flex-col" style={{ height: '600px' }}>
                {/* Chat Messages */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  {chatHistory.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                          msg.role === 'user'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    </div>
                  ))}
                  
                  {loading && (
                    <div className="flex justify-start">
                      <div className="bg-gray-100 rounded-2xl px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div ref={chatEndRef} />
                </div>

                {/* Message Input */}
                <div className="border-t border-gray-200 p-4 bg-gray-50">
                  <div className="flex gap-2">
                    <input
                      ref={messageInputRef}
                      type="text"
                      placeholder="Ask anything about the video..."
                      className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                      disabled={loading}
                    />
                    <button
                      onClick={() => sendMessage()}
                      disabled={loading || !message.trim()}
                      className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition"
                    >
                      Send
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Press Enter to send • Shift+Enter for new line
                  </p>
                </div>
              </div>
            </div>

            {/* Suggestions Sidebar */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-800">💡 Suggested Questions</h3>
                  <button
                    onClick={() => setShowSuggestions(!showSuggestions)}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    {showSuggestions ? '−' : '+'}
                  </button>
                </div>
                
                {showSuggestions && (
                  <div className="space-y-2">
                    {suggestions.length > 0 ? (
                      suggestions.map((suggestion, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            sendMessage(suggestion);
                            setShowSuggestions(false);
                          }}
                          className="w-full text-left px-4 py-3 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition text-sm text-gray-700 hover:text-indigo-900"
                        >
                          <span className="text-indigo-600 mr-2">•</span>
                          {suggestion}
                        </button>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500 italic">
                        Loading suggestions...
                      </p>
                    )}
                  </div>
                )}
                
                {/* Tips */}
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <h4 className="font-semibold text-sm text-gray-700 mb-3">💭 Tips</h4>
                  <ul className="space-y-2 text-xs text-gray-600">
                    <li>• Ask for clarification on confusing parts</li>
                    <li>• Request examples or analogies</li>
                    <li>• Ask "why" to understand deeper</li>
                    <li>• Request real-world applications</li>
                  </ul>
                </div>

                {/* Stats */}
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <h4 className="font-semibold text-sm text-gray-700 mb-3">📊 This Session</h4>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Questions asked:</span>
                      <span className="font-semibold">{chatHistory.filter(m => m.role === 'user').length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Concepts covered:</span>
                      <span className="font-semibold">{subject?.concepts?.length || 0}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}