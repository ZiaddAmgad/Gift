import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

// 1 Hour in milliseconds
const IDLE_TIMEOUT_MS = 60 * 60 * 1000; 

export const useChat = () => {
  const initialMessage = { 
    type: 'bot', 
    text: "Welcome! I can help you find the perfect gift. Who are you shopping for today?" 
  };

  const [messages, setMessages] = useState([initialMessage]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  // 1. ON LOAD: Check if we have valid history
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // A. Setup Session ID (Never expires, identifies the user)
    let storedId = localStorage.getItem('chat_session_id');
    if (!storedId) {
      storedId = uuidv4();
      localStorage.setItem('chat_session_id', storedId);
    }
    setSessionId(storedId);

    // B. Check Chat History (Expires after 1 hour of inactivity)
    const savedString = localStorage.getItem('chat_history');
    if (savedString) {
      try {
        const saved = JSON.parse(savedString);
        const now = Date.now();
        
        // Calculate how long since the last message was saved
        const timeSinceLastMessage = now - saved.timestamp;

        if (timeSinceLastMessage < IDLE_TIMEOUT_MS) {
          // STILL FRESH: Restore the chat
          setMessages(saved.data);
        } else {
          // EXPIRED: Delete only this chat history
          console.log("Session expired. Clearing chat history.");
          localStorage.removeItem('chat_history');
          // We do NOT clear 'chat_session_id', so the backend still knows it's the same user returning
        }
      } catch (e) {
        console.error("Error parsing chat history:", e);
        localStorage.removeItem('chat_history');
      }
    }
  }, []);

  // 2. ON UPDATE: Save history and RESET the timer
  useEffect(() => {
    // Only save if we have more than just the greeting
    if (messages.length > 1) {
      const payload = JSON.stringify({
        timestamp: Date.now(), // <--- This resets the 1-hour timer every time a message is added
        data: messages
      });
      localStorage.setItem('chat_history', payload);
    }
  }, [messages]);

  // 3. Send Logic
  const sendMessage = useCallback(async (text) => {
    if (!text || !text.trim()) return;

    // UI Update (Optimistic)
    setMessages(prev => [...prev, { type: 'user', text }]);
    setLoading(true);

    let currentSessionId = sessionId || localStorage.getItem('chat_session_id') || uuidv4();

    try {
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