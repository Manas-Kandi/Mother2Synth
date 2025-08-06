import { useState, useEffect } from "react";
import { fetchWithProject } from "./api";
import "./QualityGuardStage.css";
import { useGlobalStore } from "./store";

export default function QualityGuardStage({ file }) {
  const [validationReport, setValidationReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const projectSlug = useGlobalStore((state) => state.projectSlug);

  useEffect(() => {
    if (file && file.name) {
      runQualityValidation();
    }
  }, [file, projectSlug]);

  async function runQualityValidation() {
    if (!file || !file.name || !projectSlug) {
      setError("No file selected or missing project information");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `http://localhost:8000/quality-guard?filename=${encodeURIComponent(file.name)}&project_slug=${encodeURIComponent(projectSlug)}`,
        { method: "POST" }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const report = await response.json();
      setValidationReport(report);
    } catch (err) {
      setError(err.message);
      console.error("Quality validation error:", err);
    } finally {
      setLoading(false);
    }
  }

  function getSeverityColor(severity) {
    switch (severity) {
      case 'critical': return '#ff4444';
      case 'warning': return '#ff8800';
      case 'info': return '#3498db';
      default: return '#95a5a6';
    }
  }

  function getScoreColor(score) {
    if (score >= 0.9) return '#27ae60';
    if (score >= 0.7) return '#f39c12';
    return '#e74c3c';
  }

  if (loading) {
    return (
      <div className="quality-guard-stage">
        <div className="loading-container">
          <div className="spinner"></div>
          <h2>Running Quality Validation...</h2>
          <p>Checking evidence, diversity, and research quality</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="quality-guard-stage">
        <div className="error-container">
          <h2>Quality Validation Error</h2>
          <p>{error}</p>
          <button onClick={runQualityValidation} className="retry-button">
            Retry Validation
          </button>
        </div>
      </div>
    );
  }

  if (!validationReport) {
    return (
      <div className="quality-guard-stage">
        <div className="empty-state">
          <h2>Quality Validation</h2>
          <p>Run comprehensive validation to ensure research quality</p>
          <button onClick={runQualityValidation} className="validate-button">
            Start Validation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="quality-guard-stage">
      <div className="stage-header">
        <h1>Research Quality Validation</h1>
        <div className="validation-score">
          <div className="score-circle" style={{ borderColor: getScoreColor(validationReport.overall_score) }}>
            <span className="score-number">{Math.round(validationReport.overall_score * 100)}</span>
            <span className="score-label">/100</span>
          </div>
          <div className={`status-badge ${validationReport.status.toLowerCase()}`}>
            {validationReport.status}
          </div>
        </div>
      </div>

      <div className="validation-tabs">
        <button 
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          className={`tab ${activeTab === 'issues' ? 'active' : ''}`}
          onClick={() => setActiveTab('issues')}
        >
          Issues ({validationReport.critical_issues.length + validationReport.warnings.length})
        </button>
        <button 
          className={`tab ${activeTab === 'recommendations' ? 'active' : ''}`}
          onClick={() => setActiveTab('recommendations')}
        >
          Recommendations
        </button>
        <button 
          className={`tab ${activeTab === 'details' ? 'active' : ''}`}
          onClick={() => setActiveTab('details')}
        >
          Details
        </button>
      </div>

      <div className="validation-content">
        {activeTab === 'overview' && (
          <div className="overview-section">
            <div className="summary-cards">
              <div className="summary-card">
                <h3>Total Checks</h3>
                <span className="big-number">{validationReport.summary.total_checks}</span>
              </div>
              <div className="summary-card">
                <h3>Passed</h3>
                <span className="big-number passed">{validationReport.summary.passed}</span>
              </div>
              <div className="summary-card">
                <h3>Critical Issues</h3>
                <span className="big-number critical">{validationReport.summary.critical_issues}</span>
              </div>
              <div className="summary-card">
                <h3>Warnings</h3>
                <span className="big-number warning">{validationReport.summary.warnings}</span>
              </div>
            </div>

            <div className="quality-breakdown">
              <h3>Quality Breakdown</h3>
              <div className="quality-items">
                {validationReport.critical_issues.map((issue, index) => (
                  <div key={index} className="quality-item critical">
                    <div className="item-header">
                      <span className="item-name">{issue.check_name}</span>
                      <span className="item-severity" style={{ color: getSeverityColor(issue.severity) }}>
                        {issue.severity.toUpperCase()}
                      </span>
                    </div>
                    <p className="item-details">{issue.details.theme || issue.check_name}</p>
                  </div>
                ))}
                {validationReport.warnings.map((warning, index) => (
                  <div key={index} className="quality-item warning">
                    <div className="item-header">
                      <span className="item-name">{warning.check_name}</span>
                      <span className="item-severity" style={{ color: getSeverityColor(warning.severity) }}>
                        {warning.severity.toUpperCase()}
                      </span>
                    </div>
                    <p className="item-details">{warning.details.theme || warning.check_name}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'issues' && (
          <div className="issues-section">
            <h3>Issues to Address</h3>
            
            {validationReport.critical_issues.length > 0 && (
              <div className="issues-group critical-issues">
                <h4>Critical Issues</h4>
                {validationReport.critical_issues.map((issue, index) => (
                  <div key={index} className="issue-card critical">
                    <div className="issue-header">
                      <span className="issue-name">{issue.check_name}</span>
                      <span className="issue-score">Score: {Math.round(issue.score * 100)}%</span>
                    </div>
                    <div className="issue-details">
                      <p>{JSON.stringify(issue.details, null, 2)}</p>
                    </div>
                    <div className="issue-recommendations">
                      <h5>Recommendations:</h5>
                      <ul>
                        {issue.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {validationReport.warnings.length > 0 && (
              <div className="issues-group warnings">
                <h4>Warnings</h4>
                {validationReport.warnings.map((warning, index) => (
                  <div key={index} className="issue-card warning">
                    <div className="issue-header">
                      <span className="issue-name">{warning.check_name}</span>
                      <span className="issue-score">Score: {Math.round(warning.score * 100)}%</span>
                    </div>
                    <div className="issue-details">
                      <p>{JSON.stringify(warning.details, null, 2)}</p>
                    </div>
                    <div className="issue-recommendations">
                      <h5>Recommendations:</h5>
                      <ul>
                        {warning.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'recommendations' && (
          <div className="recommendations-section">
            <h3>Actionable Recommendations</h3>
            
            <div className="recommendation-cards">
              {validationReport.recommendations.map((rec, index) => (
                <div key={index} className="recommendation-card">
                  <div className="recommendation-icon">💡</div>
                  <div className="recommendation-text">{rec}</div>
                </div>
              ))}
            </div>

            <div className="next-steps">
              <h4>Next Steps</h4>
              <ul>
                {validationReport.next_steps.map((step, index) => (
                  <li key={index}>{step}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'details' && (
          <div className="details-section">
            <h3>Detailed Validation Results</h3>
            
            <div className="validation-summary">
              <h4>Validation Summary</h4>
              <pre>{JSON.stringify(validationReport, null, 2)}</pre>
            </div>

            <div className="export-section">
              <h4>Export Options</h4>
              <div className="export-buttons">
                <button className="export-btn pdf">Export PDF Report</button>
                <button className="export-btn json">Export JSON Data</button>
                <button className="export-btn csv">Export CSV Summary</button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="validation-actions">
        <button onClick={runQualityValidation} className="revalidate-btn">
          Re-run Validation
        </button>
        <button className="export-btn primary">
          Generate Report
        </button>
      </div>
    </div>
  );
}
