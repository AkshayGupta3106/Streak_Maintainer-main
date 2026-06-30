import { useEffect, useMemo, useRef, useState } from 'react';
import { getLogByDate, updateLogByDate } from '../api/logs';
import ModalShell from './ModalShell';

export default function DailyJournalModal({ open, onClose }) {
  const todayKey = useMemo(() => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }, []);

  const [selectedDate, setSelectedDate] = useState(todayKey);
  const [journalText, setJournalText] = useState('');
  const [isFrozen, setIsFrozen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const editorRef = useRef(null);
  const hasUnsavedChangesRef = useRef(false);
  const saveTimerRef = useRef(null);

  // Generate last 30 dates for switching pages
  const dateOptions = useMemo(() => {
    const options = [];
    const today = new Date();
    for (let i = 0; i < 30; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const dateKey = `${year}-${month}-${day}`;
      const label = d.toLocaleDateString(undefined, { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
      });
      options.push({
        key: dateKey,
        label: label + (i === 0 ? ' (Today)' : '')
      });
    }
    return options;
  }, []);

  const isToday = selectedDate === todayKey;

  // Load journal for selected date
  useEffect(() => {
    if (!open) return;
    
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const logData = await getLogByDate(selectedDate);
        if (active) {
          const content = logData.journal_entry || '';
          setJournalText(content);
          setIsFrozen(logData.is_frozen || false);
          hasUnsavedChangesRef.current = false;
        }
      } catch (err) {
        console.error("Failed to load journal entry for", selectedDate, err);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [selectedDate, open]);

  // Sync editor innerHTML when loading completes
  useEffect(() => {
    if (!loading && editorRef.current) {
      if (editorRef.current.innerHTML !== journalText) {
        editorRef.current.innerHTML = journalText;
      }
    }
  }, [loading, journalText]);

  // Debounced auto-save for today's entry only
  useEffect(() => {
    if (!open || !isToday || loading || !hasUnsavedChangesRef.current) return;

    saveTimerRef.current = setTimeout(async () => {
      setSaving(true);
      const textToSave = editorRef.current ? editorRef.current.innerHTML : journalText;
      try {
        await updateLogByDate(selectedDate, undefined, textToSave, undefined);
        hasUnsavedChangesRef.current = false;
      } catch (err) {
        console.error("Auto-save failed:", err);
      } finally {
        setSaving(false);
      }
    }, 800);

    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
    };
  }, [journalText, selectedDate, open, isToday, loading]);

  if (!open) return null;

  const handlePrint = () => {
    window.print();
  };

  const handleSave = async () => {
    if (!isToday || loading || saving) return;
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
    }
    setSaving(true);
    const textToSave = editorRef.current ? editorRef.current.innerHTML : journalText;
    try {
      await updateLogByDate(selectedDate, undefined, textToSave, undefined);
      hasUnsavedChangesRef.current = false;
      onClose();
    } catch (err) {
      console.error("Manual save failed:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleClose = async () => {
    if (isToday && hasUnsavedChangesRef.current) {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
      setSaving(true);
      const textToSave = editorRef.current ? editorRef.current.innerHTML : journalText;
      try {
        await updateLogByDate(selectedDate, undefined, textToSave, undefined);
        hasUnsavedChangesRef.current = false;
      } catch (err) {
        console.error("Failed to save on close:", err);
      } finally {
        setSaving(false);
      }
    }
    onClose();
  };

  const handleDateChange = async (newDate) => {
    if (isToday && hasUnsavedChangesRef.current) {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
      setSaving(true);
      const textToSave = editorRef.current ? editorRef.current.innerHTML : journalText;
      try {
        await updateLogByDate(selectedDate, undefined, textToSave, undefined);
        hasUnsavedChangesRef.current = false;
      } catch (err) {
        console.error("Failed to save on date change:", err);
      } finally {
        setSaving(false);
      }
    }
    setSelectedDate(newDate);
  };

  const format = (command, value = null) => {
    if (!isToday) return;
    document.execCommand(command, false, value);
    if (editorRef.current) {
      setJournalText(editorRef.current.innerHTML);
      hasUnsavedChangesRef.current = true;
    }
  };

  const handleInput = (e) => {
    setJournalText(e.currentTarget.innerHTML);
    hasUnsavedChangesRef.current = true;
  };


  return (
    <ModalShell title="Daily Journal & reflections" onClose={handleClose} wide>
      <div className="journal-modal-container">
        
        {/* Date Selector Row */}
        <div className="journal-date-bar">
          <label className="journal-date-label">
            <span>Choose Journal Page:</span>
            <select 
              value={selectedDate} 
              onChange={(e) => handleDateChange(e.target.value)}
              className="journal-date-select"
            >
              {dateOptions.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <div className="journal-status-badges">
            {isFrozen && <span className="journal-badge frozen-badge">❄️ Frozen Day</span>}
            {!isToday && (
              <span className="journal-badge locked-badge">🔒 Locked (Read-Only)</span>
            )}
            {saving && <span className="journal-save-indicator">Saving...</span>}
          </div>
        </div>

        {/* Google Docs Style Toolbar */}
        <div className="journal-toolbar">
          <div className="toolbar-section">
            <button type="button" className="toolbar-btn" title="Undo" onClick={() => format('undo')}>↶</button>
            <button type="button" className="toolbar-btn" title="Redo" onClick={() => format('redo')}>↷</button>
          </div>
          <div className="toolbar-divider" />
          <div className="toolbar-section">
            <button type="button" className="toolbar-btn bold-text" title="Bold" onClick={() => format('bold')}>B</button>
            <button type="button" className="toolbar-btn italic-text" title="Italic" onClick={() => format('italic')}>I</button>
            <button type="button" className="toolbar-btn underline-text" title="Underline" onClick={() => format('underline')}>U</button>
            <button type="button" className="toolbar-btn" title="Superscript" onClick={() => format('superscript')}>X²</button>
            <button type="button" className="toolbar-btn" title="Subscript" onClick={() => format('subscript')}>X₂</button>
          </div>
          <div className="toolbar-divider" />
          <div className="toolbar-section">
            <select 
              className="font-size-select"
              title="Font Size"
              onChange={(e) => format('fontSize', e.target.value)}
              defaultValue="3"
              disabled={!isToday}
            >
              <option value="1">Smallest</option>
              <option value="2">Small</option>
              <option value="3">Normal</option>
              <option value="4">Large</option>
              <option value="5">Larger</option>
              <option value="6">Largest</option>
              <option value="7">Huge</option>
            </select>
          </div>
          <div className="toolbar-divider" />
          <div className="toolbar-section">
            <button type="button" className="toolbar-btn" title="Align Left" onClick={() => format('justifyLeft')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'block' }}>
                <line x1="21" y1="6" x2="3" y2="6"></line>
                <line x1="15" y1="12" x2="3" y2="12"></line>
                <line x1="17" y1="18" x2="3" y2="18"></line>
              </svg>
            </button>
            <button type="button" className="toolbar-btn" title="Align Center" onClick={() => format('justifyCenter')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'block' }}>
                <line x1="21" y1="6" x2="3" y2="6"></line>
                <line x1="17" y1="12" x2="7" y2="12"></line>
                <line x1="19" y1="18" x2="5" y2="18"></line>
              </svg>
            </button>
            <button type="button" className="toolbar-btn" title="Align Right" onClick={() => format('justifyRight')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'block' }}>
                <line x1="21" y1="6" x2="3" y2="6"></line>
                <line x1="21" y1="12" x2="9" y2="12"></line>
                <line x1="21" y1="18" x2="7" y2="18"></line>
              </svg>
            </button>
          </div>
          <div className="toolbar-divider" style={{ marginLeft: 'auto' }} />
          <div className="toolbar-section" style={{ gap: '0.5rem' }}>
            <button 
              type="button" 
              className="toolbar-btn save-journal-btn" 
              title="Save Journal"
              onClick={handleSave}
              disabled={!isToday || loading || saving}
            >
              {saving ? (
                <>
                  <span className="spinner"></span>
                  Saving...
                </>
              ) : (
                '💾 Save'
              )}
            </button>
            <button 
              type="button" 
              className="toolbar-btn print-btn" 
              title="Print Journal Entry"
              onClick={handlePrint}
            >
              🖨️ Print Page
            </button>
          </div>
        </div>

        {/* Google Docs Page Sheet Layout */}
        <div className="journal-editor-workspace">
          {loading ? (
            <div className="journal-loading-overlay">Loading document...</div>
          ) : (
            <div className="journal-page-sheet print-document-container">
              {/* Document Header (For Printing) */}
              <div className="printable-header-doc">
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid #1e293b', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>
                  <h2 style={{ margin: 0, fontSize: '1.4rem', color: '#0f172a' }}>Daily Coding Journal</h2>
                  <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 'bold' }}>
                    {(() => {
                      if (!selectedDate) return '';
                      const [yr, mo, dy] = selectedDate.split('-').map(Number);
                      return new Date(yr, mo - 1, dy).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
                    })()}
                  </span>
                </div>
              </div>

              <div
                ref={editorRef}
                contentEditable={isToday}
                onInput={handleInput}
                className="journal-textarea-sheet"
                placeholder={isToday ? "Start writing today's journal entry here..." : "(No entry was logged on this day)"}
                style={{ outline: 'none', minHeight: '400px' }}
              />
            </div>
          )}
        </div>

      </div>
    </ModalShell>
  );
}
