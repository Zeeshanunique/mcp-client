import React, { useState } from 'react';
import api from './api';
import './App.css';

function App() {
  const [conversation, setConversation] = useState([]);
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleProcessQuery = async () => {
    if (!query.trim()) return;

    // Add user query to conversation
    const userMessage = {
      role: 'user',
      content: query
    };
    
    setConversation([...conversation, userMessage]);
    setIsProcessing(true);
    
    try {
      // Create history array for the API excluding the current query
      const historyForApi = conversation.map(entry => ({
        role: entry.role,
        content: entry.content
      }));
      
      // Process the query
      const response = await api.processQuery(query, historyForApi);
      
      // Add assistant response to conversation
      const assistantMessage = {
        role: 'assistant',
        content: response.message || response
      };
      
      setConversation(prev => [...prev, assistantMessage]);
      setQuery(''); // Clear input
    } catch (error) {
      // Add error message to conversation
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.message || 'Failed to process query'}`
      };
      
      setConversation(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClearHistory = () => {
    setConversation([]);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleProcessQuery();
    }
  };

  return (
    <div className="app-container">
      <header>
        <h1>MCP Client Interface</h1>
      </header>
      
      <main>
        {conversation.length > 0 && (
          <div className="conversation-container">
            <h2>Conversation History</h2>
            <div className="conversation-history">
              {conversation.map((entry, index) => (
                <div 
                  key={index} 
                  className={`message ${entry.role === 'user' ? 'user-message' : 'assistant-message'}`}
                >
                  <strong>{entry.role === 'user' ? 'You:' : 'Assistant:'}</strong>
                  <p>{entry.content}</p>
                  {index < conversation.length - 1 && <hr />}
                </div>
              ))}
            </div>
          </div>
        )}
        
        <div className="input-container">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter your query..."
            rows={4}
            disabled={isProcessing}
          />
          
          <div className="button-container">
            <button 
              onClick={handleProcessQuery} 
              disabled={!query.trim() || isProcessing}
              className="process-button"
            >
              {isProcessing ? 'Processing...' : 'Process Query'}
            </button>
            
            <button 
              onClick={handleClearHistory}
              disabled={conversation.length === 0 || isProcessing}
              className="clear-button"
            >
              Clear History
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App; 