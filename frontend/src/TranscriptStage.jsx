import { useState, useRef } from "react";
import "./TranscriptStage.css";

export default function TranscriptStage({ file }) {
  const [comments, setComments] = useState({});
  const [activeComment, setActiveComment] = useState(null);
  const [commentInput, setCommentInput] = useState("");
  const [showCommentBox, setShowCommentBox] = useState(false);
  const [commentPosition, setCommentPosition] = useState({ top: 0, exchangeId: null });
  const [highlightedText, setHighlightedText] = useState(null);
  const documentRef = useRef(null);

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

  const handleTextSelection = (exchangeId, event) => {
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

  const addComment = () => {
    if (commentInput.trim() && commentPosition.selectedText) {
      const commentId = Date.now();
      const newComment = {
        id: commentId,
        text: commentInput.trim(),
        selectedText: commentPosition.selectedText,
        timestamp: new Date().toLocaleString(),
        position: commentPosition.top
      };
      
      setComments(prev => ({
        ...prev,
        [commentPosition.exchangeId]: [
          ...(prev[commentPosition.exchangeId] || []),
          newComment
        ]
      }));
      
      setCommentInput("");
      setShowCommentBox(false);
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

  const deleteComment = (exchangeId, commentId) => {
    setComments(prev => ({
      ...prev,
      [exchangeId]: prev[exchangeId].filter(c => c.id !== commentId)
    }));
    if (activeComment === commentId) {
      setActiveComment(null);
      setHighlightedText(null);
    }
  };

  const cancelComment = () => {
    setShowCommentBox(false);
    setCommentInput("");
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
              const speakerIndex = uniqueSpeakers.indexOf(block.speaker) % 3;
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
                    data-highlighted-text={isHighlighted ? highlightedText.text : ''}
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
                  className="add-btn"
                  onClick={addComment}
                  disabled={!commentInput.trim()}
                >
                  Comment
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