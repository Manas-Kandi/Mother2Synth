import { useState, useEffect, useRef, useCallback } from "react";
import { useGlobalStore } from "./store";
import { fetchWithProject } from "./api";
import "./ChatAssistantStage.css";

export default function ChatAssistantStage({ file }) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [contextPanel, setContextPanel] = useState(false);
  const projectSlug = useGlobalStore((state) => state.projectSlug);
  
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load conversation history
  useEffect(() => {
    if (projectSlug) {
      loadConversationHistory();
    }
  }, [projectSlug, loadConversationHistory]);

  const loadConversationHistory = useCallback(async () => {
    if (!projectSlug) return;

    try {
      const response = await fetchWithProject(
        '/chat/history',
        {},
        projectSlug
      );

      if (response.ok) {
        const history = await response.json();
        const chatMessages = [
          {
            role: "assistant",
            content: "Hello! I'm your research synthesis assistant. I can help you understand themes, suggest improvements, validate quality, and guide you through the research process. What would you like to explore?",
            timestamp: new Date().toISOString()
          }
        ];
        
        // If there's existing history, load it
        if (history && history.messages && history.messages.length > 0) {
          setMessages(history.messages);
        } else {
          setMessages(chatMessages);
        }
      }
    } catch (err) {
      console.error("Failed to load conversation history:", err);
    }
  }, [projectSlug]);

  async function sendMessage() {
    if (!inputMessage.trim() || !projectSlug) return;

    const userMessage = {
      role: "user",
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setLoading(true);
    setError(null);

    try {
      const response = await fetchWithProject("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: inputMessage,
          context: {
            filename: file.name,
            themes: file.graph?.themes || [],
            atoms: file.atoms || [],
            insights: file.annotated?.insights || [],
            board: file.board || {},
            stage: "quality_assurance"
          }
        })
      }, file.project_slug);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      const assistantMessage = {
        role: "assistant",
        content: data.response,
        timestamp: new Date().toISOString(),
        suggestions: data.suggestions,
        actions: data.actions
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.message);
      console.error("Chat error:", err);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyPress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function executeAction(action) {
    // Handle action buttons from assistant responses
    console.log("Executing action:", action);
    
    switch (action.type) {
      case 'run_quality_check':
        // Navigate to quality guard stage
        window.dispatchEvent(new CustomEvent('navigate-to-stage', { detail: 6 }));
        break;
      case 'show_quotes': {
        // Show supporting quotes for a theme
        const quotesMessage = {
          role: "assistant",
          content: `Here are the supporting quotes for this theme:`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, quotesMessage]);
        break;
        }
      case 'add_quote': {
        // Add a quote to theme evidence
        const addMessage = {
          role: "assistant",
          content: `Quote added to theme evidence.`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, addMessage]);
        break;
        }
      default:
        console.log("Unknown action type:", action.type);
    }
  }

  function getQuickSuggestions() {
    return [
      "Explain the themes",
      "Suggest improvements",
      "Check evidence quality",
      "Help with methodology",
      "Validate research quality",
      "Export recommendations"
    ];
  }

  function sendQuickSuggestion(suggestion) {
    setInputMessage(suggestion);
  }

  return (
    <div className="chat-assistant-stage">
      <div className="stage-header">
        <h1>Research Assistant</h1>
        <div className="assistant-info">
          <span className="ai-badge">AI Assistant</span>
          {file && (
            <span className="context-info">
              Context: {file.name}
            </span>
          )}
        </div>
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-avatar">
                {message.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-text">
                  {message.content.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
                
                {message.suggestions && (
                  <div className="message-suggestions">
                    <h4>Suggestions:</h4>
                    <ul>
                      {message.suggestions.map((suggestion, i) => (
                        <li key={i}>{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {message.actions && (
                  <div className="message-actions">
                    {message.actions.map((action, i) => (
                      <button
                        key={i}
                        className="action-button"
                        onClick={() => executeAction(action)}
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                )}

                <div className="message-timestamp">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant loading">
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
            <button onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        <div className="quick-suggestions">
          <h4>Quick Questions:</h4>
          <div className="suggestion-chips">
            {getQuickSuggestions().map((suggestion, index) => (
              <button
                key={index}
                className="suggestion-chip"
                onClick={() => sendQuickSuggestion(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>

        <div className="chat-input-container">
          <textarea
            className="chat-input"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything about your research..."
            rows={3}
          />
          <div className="input-actions">
            <button 
              className="send-button"
              onClick={sendMessage}
              disabled={!inputMessage.trim() || loading}
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
            <button 
              className="context-button"
              onClick={() => setContextPanel(!contextPanel)}
            >
              Context
            </button>
          </div>
        </div>
      </div>

      {contextPanel && (
        <div className="context-panel">
          <h3>Current Context</h3>
          <div className="context-info">
            <p><strong>Project:</strong> {file?.project_slug || 'Not set'}</p>
            <p><strong>File:</strong> {file?.name || 'Not selected'}</p>
            <p><strong>Stage:</strong> {file ? 'Quality Assurance' : 'Setup'}</p>
            <p><strong>Themes:</strong> {file?.graph?.themes?.length || 0}</p>
            <p><strong>Atoms:</strong> {file?.atoms?.length || 0}</p>
          </div>
          <button onClick={() => setContextPanel(false)}>Close</button>
        </div>
      )}
    </div>
  );
}
