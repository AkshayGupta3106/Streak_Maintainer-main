import React, { useState, useEffect } from 'react';
import { getHiringAnalytics } from '../api/hiring';

export default function HiringAnalytics() {
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const data = await getHiringAnalytics();
        setAnalyticsData(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) {
    return <div className="loading-container">Loading Analytics Charts...</div>;
  }

  if (!analyticsData) {
    return <div className="error-panel">No analytics data available.</div>;
  }

  const totals = analyticsData.totals || {};
  const byType = analyticsData.by_type || {};
  const byCompanyType = analyticsData.by_company_type || {};
  const byMonth = analyticsData.by_month || [];

  // Helper to compute max values for percentage calculations
  const maxTypeCount = Math.max(...Object.values(byType), 1);
  const maxCompanyTypeCount = Math.max(...Object.values(byCompanyType), 1);

  return (
    <div className="hiring-analytics-view">
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.8rem', fontWeight: 800 }}>Placements Analytics & Insights</h2>
        <p style={{ margin: '0.25rem 0 0 0', color: 'var(--muted)', fontSize: '0.9rem' }}>Quantitative distribution of off-campus hiring windows and types.</p>
      </div>

      {/* Stats Counters Grid */}
      <div className="analytics-totals-grid">
        <div className="analytics-stat-card">
          <div className="analytics-stat-num">{totals.active}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>🔥 Active Now</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-num">{totals.upcoming}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>⏳ Upcoming Drives</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-num">{totals.this_month}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>📅 Opening This Month</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-num">{totals.total}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase' }}>📂 Total Tracked</div>
        </div>
      </div>

      <div className="analytics-charts-grid">
        {/* Opportunity Type Breakdown */}
        <div className="analytics-chart-panel">
          <h3>Opportunities by Type</h3>
          {Object.keys(byType).length === 0 ? (
            <div style={{ fontSize: '0.85rem', color: 'var(--muted)', padding: '1rem' }}>No data to display.</div>
          ) : (
            Object.entries(byType).map(([typeKey, count]) => {
              const pct = (count / maxTypeCount) * 100;
              return (
                <div key={typeKey} className="analytics-bar-row">
                  <div className="analytics-bar-label">{typeKey.replace('_', ' ')}</div>
                  <div className="analytics-bar-track">
                    <div className="analytics-bar-fill" style={{ width: `${pct}%`, background: 'var(--accent)' }}></div>
                  </div>
                  <div className="analytics-bar-val">{count}</div>
                </div>
              );
            })
          )}
        </div>

        {/* Company Type / Sector Breakdown */}
        <div className="analytics-chart-panel">
          <h3>Company Sectors</h3>
          {Object.keys(byCompanyType).length === 0 ? (
            <div style={{ fontSize: '0.85rem', color: 'var(--muted)', padding: '1rem' }}>No data to display.</div>
          ) : (
            Object.entries(byCompanyType).map(([compType, count]) => {
              const pct = (count / maxCompanyTypeCount) * 100;
              return (
                <div key={compType} className="analytics-bar-row">
                  <div className="analytics-bar-label">{compType.replace('_', ' ')}</div>
                  <div className="analytics-bar-track">
                    <div className="analytics-bar-fill" style={{ width: `${pct}%`, background: '#3b82f6' }}></div>
                  </div>
                  <div className="analytics-bar-val">{count}</div>
                </div>
              );
            })
          )}
        </div>

        {/* Monthly Distribution Roadmap */}
        <div className="analytics-chart-panel" style={{ gridColumn: '1 / -1' }}>
          <h3>Hiring Season Monthly Timeline (Next 6 Months)</h3>
          {byMonth.length === 0 ? (
            <div style={{ fontSize: '0.85rem', color: 'var(--muted)', padding: '1rem' }}>No upcoming windows scheduled in the next 6 months.</div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
              {byMonth.map((m) => (
                <div key={m.month} style={{ textAlign: 'center', padding: '1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)', borderRadius: '12px' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent)' }}>{m.count}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.2rem' }}>
                    {new Date(m.month + '-01').toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
