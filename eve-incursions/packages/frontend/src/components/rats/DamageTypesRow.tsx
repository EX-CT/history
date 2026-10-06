import {DamageTypes as DamageTypesI} from '../../lib/graphql';
import {DamageTypeCol} from './DamageTypeCol';
import styles from './rats.module.css';

export type DamageTypes = Omit<DamageTypesI, '__typename'>;
interface DamageTypesProps {
  damageTypes: DamageTypes;
  total?: number;
}

export const DamageTypesRow = ({damageTypes, total}: DamageTypesProps) => {
  const types: (keyof DamageTypes)[] = ['em', 'thermal', 'kinetic', 'explosive'];
  return (
    <div className={styles.bars}>
      {types.map((type) => {
        const value = damageTypes[type] ?? 0;
        const label = total ? value.toLocaleString([], {maximumFractionDigits: 1}) + ' hp' : (value * 100).toLocaleString([], {maximumFractionDigits: 1}) + ' %';
        const percentage = total ? value / total : value;
        return (<DamageTypeCol type={type} key={type} label={label} percentage={percentage}/>);
      })}
    </div>
  );
};
