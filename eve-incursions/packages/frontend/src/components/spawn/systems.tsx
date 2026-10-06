import {Fragment} from 'react';
import {ActiveSpawnsQuery} from '../../lib/graphql';
import {System} from './system';
import styles from './systems.module.css';

export const Systems = ({systems}: { systems: ActiveSpawnsQuery['activeSpawns'][0]['constellation']['systems'] }) => {
  const types = ['Staging', 'Vanguard', 'Assault', 'Headquarters', 'not known'];
  const sortedSystems = [...systems].sort((s1, s2) => types.indexOf(s1.type) - types.indexOf(s2.type));
  let lastType = '';

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th className={styles.toggleCol}/>
          <th>Name</th>
          <th className={styles.num}>Security</th>
          <th className={styles.num}>
            Size <abbr className={styles.hint} title="Approximation of the longest warp">(?)</abbr>
          </th>
        </tr>
      </thead>
      <tbody>
        {sortedSystems.map(system => {
          const showHeader = system.type !== lastType;
          lastType = system.type;
          return (
            <Fragment key={system.name}>
              {showHeader && (
                <tr className={styles.band}>
                  <td colSpan={4}>{system.type}</td>
                </tr>
              )}
              <System system={system}/>
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
};
