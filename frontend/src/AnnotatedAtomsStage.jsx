import "./AnnotatedAtomsStage.css";

export default function AnnotatedAtomsStage({ file }) {
  if (!file || !file.annotated || file.annotated.length === 0) {
    return (
      <div className="annotations-stage">
        <div className="empty-state">
          <div className="empty-icon">🏷️</div>
          <h2 className="empty-title">No annotations available</h2>
          <p className="empty-text">Annotations will appear here after atoms are processed</p>
        </div>
      </div>
    );
  }

  const totalAnnotations = file.annotated.length;
  const uniqueSpeakers = [...new Set(file.annotated.map(a => a.speaker))];
  const sentimentCounts = file.annotated.reduce((acc, a) => {
    acc[a.sentiment] = (acc[a.sentiment] || 0) + 1;
    return acc;
  }, {});

  // Helper functions for styling
  const getSentimentColor = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return '#10b981';
      case 'negative': return '#ef4444';
      case 'neutral': return '#6b7280';
      default: return '#6b7280';
    }
  };

  const getSpeechActIcon = (speechAct) => {
    switch (speechAct?.toLowerCase()) {
      case 'question': return '❓';
      case 'complaint': return '😤';
      case 'opinion': return '💭';
      case 'request': return '🙏';
      case 'praise': return '👍';
      default: return '💬';
    }
  };

  return (
    <div className="annotations-stage">
      <div className="annotations-document">
        <div className="document-header">
          <h1 className="document-title">Annotations</h1>
          <p className="document-subtitle">{file.name.replace('.pdf', '')}</p>
          <div className="document-meta">
            {totalAnnotations} annotated insights · {uniqueSpeakers.length} speakers
          </div>
          
          <div className="sentiment-overview">
            {Object.entries(sentimentCounts).map(([sentiment, count]) => (
              <div key={sentiment} className="sentiment-badge" style={{ '--sentiment-color': getSentimentColor(sentiment) }}>
                <span className="sentiment-dot"></span>
                <span className="sentiment-label">{sentiment}</span>
                <span className="sentiment-count">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="annotations-content">
          <div className="annotations-grid">
            {file.annotated.map((atom, i) => {
              const isInterviewer = atom.speaker?.toLowerCase().includes('interviewer');
              const speakerIndex = uniqueSpeakers.indexOf(atom.speaker || 'Unknown') % 3;
              
              return (
                <div key={atom.id || i} className={`annotation-card speaker-${speakerIndex}`}>
                  <div className="annotation-header">
                    <div className="speaker-info">
                      <div className={`speaker-dot ${isInterviewer ? 'interviewer' : 'participant'}`}>
                        {isInterviewer ? 'I' : 'P'}
                      </div>
                      <span className="speaker-name">{atom.speaker || 'Unknown'}</span>
                    </div>
                    <div className="annotation-number">#{i + 1}</div>
                  </div>

                  <div className="annotation-content">
                    <p className="annotation-text">{atom.text}</p>
                  </div>

                  <div className="annotation-tags">
                    <div className="primary-tags">
                      <div className="speech-act-tag">
                        <span className="tag-icon">{getSpeechActIcon(atom.speech_act)}</span>
                        <span className="tag-label">{atom.speech_act}</span>
                      </div>
                      
                      <div 
                        className="sentiment-tag"
                        style={{ '--sentiment-color': getSentimentColor(atom.sentiment) }}
                      >
                        <span className="sentiment-indicator"></span>
                        <span className="tag-label">{atom.sentiment}</span>
                      </div>
                    </div>

                    {atom.insights && atom.insights.length > 0 && (
                      <div className="insights-section">
                        <h4 className="insights-title">Insights</h4>
                        <div className="insights-grid">
                          {atom.insights.map((insight, idx) => (
                            <div key={idx} className="insight-item">
                              <span className="insight-type">{insight.type}</span>
                              <span className="insight-label">{insight.label}</span>
                              <span className="insight-weight">({insight.weight})</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {atom.tags && atom.tags.length > 0 && (
                      <div className="custom-tags">
                        {atom.tags.map((tag, idx) => (
                          <span key={idx} className="custom-tag">{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>

                  {atom.source_file && (
                    <div className="annotation-footer">
                      <span className="source-file">{atom.source_file}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}