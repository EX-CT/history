import Link from 'next/link';
import {useRouter} from 'next/router';
import {useState} from 'react';
import {ThemeToggle} from '../theme-toggle/theme-toggle';
import {classNames} from '../../lib/utils';
import styles from './Nav.module.css';

const links = [
  {href: '/', label: 'Status'},
  {href: '/history', label: 'History'},
  {href: '/communities', label: 'Communities'},
  {href: '/rats', label: 'Rats'},
  {href: '/about', label: 'About'},
];

export const Nav = () => {
  const [open, setOpen] = useState(false);
  const {pathname} = useRouter();
  const close = () => setOpen(false);

  return (
    <header className={styles.header}>
      <div className={classNames('container', styles.bar)}>
        <Link href="/" className={styles.brand} onClick={close}>
          <img src="/images/logo.svg" className={styles.logo} alt=""/>
          <span>EVE&#8209;Incursions</span>
        </Link>

        <button
          className={styles.burger}
          aria-label="Toggle navigation"
          aria-expanded={open}
          onClick={() => setOpen(o => !o)}
        >
          <span className={classNames(styles.burgerLines, open && styles.burgerOpen)}/>
        </button>

        <nav className={classNames(styles.nav, open && styles.navOpen)}>
          {links.map(link => (
            <Link
              key={link.href}
              href={link.href}
              onClick={close}
              className={classNames(styles.link, pathname === link.href && styles.active)}
            >
              {link.label}
            </Link>
          ))}
          <div className={styles.toggleWrap}>
            <ThemeToggle/>
          </div>
        </nav>
      </div>
    </header>
  );
};
