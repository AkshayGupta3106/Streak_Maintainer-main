import { useState } from 'react';

export default function TaskItem({ task, checked, onToggle, readOnly, dragHandleProps, onDelete, onUpdateSubtasks }) {
  const priority = task.priority || 'medium';
  const [newSubtaskText, setNewSubtaskText] = useState('');

  const handleAddSubtask = (e) => {
    e.preventDefault();
    if (!newSubtaskText.trim()) return;
    const newSub = {
      id: Date.now(), // Generate local unique ID
      name: newSubtaskText.trim(),
      is_completed: false
    };
    const nextSubtasks = [...(task.subtasks || []), newSub];
    onUpdateSubtasks?.(task.id, nextSubtasks);
    setNewSubtaskText('');
  };

  const handleToggleSubtask = (subId, isCompleted) => {
    const nextSubtasks = (task.subtasks || []).map(sub => 
      sub.id === subId ? { ...sub, is_completed: isCompleted } : sub
    );
    onUpdateSubtasks?.(task.id, nextSubtasks);
  };

  const handleDeleteSubtask = (subId) => {
    const nextSubtasks = (task.subtasks || []).filter(sub => sub.id !== subId);
    onUpdateSubtasks?.(task.id, nextSubtasks);
  };

  return (
    <div 
      className={`task-item ${checked ? 'task-item-checked' : ''} priority-border-${priority}`} 
      style={readOnly ? { cursor: 'default' } : undefined}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.9rem', flex: 1, cursor: readOnly ? 'default' : 'pointer', margin: 0 }}>
          <span className="task-item-check">
            <input
              type="checkbox"
              checked={checked}
              disabled={readOnly}
              onChange={(event) => !readOnly && onToggle?.(task.id, event.target.checked)}
            />
          </span>
          <span className="task-item-label">
            <strong style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {task.name}
              {task.is_recurring && <span title="Recurring daily task" style={{ fontSize: '0.85rem', cursor: 'help' }}>🔁</span>}
            </strong>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span className={`priority-dot priority-dot-${priority}`} title={`${priority} priority`} />
              <span style={{ fontSize: '0.8rem', fontWeight: '700', opacity: 0.8 }}>{task.displayCode}</span>
            </span>
          </span>
        </label>
        
        {!readOnly && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {onDelete && (
              <button 
                type="button" 
                className="delete-task-btn" 
                title="Delete Task" 
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onDelete(task.id);
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--danger)',
                  cursor: 'pointer',
                  fontSize: '1.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '0.2rem',
                  opacity: 0.6,
                  transition: 'opacity 0.15s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.opacity = 1}
                onMouseLeave={(e) => e.currentTarget.style.opacity = 0.6}
              >
                ×
              </button>
            )}
            <div className="drag-handle" title="Drag to reorder" {...dragHandleProps}>
              <span className="drag-line"></span>
              <span className="drag-line"></span>
            </div>
          </div>
        )}
      </div>

      {/* Checklist Subtasks Section */}
      {((task.subtasks && task.subtasks.length > 0) || !readOnly) && (
        <div className="task-subtasks-section" onClick={(e) => e.stopPropagation()}>
          {/* List existing subtasks */}
          {(task.subtasks || []).map(sub => (
            <div 
              key={sub.id} 
              className={`subtask-item ${sub.is_completed ? 'subtask-item-checked' : ''}`}
            >
              <label className="subtask-item-left">
                <input
                  type="checkbox"
                  checked={sub.is_completed}
                  disabled={readOnly}
                  className="subtask-checkbox"
                  onChange={(e) => handleToggleSubtask(sub.id, e.target.checked)}
                />
                <span className="subtask-label-text">{sub.name}</span>
              </label>
              {!readOnly && (
                <button
                  type="button"
                  className="subtask-delete-btn"
                  title="Delete Subtask"
                  onClick={() => handleDeleteSubtask(sub.id)}
                >
                  ×
                </button>
              )}
            </div>
          ))}

          {/* Add a new subtask row */}
          {!readOnly && (
            <form onSubmit={handleAddSubtask} className="subtask-add-row">
              <input
                type="text"
                className="subtask-add-input"
                placeholder="+ Add a subtask..."
                value={newSubtaskText}
                onChange={(e) => setNewSubtaskText(e.target.value)}
              />
              {newSubtaskText.trim() && (
                <button type="submit" className="subtask-add-btn" title="Add Subtask">
                  ✓
                </button>
              )}
            </form>
          )}
        </div>
      )}
    </div>
  );
}