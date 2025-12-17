import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import ProductCard from './ProductCard';

const ChatWindow = ({ isOpen, onClose }) => {
  const { messages, sendMessage, loading } = useChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="fixed bottom-24 right-6 w-96 h-[600px] bg-white rounded-xl shadow-2xl flex flex-col z-50 border border-gray-200 overflow-hidden font-sans">
      
      {/* Header */}
      <div className="bg-blue-600 p-4 flex justify-between items-center text-white shadow-md">
        <div>
          <h3 className="font-bold text-lg">AI Gift Concierge</h3>
          <p className="text-xs text-blue-100 opacity-90">Ask me about jewelry recommendations</p>
        </div>
        <button 
          onClick={onClose} 
          className="hover:bg-blue-700 p-1 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            
            {msg.type === 'products' ? (
              // RENDER PRODUCT CARDS
              <div className="w-full max-w-[90%]">
                {msg.items.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
            ) : (
              // RENDER TEXT BUBBLES
              <div className={`max-w-[85%] px-4 py-3 text-sm shadow-sm ${
                msg.type === 'user' 
                  ? 'bg-blue-600 text-white rounded-2xl rounded-br-none' 
                  : 'bg-white border border-gray-100 text-gray-800 rounded-2xl rounded-bl-none'
              }`}>
                {msg.text}
              </div>
            )}
            
          </div>
        ))}
        
        {/* Loading Indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 px-4 py-3 rounded-2xl rounded-bl-none shadow-sm flex items-center space-x-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-75"></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-150"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-100 flex gap-2 shadow-sm">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          className="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
          disabled={loading}
        />
        <button 
          type="submit" 
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white px-5 py-2 rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium text-sm shadow-sm"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatWindow;