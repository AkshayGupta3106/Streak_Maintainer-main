import { useEffect, useState } from 'react';

import { getHistory, getLogByDate } from '../api/logs';
import CalendarGrid from './CalendarGrid';
import DayDetail from './DayDetail';
import ModalShell from './ModalShell';

function toDateKey(date) {
  return date.toISOString().slice(0, 10);
}

export default function HistoryModal({ open, onClose }) {
  const [history, setHistory] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    let cancelled = false;

    const loadHistory = async () => {
      try {
        setLoading(true);
        setError('');
        const data = await getHistory();

        if (cancelled) {
          return;
        }

        setHistory(data);
        const todayKey = toDateKey(new Date());
        setSelectedDate(todayKey);
        const todayLog = await getLogByDate(todayKey);

        if (!cancelled) {
          setSelectedLog(todayLog);
        }
      } catch {
        if (!cancelled) {
          setError('Failed to load history, try again');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadHistory();

    return () => {
      cancelled = true;
    };
  }, [open]);

  if (!open) {
    return null;
  }

  const historyList = Array.isArray(history) ? history : [];

  const historyMap = historyList.reduce((accumulator, entry) => {
    accumulator[entry.date] = entry;
    return accumulator;
  }, {});

  const handleSelectDate = async (dateKey) => {
    setSelectedDate(dateKey);
    setLoading(true);
    try {
      const { data } = await getLogByDate(dateKey);
      setSelectedLog(data);
      setError('');
    } catch {
      setError('Failed to load the selected day');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalShell title="History" onClose={onClose} wide>
      {error ? <div className="banner banner-error">{error}</div> : null}
      {loading && !historyList.length ? <p className="empty-copy">Loading history…</p> : null}
      <CalendarGrid historyMap={historyMap} selectedDate={selectedDate} onSelectDate={handleSelectDate} />
      <DayDetail dateValue={selectedDate} log={selectedLog} onLogUpdated={setSelectedLog} />
    </ModalShell>
  );
}