import React, { useState, useEffect } from 'react';
import { getCalendarEvents } from '../api/hiring';
import { API_BASE_URL } from '../api/axios';

export default function HiringCalendar() {
  const todayDate = new Date();
  const [currentYear, setCurrentYear] = useState(todayDate.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(todayDate.getMonth() + 1); // 1-indexed
  const [calendarData, setCalendarData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchCalendar = async () => {
    try {
      setLoading(true);
      const data = await getCalendarEvents(currentYear, currentMonth);
      setCalendarData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalendar();
  }, [currentYear, currentMonth]);

  const handlePrevMonth = () => {
    if (calendarData?.nav?.prev) {
      setCurrentYear(calendarData.nav.prev.year);
      setCurrentMonth(calendarData.nav.prev.month);
    }
  };

  const handleNextMonth = () => {
    if (calendarData?.nav?.next) {
      setCurrentYear(calendarData.nav.next.year);
      setCurrentMonth(calendarData.nav.next.month);
    }
  };

  // Generate calendar days grid
  const getDaysInMonthGrid = () => {
    if (!calendarData) return [];

    const firstDayIndex = new Date(currentYear, currentMonth - 1, 1).getDay(); // Sunday is 0
    const totalDays = new Date(currentYear, currentMonth, 0).getDate();
    const prevMonthDays = new Date(currentYear, currentMonth - 1, 0).getDate();

    const days = [];

    // Add padding days from previous month
    // In India/standard, we usually start week on Sunday (0) or Monday (1)
    // Let's use Sunday start (0) for standard calendar grid representation
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      days.push({
        dayNum: prevMonthDays - i,
        isCurrentMonth: false,
        dateString: new Date(currentYear, currentMonth - 2, prevMonthDays - i).toISOString().split('T')[0]
      });
    }

    // Add days of current month
    for (let i = 1; i <= totalDays; i++) {
      days.push({
        dayNum: i,
        isCurrentMonth: true,
        dateString: `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(i).padStart(2, '0')}`
      });
    }

    // Add padding days for next month to complete the grid (usually 42 boxes total: 6 rows of 7 days)
    const remaining = 42 - days.length;
    for (let i = 1; i <= remaining; i++) {
      days.push({
        dayNum: i,
        isCurrentMonth: false,
        dateString: new Date(currentYear, currentMonth, i).toISOString().split('T')[0]
      });
    }

    return days;
  };

  const daysGrid = getDaysInMonthGrid();
  const events = calendarData?.events || [];

  const getEventsForDay = (dateStr) => {
    return events.filter((e) => {
      // Event overlaps with this day
      // e.start and e.end are ISO dates YYYY-MM-DD
      return dateStr >= e.start && dateStr <= e.end;
    });
  };

  const copyICalUrl = () => {
    // Construct the subscribe URL: backend base URL minus /api + /api/hiring/calendar.ics
    const icalUrl = `${API_BASE_URL}/hiring/calendar.ics`;
    navigator.clipboard.writeText(icalUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getICalUrl = () => {
    return `${API_BASE_URL}/hiring/calendar.ics`;
  };

  return (
    <div className="hiring-calendar-view">
      <div className="calendar-nav-header">
        <div>
          <h2 style={{ margin: 0, fontSize: '1.8rem', fontWeight: 800 }}>Drives & Deadlines Calendar</h2>
          <p style={{ margin: '0.25rem 0 0 0', color: 'var(--muted)', fontSize: '0.9rem' }}>Visual timeline of active hiring drives and registrations.</p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button onClick={handlePrevMonth} className="mood-btn" style={{ padding: '0.5rem 1rem' }}>
            ◀ Prev Month
          </button>
          <span style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text)', minWidth: '150px', textAlign: 'center' }}>
            {calendarData?.month_label || 'Loading...'}
          </span>
          <button onClick={handleNextMonth} className="mood-btn" style={{ padding: '0.5rem 1rem' }}>
            Next Month ▶
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-container">Loading Monthly Grid...</div>
      ) : (
        <div className="calendar-month-grid">
          {/* Day Headers */}
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
            <div key={d} className="calendar-day-header-cell">{d}</div>
          ))}

          {/* Days Grid */}
          {daysGrid.map((day, idx) => {
            const dayEvents = getEventsForDay(day.dateString);
            const isToday = day.dateString === calendarData?.today;

            return (
              <div
                key={idx}
                className={`calendar-day-cell ${day.isCurrentMonth ? '' : 'other-month'} ${isToday ? 'is-today' : ''}`}
              >
                <div className="calendar-day-num">{day.dayNum}</div>

                <div className="calendar-day-events-wrap">
                  {dayEvents.map((evt) => (
                    <button
                      key={evt.id}
                      className={`calendar-event-tag ${evt.color || 'blue'}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedEvent(selectedEvent?.id === evt.id ? null : evt);
                      }}
                      title={`${evt.title}`}
                    >
                      {evt.company} - {evt.role}
                    </button>
                  ))}
                </div>

                {/* Event details card overlay */}
                {selectedEvent && dayEvents.some((e) => e.id === selectedEvent.id) && (
                  <div className="calendar-detail-overlay">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
                      <strong style={{ fontSize: '0.85rem' }}>{selectedEvent.company}</strong>
                      <button onClick={(e) => { e.stopPropagation(); setSelectedEvent(null); }} style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: '0.8rem' }}>✕</button>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginBottom: '0.5rem' }}>{selectedEvent.role}</div>
                    <div style={{ fontSize: '0.75rem', background: 'rgba(255,255,255,0.04)', padding: '0.35rem 0.5rem', borderRadius: '6px', marginBottom: '0.6rem' }}>
                      ⏳ Status: <strong>{selectedEvent.status}</strong><br />
                      🏁 Ends: {selectedEvent.end}
                    </div>
                    {selectedEvent.portal && (
                      <a href={selectedEvent.portal} target="_blank" rel="noopener noreferrer" className="opp-portal-btn" style={{ width: '100%', justifyContent: 'center', padding: '0.35rem' }}>
                        Go to Portal
                      </a>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Copyable iCal Subscription Link */}
      <div className="ical-sync-card">
        <div>
          <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>📅 Add to Google / Apple Calendar</h4>
          <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.8rem', color: 'var(--muted)' }}>
            Subscribe to this URL in your calendar application to auto-sync placement deadlines.
          </p>
        </div>

        <div className="ical-sync-input-group">
          <input
            type="text"
            readOnly
            value={getICalUrl()}
            className="ical-sync-input"
            onClick={(e) => e.target.select()}
          />
          <button className="save-btn" onClick={copyICalUrl} style={{ padding: '0.5rem 1rem', borderRadius: '8px', fontSize: '0.8rem' }}>
            {copied ? '✓ Copied!' : '📋 Copy URL'}
          </button>
        </div>
      </div>
    </div>
  );
}
