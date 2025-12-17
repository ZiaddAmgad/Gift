import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

export const useChat = () => {
  const [messages, setMessages] = useState([
    { 
      type: 'bot', 
      text: "Welcome! I can help you find the perfect gift. Who are you shopping for today?" 
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  // 1. Initialize Session ID
  useEffect(() => {
    if (typeof window === 'undefined') return;
    let storedId = localStorage.getItem('chat_session_id');
    if (!storedId) {
      storedId = uuidv4();
      localStorage.setItem('chat_session_id', storedId);
    }
    setSessionId(storedId);
  }, []);

  // 2. Send Message Logic
  const sendMessage = useCallback(async (text) => {
    if (!text || !text.trim()) return;

    setMessages(prev => [...prev, { type: 'user', text }]);
    setLoading(true);

    let currentSessionId = sessionId;
    if (!currentSessionId) {
      currentSessionId = localStorage.getItem('chat_session_id') || uuidv4();
      setSessionId(currentSessionId);
    }

    try {
      // --- CRITICAL FIX HERE ---
      // Uses the Vercel Environment Variable if available, otherwise Localhost
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: text, 
          session_id: currentSessionId 
        }),
      });

      const data = await response.json();

      if (data.message) {
        setMessages(prev => [...prev, { type: 'bot', text: data.message }]);
      }

      if (data.products && data.products.length > 0) {
        setMessages(prev => [...prev, { type: 'products', items: data.products }]);
      }

    } catch (error) {
      console.error("Chat Error:", error);
      setMessages(prev => [...prev, { type: 'bot', text: "Sorry, I'm having trouble connecting to the server." }]);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  return { messages, sendMessage, loading };
};

export default useChat;