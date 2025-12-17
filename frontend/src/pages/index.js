// Main demo page
import React from 'react';
import ChatWidget from '../components/ChatWidget';

const Home = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-800 mb-4">
            AI Gift Concierge
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Find the perfect jewelry gift with AI assistance
          </p>
          <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-8">
            <p className="text-gray-700 mb-4">
              Click the chat button in the bottom-right corner to get started!
            </p>
            <p className="text-sm text-gray-500">
              Ask me about jewelry recommendations, styles, or gift ideas.
            </p>
          </div>
        </div>
      </div>
      <ChatWidget />
    </div>
  );
};

export default Home;
