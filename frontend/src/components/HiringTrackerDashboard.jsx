import React, { useState, useEffect } from 'react';
import {
  getHiringDashboard,
  triggerScrape,
  getCompanies,
  createOpportunity,
  updateOpportunity,
  deleteOpportunity
} from '../api/hiring';

const SCRAPER_SOURCES = [
  'internshala',
  'unstop_search',
  'superset_search',
  'cutshort_search',
  'instahyre_search',
  'hirist_search',
  'naukri_search',
  'foundit_search',
  'aicte_internship_portal_search',
  'analytics_vidhya_jobs_search',
  'nvidia_india_careers_search',
  'microsoft_india_careers_search',
  'google_careers_search',
  'atlassian_careers_search',
  'oracle_careers_search',
  'adobe_careers_search',
  'samsung_research_india_careers_search',
  'flipkart_careers_search',
  'phonepe_careers_search'
];

export default function HiringTrackerDashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [scrapeStartedAt, setScrapeStartedAt] = useState(null);
  const [scrapeElapsedSeconds, setScrapeElapsedSeconds] = useState(0);
  const [scrapeLastDurationSeconds, setScrapeLastDurationSeconds] = useState(0);
  const [scrapeMessage, setScrapeMessage] = useState('');
  const [scrapeResult, setScrapeResult] = useState(null);
  const [error, setError] = useState(null);

  // Form State
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    company: '',
    role: '',
    opportunity_type: 'FULL_TIME',
    expected_registration_start: '',
    expected_registration_end: '',
    expected_hiring_window_start: '',
    expected_hiring_window_end: '',
    career_portal_link: '',
    notes: '',
    priority_level: 2, // Medium
    status: 'UPCOMING',
    source: 'MANUAL',
    is_date_confirmed: true
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [dash, comps] = await Promise.all([
        getHiringDashboard(),
        getCompanies()
      ]);
      setDashboardData(dash);
      setCompanies(comps.results || comps);
      setError(null);
    } catch (err) {
      console.error(err);
      const status = err?.response?.status;
      const errorCode = err?.code;

      if (status === 401) {
        setError('Session expired. Please log in again.');
      } else if (status === 403) {
        setError('You do not have permission to view this data.');
      } else if (!status || errorCode === 'ERR_NETWORK') {
        setError('Cannot connect to backend API. Start backend server at http://127.0.0.1:8000 and retry.');
      } else {
        setError(`Failed to fetch opportunity data (HTTP ${status}). Please retry.`);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (!scraping || !scrapeStartedAt) return undefined;

    const tick = () => {
      const diffMs = Date.now() - scrapeStartedAt;
      setScrapeElapsedSeconds(Math.max(0, Math.floor(diffMs / 1000)));
    };

    tick();
    const timerId = window.setInterval(tick, 1000);
    return () => window.clearInterval(timerId);
  }, [scraping, scrapeStartedAt]);

  const formatElapsed = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, '0')}`;
  };

  const handleScrape = async () => {
    const runStartedAt = Date.now();
    const combinedResults = {};
    try {
      setScraping(true);
      setScrapeStartedAt(runStartedAt);
      setScrapeElapsedSeconds(0);
      setScrapeMessage('Starting scrapers and syncing opportunities...');
      setScrapeResult(null);

      for (let i = 0; i < SCRAPER_SOURCES.length; i += 1) {
        const source = SCRAPER_SOURCES[i];
        setScrapeMessage(`Running source ${i + 1}/${SCRAPER_SOURCES.length}: ${source}`);

        try {
          const res = await triggerScrape([source]);
          const sourceResult = res?.results?.[source] || {
            status: 'ok',
            seen: 0,
            created: 0,
            updated: 0
          };
          combinedResults[source] = sourceResult;
        } catch (sourceErr) {
          combinedResults[source] = {
            status: 'error',
            error: sourceErr?.response?.data?.error || sourceErr?.message || 'Request failed',
          };
        }

        setScrapeResult({ ...combinedResults });
        await fetchData();
      }

      setScrapeMessage('Scrape finished. Refreshing dashboard buckets...');
      await fetchData();
      setScrapeMessage('Scrape completed successfully.');
    } catch (err) {
      console.error(err);
      setScrapeMessage('Scrape failed. Please try again.');
      alert('Scraper failed to run.');
    } finally {
      setScraping(false);
      setScrapeLastDurationSeconds(Math.max(0, Math.floor((Date.now() - runStartedAt) / 1000)));
      setScrapeStartedAt(null);
      setScrapeElapsedSeconds(0);
    }
  };

  const handleStatusChange = async (oppId, newStatus) => {
    try {
      await updateOpportunity(oppId, { status: newStatus });
      await fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to update status.');
    }
  };

  const handleDelete = async (oppId) => {
    if (!window.confirm('Are you sure you want to delete this opportunity?')) return;
    try {
      await deleteOpportunity(oppId);
      await fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to delete opportunity.');
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!formData.company || !formData.role || !formData.expected_hiring_window_start || !formData.expected_hiring_window_end) {
      alert('Please fill out all required fields (Company, Role, Hiring Window Start & End)');
      return;
    }
    try {
      await createOpportunity(formData);
      setShowAddForm(false);
      // Reset Form
      setFormData({
        company: '',
        role: '',
        opportunity_type: 'FULL_TIME',
        expected_registration_start: '',
        expected_registration_end: '',
        expected_hiring_window_start: '',
        expected_hiring_window_end: '',
        career_portal_link: '',
        notes: '',
        priority_level: 2,
        status: 'UPCOMING',
        source: 'MANUAL',
        is_date_confirmed: true
      });
      await fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to save opportunity. Verify fields are valid.');
    }
  };

  if (loading && !dashboardData) {
    return <div className="loading-container">Loading Hiring Dashboard...</div>;
  }

  if (error) {
    return <div className="error-panel">{error}</div>;
  }

  const columns = [
    { key: 'apply_now', label: '🔴 Apply Now', color: 'red', list: dashboardData?.apply_now || [] },
    { key: 'coming_soon', label: '🟡 Coming Soon', color: 'yellow', list: dashboardData?.coming_soon || [] },
    { key: 'prepare_now', label: '🟢 Prepare Now', color: 'green', list: dashboardData?.prepare_now || [] },
    { key: 'long_term', label: '🔵 Long Term', color: 'blue', list: dashboardData?.long_term || [] },
    { key: 'missed', label: '⚪ Closed / Missed', color: 'grey', list: dashboardData?.missed || [] }
  ];

  const counts = dashboardData?.meta?.counts || {};

  return (
    <div className="hiring-dashboard-view">
      <div className="dashboard-shell-header" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.8rem', fontWeight: 800 }}>Off-Campus Placements & Internships</h2>
          <p style={{ margin: '0.25rem 0 0 0', color: 'var(--muted)', fontSize: '0.9rem' }}>Track recruiter hiring cycles, upcoming drives, and auto-scrape openings.</p>
        </div>
        <button
          className="add-task-btn"
          onClick={() => setShowAddForm(!showAddForm)}
          style={{ padding: '0.6rem 1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderRadius: '12px' }}
        >
          {showAddForm ? '✕ Close Form' : '＋ Add Opportunity'}
        </button>
      </div>

      {/* Manual Opportunity Form */}
      {showAddForm && (
        <form className="journal-editor-sheet" onSubmit={handleFormSubmit} style={{ margin: '1.5rem 0', padding: '1.5rem', border: '1px solid var(--line)', borderRadius: '20px', background: 'rgba(255,255,255,0.01)', display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
          <h3 style={{ gridColumn: '1 / -1', margin: '0 0 0.5rem 0', fontSize: '1.1rem' }}>Manually Track Placement / Internship Drive</h3>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Recruiter/Company *</label>
            <select
              value={formData.company}
              onChange={(e) => setFormData({ ...formData, company: e.target.value })}
              className="journal-font-select"
              style={{ width: '100%', padding: '0.5rem' }}
              required
            >
              <option value="">-- Select Company --</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Role/Profile Title *</label>
            <input
              type="text"
              placeholder="e.g. SDE Intern, Fresher Analyst"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="subtask-add-input"
              style={{ width: '100%', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--line)', color: 'var(--text)', padding: '0.5rem', borderRadius: '8px' }}
              required
            />
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Opportunity Type</label>
            <select
              value={formData.opportunity_type}
              onChange={(e) => setFormData({ ...formData, opportunity_type: e.target.value })}
              className="journal-font-select"
              style={{ width: '100%', padding: '0.5rem' }}
            >
              <option value="FULL_TIME">Full-Time Job</option>
              <option value="INTERNSHIP">Internship</option>
              <option value="HACKATHON">Hackathon</option>
              <option value="OA">Online Assessment (OA)</option>
              <option value="GRAD_PROGRAM">Graduate Program</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Priority Level</label>
            <select
              value={formData.priority_level}
              onChange={(e) => setFormData({ ...formData, priority_level: parseInt(e.target.value) })}
              className="journal-font-select"
              style={{ width: '100%', padding: '0.5rem' }}
            >
              <option value="1">Low</option>
              <option value="2">Medium</option>
              <option value="3">High</option>
              <option value="4">Critical</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Registration Start</label>
            <input
              type="date"
              value={formData.expected_registration_start}
              onChange={(e) => setFormData({ ...formData, expected_registration_start: e.target.value })}
              className="subtask-add-input"
              style={{ width: '100%', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--line)', color: 'var(--text)', padding: '0.5rem', borderRadius: '8px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Registration End</label>
            <input
              type="date"
              value={formData.expected_registration_end}
              onChange={(e) => setFormData({ ...formData, expected_registration_end: e.target.value })}
              className="subtask-add-input"
              style={{ width: '100%', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--line)', color: 'var(--text)', padding: '0.5rem', borderRadius: '8px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Hiring Window Start *</label>
            <input
              type="date"
              value={formData.expected_hiring_window_start}
              onChange={(e) => setFormData({ ...formData, expected_hiring_window_start: e.target.value })}
              className="subtask-add-input"
              style={{ width: '100%', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--line)', color: 'var(--text)', padding: '0.5rem', borderRadius: '8px' }}
              required
            />
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Hiring Window End *</label>
            <input
              type="date"
              value={formData.expected_hiring_window_end}
              onChange={(e) => setFormData({ ...formData, expected_hiring_window_end: e.target.value })}
              className="subtask-add-input"
              style={{ width: '100%', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--line)', color: 'var(--text)', padding: '0.5rem', borderRadius: '8px' }}
              required
            />
          </div>

          <div style={{ gridColumn: '1 / -1' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Career Portal / Apply Link</label>
            <input
              type="url"
              placeholder="https://jobs.company.com/..."
              value={formData.career_portal_link}
              onChange={(e) => setFormData({ ...formData, career_portal_link: e.target.value })}
              className="subtask-add-input"
              style={{ width: '100%', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--line)', color: 'var(--text)', padding: '0.5rem', borderRadius: '8px' }}
            />
          </div>

          <div style={{ gridColumn: '1 / -1' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: '0.35rem' }}>Notes & Preparation details</label>
            <textarea
              placeholder="Add dynamic notes, interview topics, tips..."
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="journal-textarea"
              style={{ width: '100%', height: '60px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--line)', color: 'var(--text)', padding: '0.5rem', borderRadius: '8px' }}
            />
          </div>

          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button type="button" onClick={() => setShowAddForm(false)} className="mood-btn" style={{ padding: '0.5rem 1rem' }}>Cancel</button>
            <button type="submit" className="save-btn" style={{ padding: '0.5rem 1.5rem', borderRadius: '8px' }}>Save Opportunity</button>
          </div>
        </form>
      )}

      {/* Scraper Panel */}
      <div className="hiring-scraper-panel" style={{ marginBottom: '2rem' }}>
        <div className="scraper-info-left">
          <div className="scraper-icon-wrap">🤖</div>
          <div>
            <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>Scrape & Sync Engine</h4>
            <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.8rem', color: 'var(--muted)' }}>
              Pulls roles from all configured portals and company career pages. This may take a minute due retry/backoff.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {scraping ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', minWidth: '280px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                <span className="saving-indicator" style={{ display: 'inline-block' }}></span>
                <span>Running scrapers... elapsed {formatElapsed(scrapeElapsedSeconds)}</span>
              </div>
              <div style={{ height: '6px', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${20 + (scrapeElapsedSeconds % 6) * 12}%`,
                    height: '100%',
                    borderRadius: '999px',
                    background: 'linear-gradient(90deg, #10b981, #34d399)',
                    transition: 'width 0.7s ease',
                  }}
                />
              </div>
              <span style={{ fontSize: '0.76rem', color: 'var(--muted)' }}>{scrapeMessage || 'Querying sources and deduplicating results...'}</span>
            </div>
          ) : (
            <button className="opp-portal-btn" onClick={handleScrape} style={{ background: '#10b981', color: '#09150b' }} disabled={scraping}>
              ⚡ Trigger Auto-Scrapers
            </button>
          )}
        </div>

        {scrapeResult && (
          <div style={{ width: '100%', marginTop: '0.75rem', padding: '0.75rem 1rem', background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '10px', fontSize: '0.85rem' }}>
            <strong>Scrape Complete:</strong>
            <div style={{ marginTop: '0.2rem', color: 'var(--muted)', fontSize: '0.78rem' }}>Elapsed: {formatElapsed(scrapeLastDurationSeconds)}</div>
            {Object.entries(scrapeResult).map(([source, details]) => (
              <div key={source} style={{ marginTop: '0.2rem' }}>
                • <strong>{source}</strong>: {details.status === 'ok' ? `Processed ${details.seen} listings (created ${details.created}, updated ${details.updated})` : `Failed (${details.error})`}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Kanban Buckets columns */}
      <div className="hiring-buckets-grid">
        {columns.map((col) => (
          <div key={col.key} className="hiring-bucket-column">
            <div className="hiring-bucket-header">
              <h3>
                <span>{col.label}</span>
              </h3>
              <span className="hiring-bucket-count">{col.list.length}</span>
            </div>

            {col.list.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--muted)', fontSize: '0.8rem', margin: 'auto 0', padding: '2rem 0' }}>
                No listings in this bucket.
              </div>
            ) : (
              col.list.map((opp) => (
                <div key={opp.id} className={`opp-card border-${col.color}`}>
                  <div className="opp-card-header">
                    <div>
                      <div className="opp-company-info">
                        <div className="opp-company-logo">
                          {opp.logo_url ? <img src={opp.logo_url} alt={opp.company_name} style={{ width: '100%', height: '100%', borderRadius: '8px' }} /> : opp.company_name.substring(0, 1)}
                        </div>
                        <h4 className="opp-company-name">{opp.company_name}</h4>
                      </div>
                      <p className="opp-role">{opp.role}</p>
                    </div>
                    <button
                      className="opp-delete-btn"
                      onClick={() => handleDelete(opp.id)}
                      title="Delete opportunity"
                    >
                      ✕
                    </button>
                  </div>

                  <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                    <span className="opp-type-badge">{opp.opportunity_type.replace('_', ' ')}</span>
                    <span className={`opp-priority-badge prio-${opp.priority_level}`}>
                      {opp.priority_level === 4 ? 'Critical' : opp.priority_level === 3 ? 'High' : opp.priority_level === 2 ? 'Medium' : 'Low'}
                    </span>
                    {!opp.is_date_confirmed && (
                      <span style={{ fontSize: '0.65rem', background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', padding: '0.15rem 0.45rem', borderRadius: '6px', fontWeight: 'bold' }}>
                        Projected Date
                      </span>
                    )}
                  </div>

                  <div className="opp-dates-row">
                    <div>
                      <span>Opens:</span>
                      <strong>{opp.expected_hiring_window_start ? new Date(opp.expected_hiring_window_start).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : 'N/A'}</strong>
                    </div>
                    <div>
                      <span>Closes:</span>
                      <strong>{opp.expected_hiring_window_end ? new Date(opp.expected_hiring_window_end).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : 'N/A'}</strong>
                    </div>
                    {opp.days_until_hiring > 0 && (
                      <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', marginTop: '0.2rem', paddingTop: '0.2rem', color: '#10b981', fontWeight: 600 }}>
                        <span>Countdown:</span>
                        <span>{opp.days_until_hiring} days left</span>
                      </div>
                    )}
                  </div>

                  {opp.notes && (
                    <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--muted)', background: 'rgba(255,255,255,0.02)', padding: '0.4rem 0.6rem', borderRadius: '8px', border: '1px solid var(--line)', whiteSpace: 'pre-wrap' }}>
                      {opp.notes}
                    </p>
                  )}

                  <div className="opp-footer">
                    <select
                      className="opp-status-select"
                      value={opp.status}
                      onChange={(e) => handleStatusChange(opp.id, e.target.value)}
                    >
                      <option value="UPCOMING">Upcoming</option>
                      <option value="REGISTRATION_OPEN">Reg Open</option>
                      <option value="APPLY_NOW">Apply Now</option>
                      <option value="OA_EXPECTED">OA Stage</option>
                      <option value="INTERVIEW_PHASE">Interviews</option>
                      <option value="CLOSED">Closed</option>
                      <option value="MISSED">Missed</option>
                    </select>

                    {opp.career_portal_link && (
                      <a
                        href={opp.career_portal_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="opp-portal-btn"
                      >
                        Apply →
                      </a>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
