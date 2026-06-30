import { useEffect, useMemo, useRef, useState } from 'react';
import { getLogByDate, updateLogByDate, getDailyQuote } from '../api/logs';
import ModalShell from './ModalShell';

const MOODS = [
  { emoji: '🌟', name: 'radiant', label: 'Radiant' },
  { emoji: '😊', name: 'happy', label: 'Happy' },
  { emoji: '😐', name: 'neutral', label: 'Neutral' },
  { emoji: '😔', name: 'down', label: 'Down' },
  { emoji: '😠', name: 'frustrated', label: 'Frustrated' }
];

const MOOD_COLORS = {
  radiant: '#10b981', // green
  happy: '#f59e0b', // gold/orange
  neutral: '#94a3b8', // slate/gray
  down: '#3b82f6', // blue
  frustrated: '#ef4444' // red
};

const REFLECTION_PROMPTS = [
  "Select a reflection prompt to insert...",
  "What made me smile today?",
  "What did I learn today?",
  "What was the biggest challenge, and how did I handle it?",
  "Who am I grateful for today?",
  "What would I have done differently today?"
];

const AVAILABLE_TAGS = ['Personal', 'Work', 'Family', 'Travel', 'Coding', 'Fitness', 'Milestone'];

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
  const [showSaveSuccess, setShowSaveSuccess] = useState(false);
  
  // Custom Journal States
  const [metadata, setMetadata] = useState({
    mood: '',
    rating: 0,
    gratitude: ['', '', ''],
    tomorrowGoals: ['', '', ''],
    song: '',
    tags: [],
    isPrivate: false,
    photo: ''
  });
  
  const [quote, setQuote] = useState({ text: 'Consistency shapes our character.', author: 'Unknown' });
  const [streak, setStreak] = useState(0);

  const editorRef = useRef(null);
  const hasUnsavedChangesRef = useRef(false);
  const saveTimerRef = useRef(null);
  const pageFlipRef = useRef(false);

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

  // Load Daily Quote
  useEffect(() => {
    if (!open) return;
    getDailyQuote()
      .then(data => setQuote(data))
      .catch(() => setQuote({ text: "Write your way to clear thinking.", author: "Unknown" }));
  }, [open]);

  // Load journal for selected date
  useEffect(() => {
    if (!open) return;
    
    let active = true;
    async function load() {
      setLoading(true);
      pageFlipRef.current = true;
      try {
        const logData = await getLogByDate(selectedDate);
        if (active) {
          const content = logData.journal_entry || '';
          setJournalText(content);
          setIsFrozen(logData.is_frozen || false);
          setStreak(logData.current_streak || 0);

          // Deserialize metadata
          const meta = logData.metadata || {};
          setMetadata({
            mood: meta.mood || '',
            rating: Number(meta.rating) || 0,
            gratitude: meta.gratitude || ['', '', ''],
            tomorrowGoals: meta.tomorrowGoals || ['', '', ''],
            song: meta.song || '',
            tags: meta.tags || [],
            isPrivate: Boolean(meta.isPrivate),
            photo: meta.photo || ''
          });

          hasUnsavedChangesRef.current = false;
          setTimeout(() => {
            pageFlipRef.current = false;
          }, 400);
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
        await updateLogByDate(selectedDate, undefined, textToSave, undefined, metadata);
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
  }, [journalText, selectedDate, open, isToday, loading, metadata]);

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
      await updateLogByDate(selectedDate, undefined, textToSave, undefined, metadata);
      hasUnsavedChangesRef.current = false;
      
      // Show smooth save checkmark animation before closing
      setShowSaveSuccess(true);
      setTimeout(() => {
        setShowSaveSuccess(false);
        onClose();
      }, 1000);
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
        await updateLogByDate(selectedDate, undefined, textToSave, undefined, metadata);
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
        await updateLogByDate(selectedDate, undefined, textToSave, undefined, metadata);
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

  const updateMetadataField = (field, value) => {
    if (!isToday) return;
    setMetadata(prev => {
      const next = { ...prev, [field]: value };
      hasUnsavedChangesRef.current = true;
      return next;
    });
  };

  const handlePhotoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        updateMetadataField('photo', reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleInsertPrompt = (e) => {
    const promptText = e.target.value;
    if (!promptText || promptText.startsWith("Select")) return;
    if (!isToday) return;
    
    // Insert prompt in the text area editor
    const htmlToInsert = `<blockquote>💭 <strong>${promptText}</strong><br>Write reflections here...</blockquote><p><br></p>`;
    
    if (editorRef.current) {
      editorRef.current.focus();
      document.execCommand('insertHTML', false, htmlToInsert);
      setJournalText(editorRef.current.innerHTML);
      hasUnsavedChangesRef.current = true;
    }
    // reset selection dropdown
    e.target.value = REFLECTION_PROMPTS[0];
  };

  const toggleTag = (tag) => {
    const currentTags = metadata.tags || [];
    let nextTags;
    if (currentTags.includes(tag)) {
      nextTags = currentTags.filter(t => t !== tag);
    } else {
      nextTags = [...currentTags, tag];
    }
    updateMetadataField('tags', nextTags);
  };

  const moodColor = MOOD_COLORS[metadata.mood] || 'var(--accent)';

  return (
    <ModalShell title="Daily Journal & reflections" onClose={handleClose} wide>
      <div 
        className="journal-modal-container"
        style={{ '--mood-accent': moodColor }}
      >
        
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
            {streak > 0 && (
              <span className="journal-badge streak-badge-flame">
                🔥 {streak} Day Streak
              </span>
            )}
            {isFrozen && <span className="journal-badge frozen-badge">❄️ Frozen Day</span>}
            {!isToday && (
              <span className="journal-badge locked-badge">🔒 Locked (Read-Only)</span>
            )}
            {metadata.isPrivate && (
              <span className="journal-badge privacy-badge">🔒 Private</span>
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
              className="font-family-select"
              title="Font Family"
              onChange={(e) => format('fontName', e.target.value)}
              defaultValue="Inter"
              disabled={!isToday}
            >
              <option value="Inter" style={{ fontFamily: 'Inter, sans-serif' }}>Inter</option>
              <option value="Outfit" style={{ fontFamily: 'Outfit, sans-serif' }}>Outfit</option>
              <option value="Montserrat" style={{ fontFamily: 'Montserrat, sans-serif' }}>Montserrat</option>
              <option value="Caveat" style={{ fontFamily: 'Caveat, cursive' }}>Caveat</option>
              <option value="Architects Daughter" style={{ fontFamily: '"Architects Daughter", cursive' }}>Architects Daughter</option>
              <option value="Shadows Into Light" style={{ fontFamily: '"Shadows Into Light", cursive' }}>Shadows Into Light</option>
              <option value="Indie Flower" style={{ fontFamily: '"Indie Flower", cursive' }}>Indie Flower</option>
              <option value="Dancing Script" style={{ fontFamily: '"Dancing Script", cursive' }}>Dancing Script</option>
              <option value="Gochi Hand" style={{ fontFamily: '"Gochi Hand", cursive' }}>Gochi Hand</option>
              <option value="Satisfy" style={{ fontFamily: 'Satisfy, cursive' }}>Satisfy</option>
              <option value="Great Vibes" style={{ fontFamily: '"Great Vibes", cursive' }}>Great Vibes</option>
              <option value="Patrick Hand" style={{ fontFamily: '"Patrick Hand", cursive' }}>Patrick Hand</option>
              <option value="Sacramento" style={{ fontFamily: 'Sacramento, cursive' }}>Sacramento</option>
              <option value="Reenie Beanie" style={{ fontFamily: '"Reenie Beanie", cursive' }}>Reenie Beanie</option>
              <option value="Amatic SC" style={{ fontFamily: '"Amatic SC", cursive' }}>Amatic SC</option>
              <option value="Permanent Marker" style={{ fontFamily: '"Permanent Marker", cursive' }}>Permanent Marker</option>
              <option value="Pacifico" style={{ fontFamily: 'Pacifico, cursive' }}>Pacifico</option>
              <option value="Lora" style={{ fontFamily: 'Lora, serif' }}>Lora</option>
              <option value="Playfair Display" style={{ fontFamily: '"Playfair Display", serif' }}>Playfair Display</option>
              <option value="EB Garamond" style={{ fontFamily: '"EB Garamond", serif' }}>EB Garamond</option>
              <option value="Fira Code" style={{ fontFamily: '"Fira Code", monospace' }}>Fira Code</option>
              <option value="Courier Prime" style={{ fontFamily: '"Courier Prime", monospace' }}>Courier Prime (Typewriter)</option>
              <option value="Arial" style={{ fontFamily: 'Arial, sans-serif' }}>Arial</option>
              <option value="Georgia" style={{ fontFamily: 'Georgia, serif' }}>Georgia</option>
              <option value="Times New Roman" style={{ fontFamily: '"Times New Roman", serif' }}>Times New Roman</option>
              <option value="Courier New" style={{ fontFamily: '"Courier New", monospace' }}>Courier New</option>
            </select>
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

          {/* Reflection Prompts Dropdown */}
          <div className="toolbar-section">
            <select 
              className="prompt-insert-select"
              title="Insert Reflection Prompt"
              onChange={handleInsertPrompt}
              defaultValue=""
              disabled={!isToday}
            >
              {REFLECTION_PROMPTS.map((p, i) => (
                <option key={i} value={p}>
                  {p}
                </option>
              ))}
            </select>
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

        {/* Dual Pane Layout */}
        <div className={`journal-workspace-grid ${pageFlipRef.current ? 'page-turn' : ''}`}>
          
          {/* Left Hand Details Panel (The Scrapbook Dashboard) */}
          <div className="journal-scrapbook-sidebar">
            
            {/* Mood Tracker */}
            <div className="scrapbook-card mood-card">
              <h3>😊 Mood Tracker</h3>
              <div className="mood-emojis-row">
                {MOODS.map(m => (
                  <button
                    key={m.name}
                    type="button"
                    title={m.label}
                    className={`mood-emoji-btn ${metadata.mood === m.name ? 'active' : ''}`}
                    disabled={!isToday}
                    onClick={() => updateMetadataField('mood', m.name)}
                  >
                    {m.emoji}
                  </button>
                ))}
              </div>
              {metadata.mood && (
                <span className="mood-name-caption">
                  Today is a <strong>{metadata.mood}</strong> day
                </span>
              )}
            </div>

            {/* Day Rating */}
            <div className="scrapbook-card stars-card">
              <h3>⭐ Rate Your Day</h3>
              <div className="stars-row">
                {[1, 2, 3, 4, 5].map(starNum => (
                  <button
                    key={starNum}
                    type="button"
                    className={`star-btn ${metadata.rating >= starNum ? 'filled' : ''}`}
                    disabled={!isToday}
                    onClick={() => updateMetadataField('rating', starNum)}
                  >
                    ★
                  </button>
                ))}
              </div>
            </div>

            {/* Private lock */}
            <div className="scrapbook-card lock-card">
              <h3>🔒 Security</h3>
              <button
                type="button"
                className={`lock-private-btn ${metadata.isPrivate ? 'private' : ''}`}
                disabled={!isToday}
                onClick={() => updateMetadataField('isPrivate', !metadata.isPrivate)}
              >
                {metadata.isPrivate ? '🔒 Private Entry' : '🔓 Public Entry'}
              </button>
            </div>

            {/* Gratitude section */}
            <div className="scrapbook-card gratitude-card">
              <h3>❤️ Three Gratitudes</h3>
              <ul className="gratitude-list">
                {(metadata.gratitude || ['', '', '']).map((val, idx) => (
                  <li key={idx}>
                    <span className="num">{idx + 1}.</span>
                    <input
                      type="text"
                      className="sidebar-text-input handwriting"
                      value={val}
                      disabled={!isToday}
                      placeholder="Write gratitude here..."
                      onChange={(e) => {
                        const newGrat = [...(metadata.gratitude || ['', '', ''])];
                        newGrat[idx] = e.target.value;
                        updateMetadataField('gratitude', newGrat);
                      }}
                    />
                  </li>
                ))}
              </ul>
            </div>

            {/* Tomorrow's Goals */}
            <div className="scrapbook-card goals-card">
              <h3>🎯 Tomorrow's Goals</h3>
              <ul className="tomorrow-goals-list">
                {(metadata.tomorrowGoals || ['', '', '']).map((val, idx) => (
                  <li key={idx}>
                    <span className="num">•</span>
                    <input
                      type="text"
                      className="sidebar-text-input handwriting"
                      value={val}
                      disabled={!isToday}
                      placeholder={`Goal ${idx + 1}...`}
                      onChange={(e) => {
                        const newGoals = [...(metadata.tomorrowGoals || ['', '', ''])];
                        newGoals[idx] = e.target.value;
                        updateMetadataField('tomorrowGoals', newGoals);
                      }}
                    />
                  </li>
                ))}
              </ul>
            </div>

            {/* Song of the Day */}
            <div className="scrapbook-card song-card">
              <h3>🎵 Song of the Day</h3>
              <div className="song-input-row">
                <input
                  type="text"
                  className="sidebar-text-input song-input"
                  value={metadata.song || ''}
                  disabled={!isToday}
                  placeholder="Song name & artist..."
                  onChange={(e) => updateMetadataField('song', e.target.value)}
                />
                {metadata.song && (
                  <div className="vinyl-disc-container">
                    <div className="vinyl-record">
                      <div className="vinyl-center"></div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Tags card */}
            <div className="scrapbook-card tags-card">
              <h3>🔖 Tags</h3>
              <div className="tags-container">
                {AVAILABLE_TAGS.map(t => (
                  <button
                    key={t}
                    type="button"
                    className={`tag-pill-btn ${(metadata.tags || []).includes(t) ? 'active' : ''}`}
                    disabled={!isToday}
                    onClick={() => toggleTag(t)}
                  >
                    #{t}
                  </button>
                ))}
              </div>
            </div>

          </div>

          {/* Right Hand Sheet (The Notebook Page) */}
          <div className="journal-editor-workspace">
            {loading ? (
              <div className="journal-loading-overlay">Loading document...</div>
            ) : (
              <div className={`journal-page-sheet print-document-container ${metadata.isPrivate && !isToday ? 'private-obfuscated' : ''}`}>
                
                {/* Spiral notebook rings */}
                <div className="notebook-spiral-rings">
                  {[...Array(12)].map((_, i) => (
                    <div key={i} className="notebook-spiral-ring">
                      <div className="metal-loop"></div>
                      <div className="ring-hole"></div>
                    </div>
                  ))}
                </div>

                {/* Decorative Scrapbook Stickers */}
                <div className="journal-sticker sticker-flower-top-left">🌸</div>
                <div className="journal-sticker sticker-star-right">✨</div>
                <div className="journal-sticker sticker-leaf-bottom-right">🍃</div>

                {/* Folded corner */}
                <div className="notebook-folded-corner"></div>

                {/* Document Header (For Printing) */}
                <div className="printable-header-doc">
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid var(--mood-accent)', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>
                    <h2 className="journal-handwritten-title">Daily Coding Journal</h2>
                    <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 'bold' }}>
                      {(() => {
                        if (!selectedDate) return '';
                        const [yr, mo, dy] = selectedDate.split('-').map(Number);
                        return new Date(yr, mo - 1, dy).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
                      })()}
                    </span>
                  </div>
                </div>

                {/* Polaroid photo attachment */}
                {(metadata.photo || isToday) && (
                  <div className="polaroid-attachment-container">
                    {metadata.photo ? (
                      <div className="polaroid-photo">
                        <div className="polaroid-tape"></div>
                        <div className="polaroid-image-frame">
                          <img src={metadata.photo} alt="Memory upload" />
                          {isToday && (
                            <button
                              type="button"
                              className="polaroid-remove-btn"
                              title="Remove Photo"
                              onClick={() => updateMetadataField('photo', '')}
                            >
                              ✕
                            </button>
                          )}
                        </div>
                        <div className="polaroid-caption">Memory from today</div>
                      </div>
                    ) : (
                      isToday && (
                        <div className="polaroid-uploader-box">
                          <label className="polaroid-upload-label">
                            <span className="upload-icon">📷</span>
                            <span>Stick a photo here</span>
                            <input 
                              type="file" 
                              accept="image/*" 
                              onChange={handlePhotoUpload} 
                              style={{ display: 'none' }} 
                            />
                          </label>
                        </div>
                      )
                    )}
                  </div>
                )}

                {/* Obfuscated Private Message */}
                {metadata.isPrivate && !isToday && (
                  <div className="private-journal-overlay">
                    <span className="lock-icon">🔒</span>
                    <h3>Private Journal Entry</h3>
                    <p>This page is marked private and locked.</p>
                  </div>
                )}

                {/* Content Editor Sheet */}
                <div
                  ref={editorRef}
                  contentEditable={isToday && !(metadata.isPrivate && !isToday)}
                  onInput={handleInput}
                  className="journal-textarea-sheet"
                  placeholder={isToday ? "Start writing today's journal entry here..." : "(No entry was logged on this day)"}
                  style={{ outline: 'none', minHeight: '400px' }}
                />

                {/* Daily Quote Box */}
                {quote && quote.text && (
                  <div className="journal-quote-callout">
                    <p className="quote-body">“{quote.text}”</p>
                    <p className="quote-by">— {quote.author}</p>
                  </div>
                )}

              </div>
            )}
          </div>

        </div>

        {/* Save success overlay */}
        {showSaveSuccess && (
          <div className="save-success-overlay animate-fade-in-out">
            <div className="save-success-badge">
              <span className="check-icon">✓</span>
              <span>Saved Journal Entry!</span>
            </div>
          </div>
        )}

      </div>
    </ModalShell>
  );
}
