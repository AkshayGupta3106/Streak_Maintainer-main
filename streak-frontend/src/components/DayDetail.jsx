import { useEffect, useState } from 'react';

import { updateLogByDate } from '../api/logs';
import TaskItem from './TaskItem';

export default function DayDetail({ dateValue, log, onLogUpdated }) {
  const [completedIds, setCompletedIds] = useState(log?.completed_task_ids || []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setCompletedIds(log?.completed_task_ids || []);
  }, [log?.id, log?.completed_task_ids]);

  useEffect(() => {
    if (!dateValue || !log) {
      return undefined;
    }

    const timer = window.setTimeout(async () => {
      try {
        setSaving(true);
        setError('');
        const updatedLog = await updateLogByDate(dateValue, completedIds);
        onLogUpdated?.(updatedLog);
      } catch {
        setError('Failed to save, try again');
      } finally {
        setSaving(false);
      }
    }, 500);

    return () => window.clearTimeout(timer);
  }, [completedIds, dateValue, log, onLogUpdated]);

  const toggleTask = (taskId) => {
    setCompletedIds((current) =>
      current.includes(taskId) ? current.filter((id) => id !== taskId) : [...current, taskId],
    );
  };

  if (!log) {
    return <p className="empty-copy">Pick a day to see its log.</p>;
  }

  return (
    <section className="detail-card">
      <div className="detail-card-header">
        <div>
          <p className="eyebrow">Selected Day</p>
          <h3>{dateValue}</h3>
        </div>
        <span className="status-pill">{saving ? 'Saving…' : `${log.completion_percentage}% complete`}</span>
      </div>
      {error ? <div className="banner banner-error">{error}</div> : null}
      <div className="task-list">
        {(log.tasks || []).map((task) => (
          <TaskItem key={task.id} task={task} checked={completedIds.includes(task.id)} onToggle={toggleTask} />
        ))}
      </div>
    </section>
  );
}