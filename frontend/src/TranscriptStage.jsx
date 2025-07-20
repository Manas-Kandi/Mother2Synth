import "./TranscriptStage.css";

export default function TranscriptStage({ file }) {
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

  // Extract speaker blocks
  const SPEAKER_RE = /(Speaker\s*\d+|Interviewer|Participant|[A-Z][a-z]+(?:\s\[inferred\])?):\s*(.*?)(?=(?:\n(?:[A-Z][a-z]+|Speaker|Participant|Interviewer)|$))/gis;

  const blocks = [];
  let match;
  while ((match = SPEAKER_RE.exec(transcript)) !== null) {
    const speaker = match[1].trim();
    const text = match[2].trim();
    if (text) blocks.push({ speaker, text });
  }

  const uniqueSpeakers = [...new Set(blocks.map(b => b.speaker))];

  return (
    <div className="transcript-stage">
      <div className="transcript-document">
        <div className="document-header">
          <h1 className="document-title">{file.name.replace('.pdf', '')}</h1>
          <div className="document-meta">
            {blocks.length} exchanges · {uniqueSpeakers.length} speakers
          </div>
        </div>

        <div className="transcript-flow">
          {blocks.map((block, i) => {
            const speakerIndex = uniqueSpeakers.indexOf(block.speaker) % 3;
            const isInterviewer = block.speaker.toLowerCase().includes('interviewer');
            
            return (
              <div key={i} className={`exchange exchange-${speakerIndex}`}>
                <div className="speaker-indicator">
                  <div className={`speaker-dot ${isInterviewer ? 'interviewer' : 'participant'}`}>
                    {isInterviewer ? 'I' : 'P'}
                  </div>
                  <span className="speaker-label">{block.speaker}</span>
                </div>
                <div className="exchange-content">
                  {block.text}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}