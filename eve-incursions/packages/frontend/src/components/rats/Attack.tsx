import {Rat} from '../../lib/graphql';
import {DamageTypes, DamageTypesRow} from './DamageTypesRow';
import styles from './rats.module.css';

type AttackProps = Pick<Rat, 'attackAlpha' | 'attackType' | 'attackTypeId' | 'attackTypes' | 'attackDuration'>

export const Attack = ({attackTypes, attackAlpha, attackType, attackTypeId, attackDuration}: AttackProps) => {
  if (!attackAlpha || !attackDuration || !attackType) return null;
  const dps = attackAlpha / attackDuration;
  const dpsAttackTypes = Object.fromEntries(Object.entries(attackTypes as DamageTypes).map(([k, v]) => [k, v / attackDuration]));

  return (
    <div className={styles.statSection}>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>Alpha</span>
        <span className={styles.statValue} title="Alpha">
          <img src={`https://images.evetech.net/types/${attackTypeId}/icon?size=32`} alt={attackType} className={styles.icon}/>
          {attackAlpha.toLocaleString()}
        </span>
        <DamageTypesRow damageTypes={attackTypes} total={attackAlpha}/>
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>DPS</span>
        <span className={styles.statValue} title="DPS">
          <img src={`https://images.evetech.net/types/${attackTypeId}/icon?size=32`} alt={attackType} className={styles.icon}/>
          {dps.toLocaleString([], {maximumFractionDigits: 1})}
        </span>
        <DamageTypesRow damageTypes={dpsAttackTypes as DamageTypes} total={dps}/>
      </div>
    </div>
  );
};
