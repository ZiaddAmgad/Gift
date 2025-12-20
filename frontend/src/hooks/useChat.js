import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

const IDLE_TIMEOUT_MS = 60 * 60 * 1000; 

export const useChat = () => {
  const initialMessage = { 
    type: 'bot', 
    text: "Welcome! I can help you find the perfect gift. Who are you shopping for today?" 
  };

  const [messages, setMessages] = useState([initialMessage]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    let storedId = localStorage.getItem('chat_session_id');
    if (!storedId) {
      storedId = uuidv4();
      localStorage.setItem('chat_session_id', storedId);
    }
    setSessionId(storedId);

    const savedString = localStorage.getItem('chat_history');
    if (savedString) {
      try {
        const saved = JSON.parse(savedString);
        if ((Date.now() - saved.timestamp) < IDLE_TIMEOUT_MS) {
          setMessages(saved.data);
        } else {
          localStorage.removeItem('chat_history');
        }
      } catch (e) {
        localStorage.removeItem('chat_history');
      }
    }
  }, []);

  useEffect(() => {
    if (messages.length > 1) {
      const payload = JSON.stringify({
        timestamp: Date.now(),
        data: messages
      });
      localStorage.setItem('chat_history', payload);
    }
  }, [messages]);

  const sendMessage = useCallback(async (text) => {
    if (!text || !text.trim()) return;

    const newUserMsg = { type: 'user', text };
    const newHistory = [...messages, newUserMsg];
    setMessages(newHistory);
    setLoading(true);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      
      const apiHistory = newHistory
        .filter(msg => msg.type === 'user' || msg.type === 'bot')
        .map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.text || "" 
        }));

      const response = await fetch(`${API_BASE}/api/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiHistory }),
      });

      const data = await response.json();
      
      // 1. Stop the initial loading
      setLoading(false); 

      // 2. Handle Text Bubbles with "Inter-Bubble Loading"
      if (data.text_bubbles && Array.isArray(data.text_bubbles)) {
        for (let i = 0; i < data.text_bubbles.length; i++) {
          const bubbleText = data.text_bubbles[i];

          // Add the current bubble
          setMessages(prev => [...prev, { type: 'bot', text: bubbleText }]);
          
          // Check if there are MORE bubbles coming after this one
          if (i < data.text_bubbles.length - 1) {
            setLoading(true); // Show "Typing..."
            await new Promise(resolve => setTimeout(resolve, 3000)); // Wait 3s
            setLoading(false); // Hide "Typing..." to show the next message
          }
        }
      } 
      else if (data.message) {
        setMessages(prev => [...prev, { type: 'bot', text: data.message }]);
      }

      // 3. Show Products (if any)
      if (data.products && data.products.length > 0) {
        // Optional: Small delay before products appear for better pacing
        if (data.text_bubbles?.length > 0) {
            setLoading(true);
            await new Promise(resolve => setTimeout(resolve, 1000));
            setLoading(false);
        }
        setMessages(prev => [...prev, { type: 'products', items: data.products }]);
      }

    } catch (error) {
      console.error("Chat Error:", error);
      setMessages(prev => [...prev, { type: 'bot', text: "I'm having a little trouble connecting. Could you say that again?" }]);
      setLoading(false);
    }
  }, [messages]); 

  return { messages, sendMessage, loading };
};

export default useChat;