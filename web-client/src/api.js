import axios from 'axios';

// We'll create a simple API service that communicates with our backend
const API_URL = 'http://localhost:5000'; // Adjust if your backend runs on a different port

const api = {
  // Process a query with optional conversation history
  processQuery: async (query, conversationHistory = []) => {
    try {
      const response = await axios.post(`${API_URL}/api/process`, {
        query,
        history: conversationHistory
      });
      return response.data;
    } catch (error) {
      console.error('Error processing query:', error);
      throw error;
    }
  },
};

export default api; 