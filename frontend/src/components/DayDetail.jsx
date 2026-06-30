import { useEffect, useMemo, useState } from 'react';
import { formatStreakDate } from '../utils/dateFormatter';
import { updateLogByDate } from '../api/logs';
import TaskItem from './TaskItem';

export default function DayDetail({ dateValue, log, onLogUpdated }) {
  const completedIds = useMemo(() => (log ? log.completed_task_ids || [] : []), [log]);
  const percentage = useMemo(() => (log ? (log.completion_percentage !== null && log.completion_percentage !== undefined ? log.completion_percentage : 0) : 0), [log]);

  const isToday = useMemo(() => {
    const todayStr = new Date().toISOString().slice(0, 10);
    return dateValue === todayStr;
  }, [dateValue]);

  const [note, setNote] = useState('');
  const [savingNote, setSavingNote] = useState(false);

  useEffect(() => {
    if (log) {
      setNote(log.journal_entry || '');
    }
  }, [log]);

  const codedTasks = useMemo(() => {
    if (!log || !log.tasks) return [];
    
    const PRIORITY_ORDER = { high: 1, medium: 2, low: 3 };
    const sorted = [...log.tasks].sort((left, right) => {
      const leftRank = PRIORITY_ORDER[left.priority] || 2;
      const rightRank = PRIORITY_ORDER[right.priority] || 2;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return left.id - right.id;
    });

    let highCount = 0;
    let mediumCount = 0;
    let lowCount = 0;

    return sorted.map(task => {
      let code = '';
      const prio = task.priority || 'medium';
      if (prio === 'high') {
        highCount++;
        code = `H${highCount}`;
      } else if (prio === 'medium') {
        mediumCount++;
        code = `M${mediumCount}`;
      } else {
        lowCount++;
        code = `L${lowCount}`;
      }
      return { ...task, displayCode: code };
    });
  }, [log]);

  if (!log) {
    return <p className="empty-copy">Pick a day to see its log.</p>;
  }

  const handleSaveNote = async () => {
    setSavingNote(true);
    try {
      await updateLogByDate(dateValue, completedIds, note, undefined);
      if (onLogUpdated) {
        await onLogUpdated();
      }
    } catch (err) {
      console.error("Failed to save daily note:", err);
    } finally {
      setSavingNote(false);
    }
  };

  return (
    <section className="detail-card">
      <div className="detail-card-header" style={{ marginBottom: '1.25rem' }}>
        <div>
          <p className="eyebrow">Selected Day</p>
          <h3>{formatStreakDate(dateValue)}</h3>
        </div>
        <span className="status-pill">
          {log.is_frozen ? '❄️ Frozen' : `${percentage}% complete`}
        </span>
      </div>

      {log.is_frozen && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(59, 130, 246, 0.12)', border: '1px solid rgba(59, 130, 246, 0.3)', color: '#60a5fa', padding: '0.65rem 1rem', borderRadius: '16px', marginBottom: '1.25rem', fontSize: '0.9rem', fontWeight: 'bold' }}>
          <span>❄️ This day was frozen. Streak preserved!</span>
        </div>
      )}

      <div className="task-list" style={{ marginBottom: '1.25rem' }}>
        <p className="eyebrow" style={{ marginBottom: '0.5rem' }}>Completed checklist</p>
        {codedTasks.length > 0 ? (
          codedTasks.map((task) => (
            <TaskItem key={task.id} task={task} checked={completedIds.includes(task.id)} readOnly />
          ))
        ) : (
          <p className="empty-copy" style={{ margin: 0 }}>No task found this day</p>
        )}
      </div>

      <div style={{ borderTop: '1px solid var(--line)', paddingTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="eyebrow">📝 Daily Note & reflections</span>
          {!isToday && <span style={{ fontSize: '0.75rem', color: '#94a3b8', background: 'rgba(255,255,255,0.06)', padding: '0.2rem 0.5rem', borderRadius: '6px' }}>🔒 Locked</span>}
        </div>
        <textarea
          value={note}
          onChange={(e) => isToday && setNote(e.target.value)}
          readOnly={!isToday}
          placeholder={isToday ? "What did you learn or code on this day?" : "(No entry was logged on this day)"}
          style={{
            width: '100%',
            minHeight: '80px',
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--line)',
            borderRadius: '12px',
            padding: '0.65rem 0.85rem',
            color: 'var(--text)',
            fontSize: '0.88rem',
            fontFamily: 'inherit',
            resize: 'vertical',
            outline: 'none',
          }}
        />
        {isToday && (
          <button
            type="button"
            className="primary-button"
            onClick={handleSaveNote}
            disabled={savingNote}
            style={{ padding: '0.55rem 1rem', fontSize: '0.85rem', borderRadius: '12px', width: 'fit-content', marginLeft: 'auto' }}
          >
            {savingNote ? 'Saving...' : 'Save reflections'}
          </button>
        )}
      </div>
    </section>
  );
}