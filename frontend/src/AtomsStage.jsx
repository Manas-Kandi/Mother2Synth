import "./AtomsStage.css";

export default function AtomsStage({ file }) {
  if (!file || !file.atoms || file.atoms.length === 0) {
    return (
      <div className="atoms-stage">
        <div className="empty-state">
          <div className="empty-icon">⚛️</div>
          <h2 className="empty-title">No atoms generated yet</h2>
          <p className="empty-text">Atoms will appear here after the transcript is processed</p>
        </div>
      </div>
    );
  }

  // Group atoms by speaker for better organization
  const atomsBySpeaker = file.atoms.reduce((acc, atom) => {
    const speaker = atom.speaker || 'Unknown';
    if (!acc[speaker]) acc[speaker] = [];
    acc[speaker].push(atom);
    return acc;
  }, {});

  const uniqueSpeakers = Object.keys(atomsBySpeaker);
  const totalAtoms = file.atoms.length;

  return (
    <div className="atoms-stage">
      <div className="atoms-document">
        <div className="document-header">
          <h1 className="document-title">Atoms</h1>
          <p className="document-subtitle">{file.name.replace('.pdf', '')}</p>
          <div className="document-meta">
            {totalAtoms} insights · {uniqueSpeakers.length} speakers
          </div>
        </div>

        <div className="atoms-content">
          <div className="atoms-grid">
            {file.atoms.map((atom, i) => {
              const isInterviewer = atom.speaker?.toLowerCase().includes('interviewer');
              const speakerIndex = uniqueSpeakers.indexOf(atom.speaker || 'Unknown') % 3;
              
              return (
                <div key={atom.id || i} className={`atom-card speaker-${speakerIndex}`}>
                  <div className="atom-header">
                    <div className="speaker-info">
                      <div className={`speaker-dot ${isInterviewer ? 'interviewer' : 'participant'}`}>
                        {isInterviewer ? 'I' : 'P'}
                      </div>
                      <span className="speaker-name">{atom.speaker || 'Unknown'}</span>
                    </div>
                    <div className="atom-number">#{i + 1}</div>
                  </div>
                  
                  <div className="atom-content">
                    <p className="atom-text">{atom.text}</p>
                  </div>
                  
                  {atom.source_file && (
                    <div className="atom-footer">
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