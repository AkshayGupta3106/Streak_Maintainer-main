import { formatStreakDate } from '../utils/dateFormatter';

function formatDateKey(date) {
  return date.toISOString().slice(0, 10);
}

export default function CalendarGrid({ historyMap, selectedDate, onSelectDate }) {
  const days = [];
  const today = new Date();

  for (let offset = 29; offset >= 0; offset -= 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - offset);
    const dateKey = formatDateKey(date);
    const entry = historyMap[dateKey];
    const percentage = entry ? entry.completion_percentage : null;
    const isFrozen = entry ? entry.is_frozen : false;
    let statusClass = 'calendar-cell-empty';

    if (isFrozen) {
      statusClass = 'calendar-cell-frozen';
    } else if (percentage !== null) {
      if (percentage >= 100) {
        statusClass = 'calendar-cell-green';
      } else if (percentage >= 50) {
        statusClass = 'calendar-cell-yellow';
      } else {
        statusClass = 'calendar-cell-red';
      }
    }

    const weekday = new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(date).toLowerCase();

    days.push(
      <button
        key={dateKey}
        type="button"
        className={`calendar-cell ${statusClass} ${selectedDate === dateKey ? 'calendar-cell-selected' : ''}`}
        onClick={() => onSelectDate(dateKey)}
      >
        <span>{formatStreakDate(date)}</span>
        <small>{weekday}</small>
        <strong>{isFrozen ? '❄️ Frozen' : (percentage === null ? '—' : `${percentage}%`)}</strong>
      </button>,
    );
  }

  return <div className="calendar-grid">{days}</div>;
}