import {RatGroupsQuery} from '../../lib/graphql';
import styles from './rats.module.css';

export const Ewar = ({ewar}: { ewar: RatGroupsQuery['ratGroups'][0]['rats'][0]['ewar'] }) => {
  if (ewar.length === 0) return null;

  return (
    <span className={styles.ewar}>
      {ewar.map(({name, id, values}) => {
        const title = [name, ...values.map(({name, value, unit}) => `${name}: ${value.toLocaleString()}${unit ? ' ' + unit : ''}`)].join(' | ');
        return (
          <img src={`https://images.evetech.net/types/${id}/icon?size=32`} key={name} className={styles.icon} alt={name} title={title}/>
        );
      })}
    </span>
  );
};
