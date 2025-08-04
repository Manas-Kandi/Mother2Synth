import "./BoardStage.css";

export default function BoardStage({ file }) {
  if (!file || !file.board) {
    return (
      <div className="board-stage">
        <div className="empty-state">
          <div className="empty-icon">🗂️</div>
          <h2 className="empty-title">No board data</h2>
          <p className="empty-text">Create a board to visualize themes and insights.</p>
        </div>
      </div>
    );
  }

  const board = file.board;

  return (
    <div className="board-stage">
      <header className="board-header">
        <h1 className="board-title">Research Board</h1>
        {board.board_url && (
          <a
            href={board.board_url}
            target="_blank"
            rel="noopener noreferrer"
            className="board-link"
          >
            Open Collaborative Board ↗
          </a>
        )}
      </header>

      <div className="board-content">
        <pre className="board-json">
          {JSON.stringify(board, null, 2)}
        </pre>
      </div>
    </div>
  );
}

