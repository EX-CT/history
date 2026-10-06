import styles from './RetirementNotice.module.css';

export const RetirementNotice = () => {
  return (
    <aside className={styles.notice} role="note">
      <span className={styles.tag}>Sunsetting</span>
      <p className={styles.text}>
        After many years, EVE&#8209;Incursions is being retired and will go offline later this year.
        It&rsquo;s no longer actively maintained &mdash; the source is open on{' '}
        <a className={styles.link} href="https://github.com/Shadowlauch/eve-incursions-node" target="_blank" rel="noopener noreferrer">GitHub</a>{' '}
        if you&rsquo;d like to run it yourself. Thanks to everyone who flew with it. <span className={styles.salute}>o7</span>
      </p>
    </aside>
  );
};
