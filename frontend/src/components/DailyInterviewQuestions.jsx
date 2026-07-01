import React, { useState, useEffect } from 'react';
import { getTodayQuestions, getQuestions, rateQuestion } from '../api/interview';

const CATEGORY_LABELS = {
  ml_fundamentals: { label: 'ML Fundamentals', color: 'purple' },
  stats: { label: 'Statistics & Probability', color: 'blue' },
  system_design: { label: 'ML System Design', color: 'indigo' },
  coding: { label: 'Coding / Algorithms', color: 'emerald' },
  behavioral: { label: 'Behavioral / Case Study', color: 'amber' },
  genai: { label: 'GenAI / LLM Specific', color: 'rose' }
};

const DIFFICULTY_LABELS = {
  easy: { label: 'Easy', color: 'success' },
  medium: { label: 'Medium', color: 'warning' },
  hard: { label: 'Hard', color: 'danger' }
};

function parseSources(sourceContext) {
  if (!sourceContext) return [];
  const lines = sourceContext.split('\n');
  const sources = [];
  
  lines.forEach(line => {
    const urlMatch = line.match(/^-\s+(.+?)\s+\[URL:\s*(https?:\/\/[^\]]+)\]/i);
    if (urlMatch) {
      const title = urlMatch[1].trim();
      const url = urlMatch[2].trim();
      try {
        const domain = new URL(url).hostname.replace('www.', '');
        sources.push({ title, url, domain });
      } catch {
        sources.push({ title, url, domain: 'web' });
      }
    } else {
      const lineText = line.replace(/^-\s*/, '').trim();
      if (lineText && !lineText.startsWith('Recent context')) {
        sources.push({ title: lineText, url: '', domain: 'offline' });
      }
    }
  });
  
  const seen = new Set();
  return sources.filter(s => {
    const key = s.url || s.title;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export default function DailyInterviewQuestions() {
  const [activeSubTab, setActiveSubTab] = useState('today'); // 'today' or 'bank'
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Filters for Question Bank
  const [filterCategory, setFilterCategory] = useState('');
  const [filterDifficulty, setFilterDifficulty] = useState('');

  // UI state for revealed answers & ratings
  const [revealedIds, setRevealedIds] = useState(new Set());
  const [submittingRating, setSubmittingRating] = useState({});

  useEffect(() => {
    loadQuestions();
  }, [activeSubTab, filterCategory, filterDifficulty]);

  const loadQuestions = async () => {
    setLoading(true);
    setError('');
    try {
      let data = [];
      if (activeSubTab === 'today') {
        data = await getTodayQuestions();
      } else {
        data = await getQuestions(filterCategory, filterDifficulty);
      }
      setQuestions(data);
    } catch (err) {
      console.error('Error loading questions:', err);
      setError('Failed to load interview questions. Make sure server is running and database is migrated.');
    } finally {
      setLoading(false);
    }
  };

  const toggleReveal = (id) => {
    setRevealedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleRate = async (questionId, rating) => {
    setSubmittingRating(prev => ({ ...prev, [questionId]: true }));
    try {
      const updatedQuestion = await rateQuestion(questionId, rating);
      setQuestions(prev => prev.map(q => q.id === questionId ? updatedQuestion : q));
    } catch (err) {
      console.error('Failed to rate question:', err);
      alert('Failed to submit rating. Please try again.');
    } finally {
      setSubmittingRating(prev => ({ ...prev, [questionId]: false }));
    }
  };

  return (
    <div className="interview-prep-container">
      <div className="task-panel__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <p className="eyebrow">Technical Interview Preparation</p>
          <h2>🧠 Daily AI & Data Science Questions</h2>
        </div>
        
        {/* Toggle between Today and Bank */}
        <div className="sub-tab-picker" style={{ display: 'flex', gap: '0.5rem', background: 'rgba(255,255,255,0.04)', padding: '0.25rem', borderRadius: '12px' }}>
          <button
            type="button"
            className={`tab-toggle-btn ${activeSubTab === 'today' ? 'active' : ''}`}
            onClick={() => { setActiveSubTab('today'); setQuestions([]); }}
            style={{
              padding: '0.45rem 1rem',
              fontSize: '0.85rem',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              background: activeSubTab === 'today' ? 'var(--accent)' : 'transparent',
              color: activeSubTab === 'today' ? '#fff' : 'var(--text-muted)',
              fontWeight: '500',
              transition: 'all 0.2s ease'
            }}
          >
            🗓️ Today's Batch
          </button>
          <button
            type="button"
            className={`tab-toggle-btn ${activeSubTab === 'bank' ? 'active' : ''}`}
            onClick={() => { setActiveSubTab('bank'); setQuestions([]); }}
            style={{
              padding: '0.45rem 1rem',
              fontSize: '0.85rem',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              background: activeSubTab === 'bank' ? 'var(--accent)' : 'transparent',
              color: activeSubTab === 'bank' ? '#fff' : 'var(--text-muted)',
              fontWeight: '500',
              transition: 'all 0.2s ease'
            }}
          >
            📂 Question Bank
          </button>
        </div>
      </div>

      {error && <div className="banner banner--error" style={{ marginBottom: '1rem' }}>{error}</div>}

      {/* Filter panel for Question Bank */}
      {activeSubTab === 'bank' && (
        <div className="bank-filters-panel" style={{
          display: 'flex',
          gap: '1rem',
          flexWrap: 'wrap',
          background: 'rgba(255,255,255,0.02)',
          padding: '1rem',
          borderRadius: '16px',
          border: '1px solid var(--line)',
          marginBottom: '1.5rem'
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', flex: '1 1 200px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '500' }}>Category</label>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              style={{
                background: 'rgba(255,255,255,0.04)',
                color: 'var(--text)',
                border: '1px solid var(--line)',
                borderRadius: '8px',
                padding: '0.45rem',
                outline: 'none'
              }}
            >
              <option value="">All Categories</option>
              {Object.entries(CATEGORY_LABELS).map(([key, item]) => (
                <option key={key} value={key}>{item.label}</option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', flex: '1 1 200px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '500' }}>Difficulty</label>
            <select
              value={filterDifficulty}
              onChange={(e) => setFilterDifficulty(e.target.value)}
              style={{
                background: 'rgba(255,255,255,0.04)',
                color: 'var(--text)',
                border: '1px solid var(--line)',
                borderRadius: '8px',
                padding: '0.45rem',
                outline: 'none'
              }}
            >
              <option value="">All Difficulties</option>
              {Object.entries(DIFFICULTY_LABELS).map(([key, item]) => (
                <option key={key} value={key}>{item.label}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {loading ? (
        <div className="loading-state" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          🔄 Loading questions...
        </div>
      ) : questions.length === 0 ? (
        <div className="empty-state-card" style={{
          textAlign: 'center',
          padding: '4rem 2rem',
          background: 'rgba(255,255,255,0.01)',
          border: '1px dashed var(--line)',
          borderRadius: '20px'
        }}>
          <span style={{ fontSize: '3rem' }}>💡</span>
          <h3 style={{ margin: '1rem 0 0.5rem 0', fontSize: '1.25rem' }}>No questions found</h3>
          <p className="muted" style={{ maxWidth: '400px', margin: '0 auto 1.5rem auto' }}>
            {activeSubTab === 'today'
              ? "Today's daily batch hasn't been generated yet or Celery beat schedule is pending. Try looking in the Question Bank!"
              : 'No questions match the current filters.'}
          </p>
          {activeSubTab === 'today' && (
            <button
              type="button"
              className="secondary-button"
              onClick={() => setActiveSubTab('bank')}
              style={{ padding: '0.5rem 1.5rem', borderRadius: '12px' }}
            >
              Browse Question Bank
            </button>
          )}
        </div>
      ) : (
        <div className="questions-grid" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {questions.map((q, idx) => {
            const cat = CATEGORY_LABELS[q.category] || { label: q.category, color: 'neutral' };
            const diff = DIFFICULTY_LABELS[q.difficulty] || { label: q.difficulty, color: 'neutral' };
            const isRevealed = revealedIds.has(q.id);
            const sources = parseSources(q.source_context);

            return (
              <div key={q.id} className="question-card" style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--line)',
                borderRadius: '20px',
                padding: '1.5rem',
                transition: 'all 0.3s ease',
                position: 'relative',
                boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
              }}>
                {/* Header row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <span style={{
                      padding: '0.25rem 0.65rem',
                      borderRadius: '8px',
                      fontSize: '0.75rem',
                      fontWeight: 'bold',
                      background: `var(--accent-glow)`,
                      color: `var(--accent)`,
                      border: `1px solid var(--accent)`
                    }}>
                      Question #{idx + 1}
                    </span>
                    <span className={`tag tag--${diff.color}`} style={{ fontSize: '0.75rem', fontWeight: 'bold' }}>
                      {diff.label}
                    </span>
                    <span style={{
                      padding: '0.25rem 0.65rem',
                      borderRadius: '8px',
                      fontSize: '0.75rem',
                      fontWeight: '500',
                      background: 'rgba(255,255,255,0.05)',
                      color: 'var(--text)',
                      border: '1px solid var(--line)'
                    }}>
                      🏷️ {cat.label}
                    </span>
                  </div>
                  
                  {q.company_style && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      🏢 {q.company_style} Style
                    </span>
                  )}
                </div>

                {/* Question text */}
                <h3 style={{ fontSize: '1.15rem', color: 'var(--text)', margin: '0 0 1.25rem 0', lineHeight: '1.5', fontWeight: '600' }}>
                  {q.question}
                </h3>

                {/* Sourced Websites */}
                {sources.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '-0.75rem', marginBottom: '1.25rem', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>📍 Sourced from:</span>
                    {sources.map((src, srcIdx) => (
                      src.url ? (
                        <a
                          key={srcIdx}
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            fontSize: '0.75rem',
                            padding: '0.15rem 0.5rem',
                            borderRadius: '6px',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--line)',
                            color: 'var(--accent)',
                            textDecoration: 'none',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.2rem',
                            transition: 'all 0.2s ease'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
                            e.currentTarget.style.borderColor = 'var(--accent)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                            e.currentTarget.style.borderColor = 'var(--line)';
                          }}
                          title={src.title}
                        >
                          🌐 {src.domain}
                        </a>
                      ) : (
                        <span
                          key={srcIdx}
                          style={{
                            fontSize: '0.75rem',
                            padding: '0.15rem 0.5rem',
                            borderRadius: '6px',
                            background: 'rgba(255,255,255,0.03)',
                            border: '1px dashed var(--line)',
                            color: 'var(--text-muted)'
                          }}
                        >
                          📦 {src.title}
                        </span>
                      )
                    ))}
                  </div>
                )}

                {/* Show/Hide answer actions */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', paddingTop: '0.5rem' }}>
                  <button
                    type="button"
                    className={isRevealed ? 'secondary-button' : 'primary-button'}
                    onClick={() => toggleReveal(q.id)}
                    style={{ padding: '0.5rem 1.25rem', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                  >
                    <span>{isRevealed ? '👁️‍🗨️ Hide Answer' : '🔑 Reveal Answer'}</span>
                  </button>

                  {/* Rating control */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {q.user_rating ? 'Your Rating:' : 'Rate this question:'}
                    </span>
                    <div style={{ display: 'flex', gap: '0.2rem' }}>
                      {[1, 2, 3, 4, 5].map((star) => {
                        const isFilled = q.user_rating && star <= q.user_rating;
                        return (
                          <button
                            key={star}
                            disabled={submittingRating[q.id]}
                            onClick={() => handleRate(q.id, star)}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: submittingRating[q.id] ? 'not-allowed' : 'pointer',
                              padding: 0,
                              fontSize: '1.2rem',
                              color: isFilled ? '#FFD700' : 'rgba(255,255,255,0.2)',
                              transition: 'color 0.2s ease',
                              textShadow: isFilled ? '0 0 8px rgba(255, 215, 0, 0.4)' : 'none'
                            }}
                            title={`Rate ${star} Stars`}
                          >
                            ★
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Revealed Content Section */}
                {isRevealed && (
                  <div className="revealed-answer-block" style={{
                    marginTop: '1.5rem',
                    background: 'rgba(0, 0, 0, 0.15)',
                    padding: '1.25rem',
                    borderRadius: '16px',
                    border: '1px solid var(--line)',
                    animation: 'fadeIn 0.3s ease'
                  }}>
                    <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.95rem', color: 'var(--accent)', fontWeight: 'bold' }}>
                      💡 Model Answer:
                    </h4>
                    
                    {/* Render model answer lines formatted */}
                    <div style={{
                      whiteSpace: 'pre-wrap',
                      lineHeight: '1.6',
                      color: 'var(--text)',
                      fontSize: '0.95rem',
                      fontFamily: 'system-ui, -apple-system, sans-serif'
                    }}>
                      {q.model_answer}
                    </div>

                    {q.follow_up_questions && q.follow_up_questions.length > 0 && (
                      <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>
                          💬 Follow-up Questions:
                        </h4>
                        <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          {q.follow_up_questions.map((fq, fidx) => (
                            <li key={fidx} style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: '1.4' }}>
                              {fq}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
