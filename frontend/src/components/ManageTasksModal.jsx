import { useEffect, useMemo, useState } from 'react';

import { createTask, deleteTask, getTasks, updateTask } from '../api/tasks';
import ModalShell from './ModalShell';

export default function ManageTasksModal({ open, tasks, onClose, onTasksChanged }) {
  const [taskName, setTaskName] = useState('');
  const [taskOrder, setTaskOrder] = useState(1);
  const [taskPriority, setTaskPriority] = useState('medium');
  const [taskIsRecurring, setTaskIsRecurring] = useState(false);
  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [error, setError] = useState('');
  const [showOptions, setShowOptions] = useState(false);

  useEffect(() => {
    setTaskOrder((tasks || []).length + 1);
  }, [tasks]);

  const sortedTasks = useMemo(
    () => [...(tasks || [])].sort((left, right) => left.order - right.order),
    [tasks],
  );

  if (!open) {
    return null;
  }

  const refresh = async () => {
    const nextTasks = await getTasks();
    onTasksChanged?.(nextTasks);
  };

  const handleCreate = async (event) => {
    event.preventDefault();

    if (!taskName.trim()) {
      return;
    }

    try {
      setError('');
      await createTask({ 
        name: taskName.trim(), 
        order: Number(taskOrder) || 0,
        priority: taskPriority,
        is_recurring: taskIsRecurring
      });
      setTaskName('');
      setTaskPriority('medium');
      setTaskIsRecurring(false);
      setShowOptions(false);
      await refresh();
    } catch {
      setError('Failed to save, try again');
    }
  };

  const handleEdit = (task) => {
    setEditingTaskId(task.id);
    setEditingName(task.name);
  };

  const handleSaveEdit = async (taskId) => {
    if (!editingName.trim()) {
      return;
    }

    try {
      setError('');
      await updateTask(taskId, { name: editingName.trim() });
      setEditingTaskId(null);
      setEditingName('');
      await refresh();
    } catch {
      setError('Failed to save, try again');
    }
  };

  const handleDelete = async (taskId) => {
    try {
      setError('');
      await deleteTask(taskId);
      await refresh();
    } catch {
      setError('Failed to save, try again');
    }
  };

  return (
    <ModalShell title="Manage Tasks" onClose={onClose} narrow>
      {error ? <div className="banner banner-error">{error}</div> : null}

      <form className="stack-form" onSubmit={handleCreate}>
        <div className="form-row">
          <label style={{ width: '100%' }}>
            Task name
            <input value={taskName} onChange={(event) => setTaskName(event.target.value)} placeholder="e.g. Solve 3 LeetCode problems" />
          </label>
        </div>

        {taskName.trim().length > 0 && (
          <div className="task-options-trigger-container">
            <button 
              type="button" 
              className={`options-trigger-btn ${showOptions ? 'active' : ''}`}
              onClick={() => setShowOptions(prev => !prev)}
            >
              <span>⚙️ Set Priority & Recurring Options</span>
              <span className={`chevron-icon ${showOptions ? 'open' : ''}`}>▼</span>
            </button>
          </div>
        )}

        {taskName.trim().length > 0 && showOptions && (
          <div className="task-options-expanded-panel">
            <div className="option-group">
              <span className="option-label">Choose Priority</span>
              <div className="priority-picker-aesthetic">
                <button
                  type="button"
                  className={`priority-picker-btn high ${taskPriority === 'high' ? 'active' : ''}`}
                  onClick={() => setTaskPriority('high')}
                >
                  <span className="dot red"></span> High
                </button>
                <button
                  type="button"
                  className={`priority-picker-btn medium ${taskPriority === 'medium' ? 'active' : ''}`}
                  onClick={() => setTaskPriority('medium')}
                >
                  <span className="dot yellow"></span> Medium
                </button>
                <button
                  type="button"
                  className={`priority-picker-btn low ${taskPriority === 'low' ? 'active' : ''}`}
                  onClick={() => setTaskPriority('low')}
                >
                  <span className="dot green"></span> Low
                </button>
              </div>
            </div>

            <div className="option-group separator-top">
              <span className="option-label">Daily Recurrence</span>
              <div className="recurring-toggle-card">
                <label className="toggle-switch-label">
                  <div className="toggle-switch-wrapper">
                    <input
                      type="checkbox"
                      checked={taskIsRecurring}
                      onChange={(event) => setTaskIsRecurring(event.target.checked)}
                      className="toggle-switch-input"
                    />
                    <span className="toggle-switch-slider"></span>
                  </div>
                  <span className="toggle-switch-text">🔁 Repeat task everyday automatically</span>
                </label>
              </div>
            </div>
          </div>
        )}

        <button className="primary-button" type="submit" style={{ marginTop: '0.2rem' }}>
          Add task
        </button>
      </form>

      <div className="task-admin-list">
        {sortedTasks.map((task) => (
          <div key={task.id} className="task-admin-row">
            {editingTaskId === task.id ? (
              <input value={editingName} onChange={(event) => setEditingName(event.target.value)} />
            ) : (
              <div>
                <strong>{task.name}</strong>
                <p style={{ margin: '0.2rem 0 0 0', display: 'flex', gap: '0.45rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span className={`priority-badge priority-${task.priority || 'medium'}`} style={{ textTransform: 'capitalize' }}>
                    {task.priority || 'medium'}
                  </span>
                  {task.is_recurring && <span className="recurring-badge">🔁 Recurring</span>}
                  <span className="order-badge">Order {task.order}</span>
                </p>
              </div>
            )}

            <div className="task-admin-actions">
              {editingTaskId === task.id ? (
                <button className="secondary-button" type="button" onClick={() => handleSaveEdit(task.id)}>
                  Save
                </button>
              ) : (
                <button className="secondary-button" type="button" onClick={() => handleEdit(task)}>
                  Rename
                </button>
              )}
              <button className="ghost-button" type="button" onClick={() => handleDelete(task.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </ModalShell>
  );
}