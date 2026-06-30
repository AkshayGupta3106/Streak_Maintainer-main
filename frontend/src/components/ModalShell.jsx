export default function ModalShell({ title, onClose, wide = false, narrow = false, children }) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className={`modal-panel ${wide ? 'modal-panel-wide' : narrow ? 'modal-panel-narrow' : ''}`}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">Streak Tracker</p>
            <h2>{title}</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close modal">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}