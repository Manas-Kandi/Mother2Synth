import { useEffect, useState } from "react";
import { fetchWithProject } from "./api";
import "./HumanCheckpointsStage.css";

export default function HumanCheckpointsStage({ file }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchQuestions() {
      if (!file || !file.project_slug) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetchWithProject(
          `/qa?filename=${encodeURIComponent(file.name)}`,
          {},
          file.project_slug
        );
        if (!res.ok) throw new Error("Failed to load checkpoints");
        const data = await res.json();
        if (Array.isArray(data?.questions)) {
          setQuestions(data.questions);
        } else if (Array.isArray(data)) {
          setQuestions(data);
        } else {
          setQuestions([]);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchQuestions();
  }, [file]);

  async function answerQuestion(id, answer) {
    setQuestions(prev => prev.map(q => q.question_id === id ? { ...q, current_answer: answer } : q));
    try {
      await fetchWithProject(
        "/qa/answer",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question_id: id,
            answer
          })
        },
        file.project_slug
      );
    } catch {
      // Ignore errors for now
    }
  }

  if (!file) {
    return (
      <div className="human-checkpoints-stage">
        <div className="empty-state">No file selected</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="human-checkpoints-stage">
        <div className="loading">Loading questions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="human-checkpoints-stage">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  if (!questions.length) {
    return (
      <div className="human-checkpoints-stage">
        <div className="empty-state">No pending questions</div>
      </div>
    );
  }

  return (
    <div className="human-checkpoints-stage">
      <h1>Human Checkpoints</h1>
      <ul className="question-list">
        {questions.map(q => (
          <li key={q.question_id} className="question-item">
            {q.context && <div className="question-context">{q.context}</div>}
            <div className="question-text">{q.question}</div>
            <div className="question-options">
              {q.options?.map(opt => (
                <button
                  key={opt}
                  className={`option-btn ${q.current_answer === opt ? "selected" : ""}`}
                  onClick={() => answerQuestion(q.question_id, opt)}
                >
                  {opt}
                </button>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

