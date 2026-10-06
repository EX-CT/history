import {useEffect, useState} from 'react';

/** Tracks the current theme by observing the data-theme attribute on <html>. */
export function useTheme(): 'light' | 'dark' {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const el = document.documentElement;
    const read = () => setTheme(el.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');
    read();
    const obs = new MutationObserver(read);
    obs.observe(el, {attributes: true, attributeFilter: ['data-theme']});
    return () => obs.disconnect();
  }, []);

  return theme;
}
