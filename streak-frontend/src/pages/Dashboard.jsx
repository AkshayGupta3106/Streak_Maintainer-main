import { useEffect, useState } from 'react';

import { getTodayLog, updateTodayLog } from '../api/logs';
import { getTasks } from '../api/tasks';
import HistoryModal from '../components/HistoryModal';
import ManageTasksModal from '../components/ManageTasksModal';
import TaskItem from '../components/TaskItem';
import { useAuth } from '../context/AuthContext';

const QUOTES = [
  'Small wins compound into strong streaks.',
  'Consistency beats intensity when the goal is lasting change.',
  'Do the easy part today so tomorrow is lighter.',
  'Momentum is built one checked box at a time.',
  'Your future self reads the log you write today.',
  'Progress loves repetition.',
  'One honest day is better than a perfect plan you never start.',
  'Streaks turn intention into identity.',
  'Track the habit, then let the habit carry you.',
  'A clean checklist is a quiet kind of momentum.',
];

function formatToday() {
  return new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [completedTaskIds, setCompletedTaskIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const [quote] = useState(() => QUOTES[Math.floor(Math.random() * QUOTES.length)]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const [taskData, logData] = await Promise.all([getTasks(), getTodayLog()]);
        if (!cancelled) {
          setTasks(taskData);
          setCompletedTaskIds(logData.completed_task_ids || []);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError('Failed to load dashboard.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (loading) {
      return undefined;
    }

    const timer = window.setTimeout(async () => {
      setSaving(true);
      setError('');
      try {
        await updateTodayLog(completedTaskIds);
      } catch (requestError) {
        setError('Failed to save, try again.');
      } finally {
        setSaving(false);
      }
    }, 500);

    return () => window.clearTimeout(timer);
  }, [completedTaskIds, loading]);

  const activeTasks = tasks.filter((task) => task.is_active !== false);
  const completedVisibleCount = activeTasks.filter((task) => completedTaskIds.includes(task.id)).length;
  const completionPercentage = activeTasks.length ? Math.round((completedVisibleCount / activeTasks.length) * 100) : 0;

  const toggleTask = (taskId, checked) => {
    setCompletedTaskIds((current) => {
      const next = new Set(current);
      if (checked) {
        next.add(taskId);
      } else {
        next.delete(taskId);
      }
      return Array.from(next);
    });
  };

  return (
    <div className="dashboard-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Good to see you</p>
          <h1>{user?.username || 'Your streak dashboard'}</h1>
          <p className="hero-panel__date">{formatToday()}</p>
        </div>
        <div className="hero-actions">
          <button type="button" className="secondary-button" onClick={() => setHistoryOpen(true)}>
            History
          </button>
          <button type="button" className="secondary-button" onClick={() => setManageOpen(true)}>
            Manage Tasks
          </button>
          <button type="button" className="ghost-button" onClick={logout}>
            Logout
          </button>
        </div>
      </section>

      <section className="quote-panel">
        <span className="quote-panel__label">Motivation</span>
        <p>{quote}</p>
      </section>

      <section className="progress-panel">
        <div className="progress-panel__header">
          <strong>Today</strong>
          <span>{completionPercentage}%</span>
        </div>
        <div className="progress-bar">
          <div className="progress-bar__fill" style={{ width: `${completionPercentage}%` }} />
        </div>
        <p className="muted">
          {completedVisibleCount} of {activeTasks.length} tasks complete
        </p>
      </section>

      {error ? <div className="banner banner--error">{error}</div> : null}
      {saving ? <div className="banner">Saving streak data...</div> : null}

      <section className="task-panel">
        <div className="task-panel__header">
          <div>
            <p className="eyebrow">Today's tasks</p>
            <h2>Your checklist</h2>
          </div>
        </div>

        {loading ? <div className="loading-state">Loading dashboard...</div> : null}

        {!loading && activeTasks.length === 0 ? (
          <div className="empty-state">Add your first streak to get started!</div>
        ) : null}

        <div className="task-list">
          {activeTasks.map((task) => (
            <TaskItem key={task.id} task={task} checked={completedTaskIds.includes(task.id)} onToggle={toggleTask} />
          ))}
        </div>
      </section>

      <HistoryModal open={historyOpen} onClose={() => setHistoryOpen(false)} />
      <ManageTasksModal
        open={manageOpen}
        tasks={tasks}
        onClose={() => setManageOpen(false)}
        onTasksChanged={(nextTasks) => setTasks(nextTasks)}
      />
    </div>
  );
}