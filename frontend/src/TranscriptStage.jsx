import { useState, useRef, useEffect } from "react";
import { useGlobalStore } from "./store";
import "./TranscriptStage.css";

export default function TranscriptStage({ file }) {
  const [comments, setComments] = useState({});
  const [activeComment, setActiveComment] = useState(null);
  const [commentInput, setCommentInput] = useState("");
  const [showCommentBox, setShowCommentBox] = useState(false);
  const [commentPosition, setCommentPosition] = useState({ top: 0, exchangeId: null });
  const [highlightedText, setHighlightedText] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const documentRef = useRef(null);
  const projectSlug = useGlobalStore((state) => state.projectSlug);

  // Load existing comments when file changes
  useEffect(() => {
    if (file?.name) {
      loadComments();
    }
  }, [file?.name, projectSlug]);

  const loadComments = async () => {
    try {
      const response = await fetch(`http://localhost:8000/comments/${encodeURIComponent(file.name)}?project_slug=${projectSlug}`);
      if (response.ok) {
        const data = await response.json();
        setComments(data.comments || {});
      }
    } catch (error) {
      console.error('Failed to load comments:', error);
    }
  };

  const saveComment = async (comment, exchangeId) => {
    try {
      setIsLoading(true);
      const response = await fetch(`http://localhost:8000/comments/${encodeURIComponent(file.name)}?project_slug=${projectSlug}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          exchangeId,
          comment: {
            ...comment,
            author: 'Current User', // This would come from auth system
            filename: file.name
          }
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to save comment');
      }
      
      const result = await response.json();
      return result.success;
    } catch (error) {
      console.error('Failed to save comment:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const removeComment = async (exchangeId, commentId) => {
    try {
      const response = await fetch(`http://localhost:8000/comments/${encodeURIComponent(file.name)}/${commentId}?project_slug=${projectSlug}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete comment');
      }
      
      return true;
    } catch (error) {
      console.error('Failed to delete comment:', error);
      return false;
    }
  };

  if (!file || !file.cleaned) {
    return (
      <div className="transcript-stage">
        <div className="empty-state">
          <div className="empty-icon">📝</div>
          <h2 className="empty-title">No transcript selected</h2>
          <p className="empty-text">Choose a file from the sidebar to start reviewing</p>
        </div>
      </div>
    );
  }

  const transcript = file.cleaned;
  const SPEAKER_RE = /(Speaker\s*\d+|Interviewer|Participant|[A-Z][a-z]+(?:\s\[inferred\])?):\s*(.*?)(?=(?:\n(?:[A-Z][a-z]+|Speaker|Participant|Interviewer)|$))/gis;

  const blocks = [];
  let match;
  while ((match = SPEAKER_RE.exec(transcript)) !== null) {
    const speaker = match[1].trim();
    const text = match[2].trim();
    if (text) blocks.push({ speaker, text });
  }

  const uniqueSpeakers = [...new Set(blocks.map(b => b.speaker))];

  const handleTextSelection = (exchangeId) => {
    const selection = window.getSelection();
    if (selection.toString().trim()) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      const containerRect = documentRef.current.getBoundingClientRect();
      
      setCommentPosition({
        top: rect.top - containerRect.top + rect.height / 2,
        exchangeId: exchangeId,
        selectedText: selection.toString().trim()
      });
      setShowCommentBox(true);
      setActiveComment(null);
      setHighlightedText(null);
    }
  };

  const addComment = async () => {
    if (commentInput.trim() && commentPosition.selectedText) {
      const commentId = Date.now();
      const newComment = {
        id: commentId,
        text: commentInput.trim(),
        selectedText: commentPosition.selectedText,
        timestamp: new Date().toISOString(),
        position: commentPosition.top,
        exchangeIndex: commentPosition.exchangeId
      };
      
      // Optimistically update UI
      setComments(prev => ({
        ...prev,
        [commentPosition.exchangeId]: [
          ...(prev[commentPosition.exchangeId] || []),
          newComment
        ]
      }));
      
      // Save to backend
      const success = await saveComment(newComment, commentPosition.exchangeId);
      
      if (!success) {
        // Revert on failure
        setComments(prev => ({
          ...prev,
          [commentPosition.exchangeId]: prev[commentPosition.exchangeId].filter(c => c.id !== commentId)
        }));
        alert('Failed to save comment. Please try again.');
        return;
      }
      
      setCommentInput("");
      setShowCommentBox(false);
      setCommentPosition({ top: 0, exchangeId: null });
      window.getSelection().removeAllRanges();
    }
  };

  const handleCommentClick = (comment, exchangeId) => {
    setActiveComment(comment.id);
    setHighlightedText({
      text: comment.selectedText,
      exchangeId: exchangeId
    });
  };

  const deleteComment = async (exchangeId, commentId) => {
    // Optimistically update UI
    const originalComments = comments[exchangeId];
    setComments(prev => ({
      ...prev,
      [exchangeId]: prev[exchangeId].filter(c => c.id !== commentId)
    }));
    
    // Remove from backend
    const success = await removeComment(exchangeId, commentId);
    
    if (!success) {
      // Revert on failure
      setComments(prev => ({
        ...prev,
        [exchangeId]: originalComments
      }));
      alert('Failed to delete comment. Please try again.');
      return;
    }
    
    if (activeComment === commentId) {
      setActiveComment(null);
      setHighlightedText(null);
    }
  };

  const cancelComment = () => {
    setShowCommentBox(false);
    setCommentInput("");
    setCommentPosition({ top: 0, exchangeId: null });
    window.getSelection().removeAllRanges();
  };

  // Get all comments sorted by position for sidebar
  const allComments = Object.entries(comments).flatMap(([exchangeId, exchangeComments]) =>
    exchangeComments.map(comment => ({ ...comment, exchangeId: parseInt(exchangeId) }))
  ).sort((a, b) => a.position - b.position);

  return (
    <div className="transcript-stage">
      <div className="transcript-container" ref={documentRef}>
        <div className="transcript-document">
          <div className="document-header">
            <h1 className="document-title">{file.name.replace('.pdf', '')}</h1>
            <div className="document-meta">
              {blocks.length} exchanges · {uniqueSpeakers.length} speakers · {allComments.length} comments
            </div>
          </div>

          <div className="transcript-flow">
            {blocks.map((block, i) => {
              const isInterviewer = block.speaker.toLowerCase().includes('interviewer');
              const exchangeComments = comments[i] || [];
              const isHighlighted = highlightedText && highlightedText.exchangeId === i;
              
              return (
                <div key={i} className={`exchange ${exchangeComments.length > 0 ? 'has-comments' : ''}`}>
                  <div className="speaker-indicator">
                    <div className={`speaker-dot ${isInterviewer ? 'interviewer' : 'participant'}`}>
                      {isInterviewer ? 'I' : 'P'}
                    </div>
                    <span className="speaker-label">{block.speaker}</span>
                    {exchangeComments.length > 0 && (
                      <div className="comment-count">
                        {exchangeComments.length}
                      </div>
                    )}
                  </div>
                  
                  <div 
                    className={`exchange-content ${isHighlighted ? 'highlighted' : ''}`}
                    onMouseUp={(e) => handleTextSelection(i, e)}
                  >
                    {block.text}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Comments Sidebar */}
        <div className="comments-sidebar">
          {showCommentBox && (
            <div 
              className="comment-composer"
              style={{ top: commentPosition.top - 50 }}
            >
              <div className="comment-quote">
                "{commentPosition.selectedText}"
              </div>
              <textarea
                value={commentInput}
                onChange={(e) => setCommentInput(e.target.value)}
                placeholder="Add your research note..."
                className="comment-input"
                autoFocus
                rows="3"
              />
              <div className="comment-actions">
                <button className="cancel-btn" onClick={cancelComment}>
                  Cancel
                </button>
                <button 
                  className={`add-btn ${isLoading ? 'loading' : ''}`}
                  onClick={addComment}
                  disabled={!commentInput.trim() || isLoading}
                >
                  {isLoading ? 'Saving...' : 'Comment'}
                </button>
              </div>
            </div>
          )}

          {allComments.map((comment) => (
            <div 
              key={comment.id}
              className={`comment-card ${activeComment === comment.id ? 'active' : ''}`}
              style={{ top: comment.position - 20 }}
              onClick={() => handleCommentClick(comment, comment.exchangeId)}
            >
              <div className="comment-content">
                <div className="comment-quote">"{comment.selectedText}"</div>
                <div className="comment-text">{comment.text}</div>
                <div className="comment-meta">{comment.timestamp}</div>
              </div>
              <button 
                className="delete-comment"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteComment(comment.exchangeId, comment.id);
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}