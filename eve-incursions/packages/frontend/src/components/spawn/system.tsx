import {useState} from 'react';
import {ActiveSpawnsQuery} from '../../lib/graphql';
import {classNames, dotlanTransform} from '../../lib/utils';
import styles from './systems.module.css';

export const System = ({system}: { system: ActiveSpawnsQuery['activeSpawns'][0]['constellation']['systems'][0] }) => {
  const [open, setOpen] = useState(false);
  const hasStations = system.stations.length > 0;

  return (
    <>
      <tr className={classNames(styles.row, open && styles.rowOpen)}>
        <td className={styles.toggleCell}>
          {hasStations && (
            <button
              className={classNames(styles.toggle, open && styles.toggleOpen)}
              onClick={() => setOpen(o => !o)}
              aria-label={open ? 'Hide stations' : 'Show stations'}
              aria-expanded={open}
            >
              <svg className={styles.chev} viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                <path d="M9 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          )}
        </td>
        <td>
          <a href={`https://evemaps.dotlan.net/system/${dotlanTransform(system.name)}`} target="_blank" rel="noopener">{system.name}</a>
        </td>
        <td className={classNames(styles.num, 'sec', `sec-${system.securityArea}`)}>{system.security}</td>
        <td className={styles.num}>{system.size} AU</td>
      </tr>
      {hasStations && (
        <tr className={styles.stationsRow}>
          <td colSpan={4}>
            <div className={classNames(styles.stationsWrap, open && styles.stationsOpen)}>
              <div className={styles.stationsInner}>
                <div className={styles.stations}>
                  {system.stations.map(station => (
                    <div className={styles.station} key={station.name}>
                      {station.hasRepairService && <img className={styles.wrench} src="/images/wrench.png" alt="Repair"/>}
                      <span>{station.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
};
