export default function TaskItem({ task, checked, onToggle }) {
  return (
    <label className={`task-item ${checked ? 'task-item-checked' : ''}`}>
      <span className="task-item-check">
        <input type="checkbox" checked={checked} onChange={(event) => onToggle(task.id, event.target.checked)} />
      </span>
      <span className="task-item-label">
        <strong>{task.name}</strong>
        <span>#{task.order}</span>
      </span>
    </label>
  );
}