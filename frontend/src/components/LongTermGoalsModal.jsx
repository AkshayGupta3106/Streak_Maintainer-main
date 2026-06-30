import { useEffect, useState } from 'react';
import { getGoals, createGoal, updateGoal, deleteGoal } from '../api/goals';
import ModalShell from './ModalShell';

export default function LongTermGoalsModal({ open, onClose }) {
  const [goals, setGoals] = useState([]);
  const [newTitle, setNewTitle] = useState('');
  const [newTargetDate, setNewTargetDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadGoals = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getGoals();
      setGoals(data);
    } catch {
      setError('Failed to fetch goals');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadGoals();
    }
  }, [open]);

  if (!open) return null;

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!newTitle.trim()) return;

    try {
      setError('');
      await createGoal({
        title: newTitle.trim(),
        target_date: newTargetDate || null,
      });
      setNewTitle('');
      setNewTargetDate('');
      await loadGoals();
    } catch {
      setError('Failed to create goal');
    }
  };

  const handleToggle = async (goal) => {
    try {
      setError('');
      const updated = await updateGoal(goal.id, { is_completed: !goal.is_completed });
      setGoals(prev => prev.map(g => g.id === goal.id ? updated : g));
    } catch {
      setError('Failed to update goal');
    }
  };

  const handleDelete = async (goalId) => {
    try {
      setError('');
      await deleteGoal(goalId);
      setGoals(prev => prev.filter(g => g.id !== goalId));
    } catch {
      setError('Failed to delete goal');
    }
  };

  const formatGoalDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const completedCount = goals.filter(g => g.is_completed).length;
  const goalPercentage = goals.length ? Math.round((completedCount / goals.length) * 100) : 0;

  return (
    <ModalShell title="Long-Term Goals" onClose={onClose} wide>
      {error && <div className="banner banner-error">{error}</div>}

      <div className="goals-summary-panel" style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', padding: '1.15rem', background: 'rgba(255,255,255,0.03)', borderRadius: '14px', marginBottom: '1.25rem', border: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: '1.1rem' }}>Overall Goals Progress</strong>
          <p className="muted" style={{ fontSize: '0.85rem', margin: '0.2rem 0 0 0' }}>{completedCount} of {goals.length} goals achieved</p>
        </div>
        <div style={{ fontSize: '1.6rem', fontWeight: '700', color: 'var(--accent-primary)' }}>
          {goalPercentage}%
        </div>
      </div>

      <form className="stack-form" onSubmit={handleCreate} style={{ marginBottom: '1.5rem' }}>
        <div className="form-row split" style={{ gap: '1rem' }}>
          <label style={{ flex: 2 }}>
            Goal Description
            <input 
              value={newTitle} 
              onChange={e => setNewTitle(e.target.value)} 
              placeholder="e.g. Reach 1900 rating on LeetCode" 
              required
            />
          </label>
          <label style={{ flex: 1 }}>
            Target Date (Optional)
            <input 
              type="date"
              value={newTargetDate} 
              onChange={e => setNewTargetDate(e.target.value)} 
            />
          </label>
        </div>
        <button className="primary-button" type="submit" style={{ marginTop: '0.5rem', width: '100%' }}>
          Add Long-Term Goal
        </button>
      </form>

      {loading && goals.length === 0 ? (
        <div className="loading-state">Loading goals...</div>
      ) : goals.length === 0 ? (
        <div className="empty-state">No long-term goals set. Add one to dream big!</div>
      ) : (
        <div className="goals-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '350px', overflowY: 'auto', paddingRight: '0.25rem' }}>
          {goals.map((goal) => (
            <div 
              key={goal.id} 
              className={`goal-item-card ${goal.is_completed ? 'completed' : ''}`}
              style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between', 
                padding: '0.9rem 1.15rem', 
                background: goal.is_completed ? 'rgba(16,185,129,0.04)' : 'rgba(255,255,255,0.02)', 
                borderRadius: '12px', 
                border: goal.is_completed ? '1px solid rgba(16,185,129,0.15)' : '1px solid rgba(255,255,255,0.04)',
                transition: 'all 0.3s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem', flex: 1, marginRight: '1rem' }}>
                <input 
                  type="checkbox"
                  checked={goal.is_completed}
                  onChange={() => handleToggle(goal)}
                  style={{ width: '1.25rem', height: '1.25rem', cursor: 'pointer', accentColor: 'var(--accent-primary)' }}
                />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                  <span style={{ 
                    fontWeight: '600', 
                    fontSize: '0.95rem',
                    textDecoration: goal.is_completed ? 'line-through' : 'none', 
                    color: goal.is_completed ? 'var(--text-muted)' : 'var(--text-primary)',
                    transition: 'all 0.3s ease'
                  }}>
                    {goal.title}
                  </span>
                  {goal.target_date && (
                    <span className="muted" style={{ fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      📅 Target: {formatGoalDate(goal.target_date)}
                    </span>
                  )}
                </div>
              </div>
              <button 
                className="ghost-button" 
                type="button" 
                onClick={() => handleDelete(goal.id)}
                style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem', color: 'var(--status-error)' }}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </ModalShell>
  );
}
