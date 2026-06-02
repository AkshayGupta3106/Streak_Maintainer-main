import { useEffect, useMemo, useState } from 'react';

import { createTask, deleteTask, getTasks, updateTask } from '../api/tasks';
import ModalShell from './ModalShell';

export default function ManageTasksModal({ open, tasks, onClose, onChanged }) {
  const [taskName, setTaskName] = useState('');
  const [taskOrder, setTaskOrder] = useState(1);
  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [error, setError] = useState('');

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
    const { data } = await getTasks();
    onChanged?.(data);
  };

  const handleCreate = async (event) => {
    event.preventDefault();

    if (!taskName.trim()) {
      return;
    }

    try {
      setError('');
      await createTask({ name: taskName.trim(), order: Number(taskOrder) || 0 });
      setTaskName('');
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
    <ModalShell title="Manage Tasks" onClose={onClose} wide>
      {error ? <div className="banner banner-error">{error}</div> : null}

      <form className="stack-form" onSubmit={handleCreate}>
        <div className="form-row split">
          <label>
            Task name
            <input value={taskName} onChange={(event) => setTaskName(event.target.value)} placeholder="Drink water" />
          </label>
          <label>
            Order
            <input
              type="number"
              value={taskOrder}
              onChange={(event) => setTaskOrder(event.target.value)}
              min="0"
            />
          </label>
        </div>
        <button className="primary-button" type="submit">
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
                <p>Order {task.order}</p>
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