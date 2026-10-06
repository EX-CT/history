import styles from './theme-toggle.module.css';

export const ThemeToggle = () => {
  return (
    <button
      type="button"
      className={styles.toggle}
      aria-label="Toggle dark mode"
      onClick={() => {
        // @ts-ignore — set by the inline theme script in _document
        const current = window?.__theme;
        // @ts-ignore
        window?.__setPreferredTheme(current === 'dark' ? 'light' : 'dark');
      }}
    >
      <span className={styles.track}>
        <svg className={styles.sun} viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
          <circle cx="12" cy="12" r="4.2" fill="currentColor"/>
          <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="12" y1="1.5" x2="12" y2="4"/>
            <line x1="12" y1="20" x2="12" y2="22.5"/>
            <line x1="1.5" y1="12" x2="4" y2="12"/>
            <line x1="20" y1="12" x2="22.5" y2="12"/>
            <line x1="4.2" y1="4.2" x2="6" y2="6"/>
            <line x1="18" y1="18" x2="19.8" y2="19.8"/>
            <line x1="4.2" y1="19.8" x2="6" y2="18"/>
            <line x1="18" y1="6" x2="19.8" y2="4.2"/>
          </g>
        </svg>
        <svg className={styles.moon} viewBox="0 0 24 24" width="13" height="13" aria-hidden="true">
          <path fill="currentColor" d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>
        </svg>
        <span className={styles.knob}/>
      </span>
    </button>
  );
};
