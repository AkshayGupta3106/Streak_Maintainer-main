import { useEffect, useMemo, useState } from 'react';

import { getTodayLog, updateTodayLog } from '../api/logs';
import { getUpcomingContests, getCodingProfileStats, getDailyQuote } from '../api/profiles';
import { getTasks, deleteTask, updateTask } from '../api/tasks';
import CodingProfilesModal from '../components/CodingProfilesModal';
import HistoryModal from '../components/HistoryModal';
import ManageTasksModal from '../components/ManageTasksModal';
import LongTermGoalsModal from '../components/LongTermGoalsModal';
import TaskItem from '../components/TaskItem';
import DailyJournalModal from '../components/DailyJournalModal';
import { useAuth } from '../context/AuthContext';
import { formatStreakDate } from '../utils/dateFormatter';
import { triggerConfetti } from '../utils/confetti';

const PHASE_DATA = {
  morning: {
    title: 'Start Every Morning Fully Caught Up',
    eyebrow: '🌅 Morning Phase',
    quotes: [
      'Small wins compound into strong streaks.',
      'Consistency beats intensity when the goal is lasting change.',
      'Do the easy part today so tomorrow is lighter.',
      'The morning breeze has secrets to tell you. Don\'t go back to sleep.',
      'Start your day by checking off your core streaks.'
    ]
  },
  afternoon: {
    title: 'Power Through Your Afternoon Productively',
    eyebrow: '☀️ Afternoon Phase',
    quotes: [
      'Momentum is built one checked box at a time.',
      'Your future self reads the log you write today.',
      'Progress loves repetition.',
      'Keep pushing; you are already halfway to your daily goals.',
      'Focus on progress, not perfection.'
    ]
  },
  evening: {
    title: 'Wind Down Your Evening with Gratitude',
    eyebrow: '🌇 Evening Phase',
    quotes: [
      'One honest day is better than a perfect plan you never start.',
      'Reflect on today\'s efforts. Every step counts.',
      'Quiet progress is still progress.',
      'Streaks turn intention into identity.',
      'A clean checklist is a quiet kind of momentum.'
    ]
  },
  night: {
    title: 'Rest Easy Tonight, Ready for Tomorrow',
    eyebrow: '🌌 Night Phase',
    quotes: [
      'Sleep is the best meditation. Recover for tomorrow\'s streak.',
      'You did your best today. Rest now.',
      'Tomorrow is a clean slate and a new opportunity.',
      'Track the habit, then let the habit carry you.',
      'Resting is part of the process, not a pause in it.'
    ]
  }
};

const FALLBACK_QUOTES = [
  { text: "Consistency beats intensity when the goal is lasting change.", author: "James Clear" },
  { text: "Do the easy part today so tomorrow is lighter.", author: "Unknown" },
  { text: "Small wins compound into strong streaks.", author: "James Clear" },
  { text: "One honest day is better than a perfect plan you never start.", author: "Unknown" },
  { text: "Focus on progress, not perfection.", author: "Bill Gates" },
  { text: "The secret of getting ahead is getting started.", author: "Mark Twain" },
  { text: "It's not that I'm so smart, it's just that I stay with problems longer.", author: "Albert Einstein" },
  { text: "Quality is not an act, it is a habit.", author: "Aristotle" },
  { text: "First, solve the problem. Then, write the code.", author: "John Johnson" },
  { text: "Experience is the name everyone gives to their mistakes.", author: "Oscar Wilde" },
  { text: "In order to be irreplaceable one must always be different.", author: "Coco Chanel" },
  { text: "Make each day your masterpiece.", author: "John Wooden" },
  { text: "Before software can be reusable it first has to be usable.", author: "Ralph Johnson" },
  { text: "Simplicity is the soul of efficiency.", author: "Austin Freeman" },
  { text: "Patience is a necessary ingredient of genius.", author: "Napoleon Hill" },
  { text: "The best way to predict the future is to invent it.", author: "Alan Kay" },
  { text: "Code is like humor. When you have to explain it, it’s bad.", author: "Cory House" },
  { text: "Fix the cause, not the symptom.", author: "Steve Maguire" },
  { text: "Make it work, make it right, make it fast.", author: "Kent Beck" },
  { text: "Clean code always looks like it was written by someone who cares.", author: "Michael Feathers" }
];

function getISTHour() {
  const options = { timeZone: 'Asia/Kolkata', hour: '2-digit', hour12: false };
  const formatter = new Intl.DateTimeFormat('en-US', options);
  const parts = formatter.formatToParts(new Date());
  const hourPart = parts.find(part => part.type === 'hour');
  return hourPart ? parseInt(hourPart.value, 10) : new Date().getHours();
}

function getISTTimeString() {
  const options = { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
  const formatter = new Intl.DateTimeFormat('en-US', options);
  return formatter.format(new Date());
}

function getPhaseForHour(hour) {
  if (hour >= 5 && hour < 12) return 'morning';
  if (hour >= 12 && hour < 17) return 'afternoon';
  if (hour >= 17 && hour < 21) return 'evening';
  return 'night';
}

function formatToday() {
  return formatStreakDate(new Date());
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [completedTaskIds, setCompletedTaskIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const [codingProfilesOpen, setCodingProfilesOpen] = useState(false);
  const [goalsOpen, setGoalsOpen] = useState(false);
  const [journalOpen, setJournalOpen] = useState(false);
  const [contests, setContests] = useState([]);
  const [loadingContests, setLoadingContests] = useState(false);
  const [profileStats, setProfileStats] = useState(null);

  // Streak, Tokens, & Journal States
  const [currentStreak, setCurrentStreak] = useState(0);
  const [bestStreak, setBestStreak] = useState(0);

  // Time & Phase State
  const [istTime, setIstTime] = useState(getISTTimeString());
  const [currentPhase, setCurrentPhase] = useState(() => getPhaseForHour(getISTHour()));
  const [theme, setTheme] = useState(() => localStorage.getItem('streak_theme') || 'dark');
  const [accentColor, setAccentColor] = useState(() => localStorage.getItem('streak_accent') || 'emerald');
  const [moreDropdownOpen, setMoreDropdownOpen] = useState(false);
  const [displayTasks, setDisplayTasks] = useState([]);

  // Custom task ordering & daily quotes & dragging
  const [customOrderIds, setCustomOrderIds] = useState(() => {
    try {
      const saved = localStorage.getItem('streak_custom_task_order');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [dailyQuote, setDailyQuote] = useState(() => {
    const dayOfYear = Math.floor((new Date() - new Date(new Date().getFullYear(), 0, 0)) / 86400000);
    return FALLBACK_QUOTES[dayOfYear % FALLBACK_QUOTES.length];
  });
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [canDrag, setCanDrag] = useState(false);

  const activePhase = currentPhase;

  // Persist settings
  useEffect(() => {
    localStorage.setItem('streak_theme', theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem('streak_accent', accentColor);
  }, [accentColor]);

  // Sync clock every second
  useEffect(() => {
    const timer = setInterval(() => {
      setIstTime(getISTTimeString());
      setCurrentPhase(getPhaseForHour(getISTHour()));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch daily quote from backend proxy
  useEffect(() => {
    let active = true;
    async function fetchQuote() {
      try {
        const data = await getDailyQuote();
        if (active && data?.text) {
          setDailyQuote({
            text: data.text,
            author: data.author || 'Unknown'
          });
        }
      } catch (err) {
        console.warn('Quote fetch failed, utilizing rotation fallback:', err);
      }
    }
    fetchQuote();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;


    async function load() {
      setLoading(true);
      setLoadingContests(true);
      setError('');
      try {
        const [taskData, logData, contestData, statsData] = await Promise.all([
          getTasks(),
          getTodayLog(),
          getUpcomingContests().catch(() => []),
          getCodingProfileStats().catch(() => null),
        ]);
        if (!cancelled) {
          setTasks(taskData);
          setCompletedTaskIds(logData.completed_task_ids || []);
          setContests(contestData);
          setProfileStats(statsData);
          setCurrentStreak(logData.current_streak || 0);
          setBestStreak(logData.longest_streak || 0);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError('Failed to load dashboard.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setLoadingContests(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (loading) {
      return undefined;
    }

    const timer = window.setTimeout(async () => {
      setSaving(true);
      setError('');
      try {
        const updatedLog = await updateTodayLog(completedTaskIds, undefined, undefined);
        if (updatedLog) {
          setCurrentStreak(updatedLog.current_streak || 0);
          setBestStreak(updatedLog.longest_streak || 0);
        }
      } catch (requestError) {
        setError('Failed to save log details, try again.');
      } finally {
        setSaving(false);
      }
    }, 800);

    return () => window.clearTimeout(timer);
  }, [completedTaskIds, loading]);

  const activeTasks = useMemo(() => tasks.filter((task) => task.is_active !== false), [tasks]);

  const defaultSortedTasks = useMemo(() => {
    const PRIORITY_ORDER = { high: 1, medium: 2, low: 3 };
    const sorted = [...activeTasks].sort((left, right) => {
      const leftRank = PRIORITY_ORDER[left.priority] || 2;
      const rightRank = PRIORITY_ORDER[right.priority] || 2;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return left.id - right.id;
    });

    let highCount = 0;
    let mediumCount = 0;
    let lowCount = 0;

    return sorted.map(task => {
      let code = '';
      const prio = task.priority || 'medium';
      if (prio === 'high') {
        highCount++;
        code = `H${highCount}`;
      } else if (prio === 'medium') {
        mediumCount++;
        code = `M${mediumCount}`;
      } else {
        lowCount++;
        code = `L${lowCount}`;
      }
      return { ...task, displayCode: code };
    });
  }, [activeTasks]);

  const finalTasks = useMemo(() => {
    if (customOrderIds.length > 0) {
      const idMap = new Map(customOrderIds.map((id, index) => [id, index]));
      return [...defaultSortedTasks].sort((left, right) => {
        const leftIdx = idMap.has(left.id) ? idMap.get(left.id) : 999999;
        const rightIdx = idMap.has(right.id) ? idMap.get(right.id) : 999999;
        if (leftIdx !== rightIdx) {
          return leftIdx - rightIdx;
        }
        return defaultSortedTasks.indexOf(left) - defaultSortedTasks.indexOf(right);
      });
    }
    return defaultSortedTasks;
  }, [defaultSortedTasks, customOrderIds]);

  useEffect(() => {
    setDisplayTasks(finalTasks);
  }, [finalTasks]);

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', index.toString());
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    setDisplayTasks(prev => {
      const newTasks = [...prev];
      const [draggedItem] = newTasks.splice(draggedIndex, 1);
      newTasks.splice(index, 0, draggedItem);
      
      const ids = newTasks.map(t => t.id);
      setCustomOrderIds(ids);
      localStorage.setItem('streak_custom_task_order', JSON.stringify(ids));
      
      return newTasks;
    });

    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setCanDrag(false);
  };

  const completedVisibleCount = activeTasks.filter((task) => completedTaskIds.includes(task.id)).length;
  const completionPercentage = activeTasks.length ? Math.round((completedVisibleCount / activeTasks.length) * 100) : 0;

  useEffect(() => {
    if (completionPercentage === 100 && activeTasks.length > 0) {
      triggerConfetti();
    }
  }, [completionPercentage, activeTasks.length]);

  const toggleTask = (taskId, checked) => {
    setCompletedTaskIds((current) => {
      const next = new Set(current);
      if (checked) {
        next.add(taskId);
      } else {
        next.delete(taskId);
      }
      return Array.from(next);
    });
  };

  const handleUpdateSubtasks = async (taskId, nextSubtasks) => {
    try {
      const updated = await updateTask(taskId, { subtasks: nextSubtasks });
      setTasks(prev => prev.map(t => t.id === taskId ? updated : t));
    } catch (err) {
      console.error("Failed to update task subtasks:", err);
      setError("Failed to update subtasks, please try again.");
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm("Are you sure you want to delete this task?")) return;
    try {
      setError('');
      await deleteTask(taskId);
      const nextTasks = await getTasks();
      setTasks(nextTasks);
      
      const logData = await getTodayLog();
      setCompletedTaskIds(logData.completed_task_ids || []);
      setCurrentStreak(logData.current_streak || 0);
      setBestStreak(logData.longest_streak || 0);
    } catch (err) {
      console.error("Failed to delete task:", err);
      setError("Failed to delete task, please try again.");
    }
  };

  const getBackgroundStyle = () => {
    let gradient = theme === 'dark' 
      ? 'rgba(10, 20, 38, 0.72), rgba(8, 17, 32, 0.82)' 
      : 'rgba(255, 255, 255, 0.45), rgba(240, 244, 248, 0.55)';
      
    if (activePhase === 'afternoon') {
      gradient = theme === 'dark' 
        ? 'rgba(10, 20, 38, 0.68), rgba(8, 17, 32, 0.78)' 
        : 'rgba(255, 255, 255, 0.4), rgba(240, 244, 248, 0.5)';
    } else if (activePhase === 'night') {
      gradient = theme === 'dark' 
        ? 'rgba(5, 10, 20, 0.78), rgba(4, 8, 16, 0.88)' 
        : 'rgba(235, 240, 245, 0.5), rgba(220, 225, 235, 0.6)';
    }
    return {
      backgroundImage: `linear-gradient(${gradient}), url('/images/${activePhase}.png')`
    };
  };

  return (
    <div className={`dashboard-shell-container theme-${theme} accent-${accentColor} mode-${activePhase}`} style={getBackgroundStyle()}>
      <header className="dashboard-header">
        <div className="header-logo">
          <svg width="32" height="32" viewBox="0 0 400 400" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginRight: '0.45rem' }}>
            {/* Background circle */}
            <circle cx="200" cy="200" r="180" fill="#0F172A"/>
            
            {/* Streak Flame */}
            <path d="M200 80 Q160 140 170 200 Q160 260 200 300 Q240 260 230 200 Q240 140 200 80" fill="#F97316"/>
            <path d="M200 100 Q170 150 175 190 Q170 230 200 260 Q230 230 225 190 Q230 150 200 100" fill="#FB923C"/>
            
            {/* Checkmarks forming streak */}
            <path d="M165 170 L180 185 L210 150" stroke="#67E8F9" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M175 200 L190 215 L220 180" stroke="#22D3EE" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
            
            {/* Code brackets */}
            <text x="95" y="255" font-family="monospace" font-size="52" fill="#67E8F9" font-weight="bold">{"{"}</text>
            <text x="255" y="255" font-family="monospace" font-size="52" fill="#67E8F9" font-weight="bold">{"}"}</text>
            
            {/* Text */}
            <text x="200" y="340" text-anchor="middle" font-family="Arial, sans-serif" font-size="44" font-weight="700" fill="#E0F2FE">EYES ON</text>
            <text x="200" y="375" text-anchor="middle" font-family="Arial, sans-serif" font-size="36" font-weight="600" fill="#F97316">STREAK</text>
          </svg>
          <strong className="desktop-only">Eyes on Streak</strong>
        </div>
        
        <div className="header-clock" style={{ display: 'flex', gap: '0.65rem', alignItems: 'center' }}>
          <span className="clock-time">
            <span>{istTime.split(':')[0]}:{istTime.split(':')[1]}</span>
            <span className="desktop-only">:{istTime.split(':')[2]}</span>
          </span>
          {currentStreak > 0 && (
            <span className="header-streak-badge" title={`${currentStreak} days active streak!`}>
              {currentStreak}🔥
            </span>
          )}
        </div>
        
        {/* Unified Controls */}
        <div className="header-controls">
          <button
            type="button"
            className="primary-button add-tasks-header-btn"
            onClick={() => setManageOpen(true)}
            style={{ 
              padding: '0.45rem 1.1rem', 
              fontSize: '0.85rem', 
              borderRadius: '12px', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.35rem',
              cursor: 'pointer'
            }}
          >
            <span>➕</span>
            <span className="desktop-only">Add Tasks</span>
            <span className="mobile-only">Tasks</span>
          </button>
          
          <div className="accent-picker desktop-only">
            <button 
              type="button" 
              className={`accent-dot emerald ${accentColor === 'emerald' ? 'active' : ''}`}
              onClick={() => setAccentColor('emerald')}
              title="Emerald Accent"
            />
            <button 
              type="button" 
              className={`accent-dot ocean ${accentColor === 'ocean' ? 'active' : ''}`}
              onClick={() => setAccentColor('ocean')}
              title="Ocean Accent"
            />
            <button 
              type="button" 
              className={`accent-dot coral ${accentColor === 'coral' ? 'active' : ''}`}
              onClick={() => setAccentColor('coral')}
              title="Coral Accent"
            />
            <button 
              type="button" 
              className={`accent-dot sunset ${accentColor === 'sunset' ? 'active' : ''}`}
              onClick={() => setAccentColor('sunset')}
              title="Sunset Accent"
            />
          </div>
          <button 
            type="button" 
            className="secondary-button theme-toggle-btn" 
            onClick={() => setTheme(prev => prev === 'dark' ? 'light' : 'dark')}
            style={{ padding: '0.45rem 1rem', fontSize: '0.85rem', borderRadius: '12px', display: 'flex', alignItems: 'center' }}
          >
            <span style={{ marginRight: '0.35rem' }}>{theme === 'dark' ? '☀️' : '🌙'}</span>
            <span className="desktop-only">{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
          
          <div className="more-dropdown-wrapper" style={{ position: 'relative' }}>
            <button 
              type="button" 
              className={`secondary-button more-btn ${moreDropdownOpen ? 'active' : ''}`}
              onClick={() => setMoreDropdownOpen(prev => !prev)}
              style={{ padding: '0.45rem 1rem', fontSize: '0.85rem', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <span className="desktop-only">⚙️</span>
              <span className="mobile-only" style={{ display: 'none' }}>
                <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="3" y1="5" x2="17" y2="5" strokeLinecap="round" />
                  <line x1="3" y1="10" x2="17" y2="10" strokeLinecap="round" />
                  <line x1="3" y1="15" x2="17" y2="15" strokeLinecap="round" />
                </svg>
              </span>
              <span className="desktop-only">More</span>
            </button>
            {moreDropdownOpen && (
              <div className="more-dropdown-menu">
                <div className="menu-section mobile-only">
                  <span className="menu-label">Accent Color</span>
                  <div className="accent-picker" style={{ border: 'none', background: 'none', padding: 0 }}>
                    <button 
                      type="button" 
                      className={`accent-dot emerald ${accentColor === 'emerald' ? 'active' : ''}`}
                      onClick={() => setAccentColor('emerald')}
                    />
                    <button 
                      type="button" 
                      className={`accent-dot ocean ${accentColor === 'ocean' ? 'active' : ''}`}
                      onClick={() => setAccentColor('ocean')}
                    />
                    <button 
                      type="button" 
                      className={`accent-dot coral ${accentColor === 'coral' ? 'active' : ''}`}
                      onClick={() => setAccentColor('coral')}
                    />
                    <button 
                      type="button" 
                      className={`accent-dot sunset ${accentColor === 'sunset' ? 'active' : ''}`}
                      onClick={() => setAccentColor('sunset')}
                    />
                  </div>
                </div>
                <hr className="menu-divider mobile-only" />
                <button 
                  type="button" 
                  className="menu-item-btn" 
                  onClick={() => { setHistoryOpen(true); setMoreDropdownOpen(false); }}
                >
                  ⏳ History
                </button>
                <button 
                  type="button" 
                  className="menu-item-btn" 
                  onClick={() => { setCodingProfilesOpen(true); setMoreDropdownOpen(false); }}
                >
                  🏆 Coding Profiles
                </button>
                <button 
                  type="button" 
                  className="menu-item-btn" 
                  onClick={() => { setGoalsOpen(true); setMoreDropdownOpen(false); }}
                >
                  🎯 Long-Term Goals
                </button>
                <button 
                  type="button" 
                  className="menu-item-btn" 
                  onClick={() => { setJournalOpen(true); setMoreDropdownOpen(false); }}
                >
                  📖 Daily Journal
                </button>
                <hr className="menu-divider" />
                <button 
                  type="button" 
                  className="menu-item-btn danger-item" 
                  onClick={logout}
                >
                  🚪 Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="dashboard-shell">
        <section className="hero-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1.5rem' }}>
          <div>
            <p className="eyebrow">{PHASE_DATA[activePhase].eyebrow}</p>
            <h1>{PHASE_DATA[activePhase].title}</h1>
            <p className="hero-panel__welcome">Good to see you, {user?.name || user?.username || 'Streak Tracker'}</p>
            <p className="hero-panel__date">{formatToday()}</p>
          </div>
          
          <div className="hero-streak-display">
            <div className="streak-stat-box">
              <span className="streak-label">Current Streak</span>
              <span className="streak-value">{currentStreak}🔥</span>
            </div>
            <div className="streak-stat-box">
              <span className="streak-label">Best Streak</span>
              <span className="streak-value">{bestStreak}🔥</span>
            </div>
          </div>
        </section>

        <section className="merged-activity-panel">
          <div className="activity-left">
            <div className="progress-ring-container">
              <svg className="progress-ring" width="88" height="88">
                <circle
                  className="progress-ring__circle-bg"
                  stroke="rgba(255,255,255,0.06)"
                  strokeWidth="8"
                  fill="transparent"
                  r="34"
                  cx="44"
                  cy="44"
                />
                <circle
                  className="progress-ring__circle"
                  stroke="var(--accent)"
                  strokeWidth="8"
                  strokeDasharray="213.628"
                  strokeDashoffset={213.628 - (completionPercentage / 100) * 213.628}
                  strokeLinecap="round"
                  fill="var(--accent)"
                  fillOpacity={(completionPercentage / 100) * 0.12}
                  r="34"
                  cx="44"
                  cy="44"
                  style={{
                    transition: 'stroke-dashoffset 0.6s ease-in-out, fill-opacity 0.6s ease-in-out',
                    transform: 'rotate(-90deg)',
                    transformOrigin: '50% 50%'
                  }}
                />
              </svg>
              <div className="progress-ring-text">{completionPercentage}%</div>
            </div>
            <div className="progress-stats">
              <span className="eyebrow">Your Daily Progress</span>
              <h2 style={{ margin: '0.15rem 0 0.35rem 0', fontSize: '1.4rem' }}>Today's Activity</h2>
              <p className="muted" style={{ margin: 0, fontSize: '0.9rem' }}>
                {completedVisibleCount} of {activeTasks.length} tasks complete
              </p>
            </div>
          </div>
          <div className="activity-divider" />
          <div className="activity-right">
            <blockquote className="daily-quote">
              <p className="quote-text">“{dailyQuote.text}”</p>
              <cite className="quote-author">— {dailyQuote.author}</cite>
            </blockquote>
          </div>
        </section>

        {error ? <div className="banner banner--error">{error}</div> : null}
        {saving ? <div className="banner">Saving streak data...</div> : null}

        <div className="split">
          <section className="task-panel">
            <div className="task-panel__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p className="eyebrow">Today's tasks</p>
                <h2>Your checklist</h2>
              </div>
              <button 
                type="button" 
                className="secondary-button add-task-header-btn" 
                onClick={() => setManageOpen(true)}
                title="Manage Tasks"
                style={{ 
                  width: '2.4rem', 
                  height: '2.4rem', 
                  borderRadius: '50%', 
                  fontSize: '1.25rem', 
                  display: 'grid', 
                  placeItems: 'center', 
                  padding: 0,
                  fontWeight: 'normal'
                }}
              >
                ＋
              </button>
            </div>

            {loading ? <div className="loading-state">Loading dashboard...</div> : null}

            {!loading && activeTasks.length === 0 ? (
              <div className="empty-state">Add your first task of today to get started!</div>
            ) : null}

            <div className="task-list">
              {displayTasks.map((task, index) => (
                <div
                  key={task.id}
                  draggable={canDrag}
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDragEnd={handleDragEnd}
                  className={`task-drag-wrapper ${draggedIndex === index ? 'is-dragging' : ''}`}
                >
                  <TaskItem
                    task={task}
                    checked={completedTaskIds.includes(task.id)}
                    onToggle={toggleTask}
                    onDelete={handleDeleteTask}
                    onUpdateSubtasks={handleUpdateSubtasks}
                    dragHandleProps={{
                      onMouseDown: () => setCanDrag(true),
                      onMouseUp: () => setCanDrag(false),
                      onTouchStart: () => setCanDrag(true),
                      onTouchEnd: () => setCanDrag(false)
                    }}
                  />
                </div>
              ))}
            </div>
          </section>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {/* Today's Journal & Freeze Widget */}
            {/* Today's Journal Promo Card */}
            <section className="task-panel">
              <div className="task-panel__header">
                <div>
                  <p className="eyebrow">Personal reflections</p>
                  <h2>Daily Journal</h2>
                </div>
              </div>
              <div className="journal-promo-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '1.25rem 1.5rem', textAlign: 'center', background: 'rgba(255,255,255,0.01)', border: '1px dashed var(--line)', borderRadius: '16px', marginTop: '1rem', gap: '0.85rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.6rem' }}>
                  <span style={{ fontSize: '1.5rem', lineHeight: '1' }}>✍️</span>
                  <p style={{ margin: 0, fontSize: '1.05rem', fontWeight: '500', color: 'var(--text)' }}>
                    Want to journal your day? Go ahead
                  </p>
                </div>
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => setJournalOpen(true)}
                  style={{ width: '100%', maxWidth: '200px', padding: '0.6rem 1.5rem', borderRadius: '12px' }}
                >
                  Enter
                </button>
              </div>
            </section>
            {/* Platform Stats Section */}
            {profileStats && (profileStats.leetcode || profileStats.codeforces) ? (
              <section className="task-panel">
                <div className="task-panel__header">
                  <div>
                    <p className="eyebrow">Platform Stats</p>
                    <h2>Solved Problems</h2>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.85rem', marginTop: '1rem' }}>
                  {profileStats.leetcode && (
                    <div className="task-item" style={{ flexDirection: 'column', alignItems: 'stretch', padding: '1rem', background: 'rgba(255,255,255,0.02)', gap: '0.6rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong style={{ color: '#FFA116' }}>LeetCode</strong>
                        <strong style={{ fontSize: '1.25rem' }}>{profileStats.leetcode.all || 0}</strong>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.3rem', textAlign: 'center', fontSize: '0.75rem' }}>
                        <div style={{ background: 'rgba(0,184,163,0.08)', color: '#00B8A3', padding: '0.3rem 0.15rem', borderRadius: '8px' }}>
                          <div>Easy</div>
                          <strong>{profileStats.leetcode.easy || 0}</strong>
                        </div>
                        <div style={{ background: 'rgba(255,192,30,0.08)', color: '#FFC01E', padding: '0.3rem 0.15rem', borderRadius: '8px' }}>
                          <div>Med</div>
                          <strong>{profileStats.leetcode.medium || 0}</strong>
                        </div>
                        <div style={{ background: 'rgba(239,71,111,0.08)', color: '#EF476F', padding: '0.3rem 0.15rem', borderRadius: '8px' }}>
                          <div>Hard</div>
                          <strong>{profileStats.leetcode.hard || 0}</strong>
                        </div>
                      </div>
                    </div>
                  )}
                  {profileStats.codeforces && (
                    <div className="task-item" style={{ flexDirection: 'column', alignItems: 'stretch', padding: '1rem', background: 'rgba(255,255,255,0.02)', justifyContent: 'center', gap: '0.6rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong style={{ color: '#3B5998' }}>Codeforces</strong>
                        <strong style={{ fontSize: '1.25rem' }}>{profileStats.codeforces.all || 0}</strong>
                      </div>
                      <span className="muted" style={{ fontSize: '0.75rem' }}>Unique problems solved</span>
                    </div>
                  )}
                </div>
              </section>
            ) : null}

            {/* Upcoming Contests Section */}
            <section className="task-panel" style={{ flex: 1 }}>
              <div className="task-panel__header">
                <div>
                  <p className="eyebrow">Competitive Programming</p>
                  <h2>Upcoming Contests</h2>
                </div>
              </div>

              {loadingContests ? <div className="loading-state">Loading contests...</div> : null}

              {!loadingContests && contests.length === 0 ? (
                <div className="empty-state">
                  No upcoming contests. Connect your coding profiles to sync upcoming events!
                </div>
              ) : null}

              <div className="task-list">
                {contests.slice(0, 10).map((contest) => {
                  const datePart = formatStreakDate(contest.start_time);
                  const timePart = new Date(contest.start_time).toLocaleTimeString(undefined, {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                  });
                  const start = `${datePart}, ${timePart}`;
                  return (
                    <div key={contest.id} className="task-item" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                      <div className="task-item-label">
                        <strong>{contest.title}</strong>
                        <span style={{ fontSize: '0.8rem' }}>{contest.source_name} • {start} • {contest.duration_minutes} mins</span>
                      </div>
                      <a href={contest.url} target="_blank" rel="noopener noreferrer" className="secondary-button" style={{ textDecoration: 'none', padding: '0.4rem 0.8rem', borderRadius: '10px', fontSize: '0.85rem' }}>
                        View
                      </a>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        </div>
      </div>

      <HistoryModal open={historyOpen} onClose={() => setHistoryOpen(false)} />
      <DailyJournalModal
        open={journalOpen}
        onClose={async () => {
          setJournalOpen(false);
          try {
            const logData = await getTodayLog();
            setCurrentStreak(logData.current_streak || 0);
            setBestStreak(logData.longest_streak || 0);

          } catch (err) {
            console.error("Failed to refresh today's log after journal close:", err);
          }
        }}
      />
      <LongTermGoalsModal open={goalsOpen} onClose={() => setGoalsOpen(false)} />
      <ManageTasksModal
        open={manageOpen}
        tasks={tasks}
        onClose={() => setManageOpen(false)}
        onTasksChanged={(nextTasks) => setTasks(nextTasks)}
      />
      <CodingProfilesModal
        open={codingProfilesOpen}
        onClose={() => setCodingProfilesOpen(false)}
        onProfileUpdated={async () => {
          setLoadingContests(true);
          try {
            const [contestData, statsData] = await Promise.all([
              getUpcomingContests().catch(() => []),
              getCodingProfileStats().catch(() => null),
            ]);
            setContests(contestData);
            setProfileStats(statsData);
          } catch (err) {
            console.error("Failed to reload profile details", err);
          } finally {
            setLoadingContests(false);
          }
        }}
      />
    </div>
  );
}