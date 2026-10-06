import {Rat} from '../../lib/graphql';
import {DamageTypesRow} from './DamageTypesRow';
import {classNames} from '../../lib/utils';
import styles from './rats.module.css';

type DefenseProps = Pick<Rat, 'hp' | 'ehp' | 'armorResistances' | 'shieldResistances' | 'structureResistances'>

const Layer = ({label, hp, ehp, resistances}: { label: string; hp: number; ehp: number; resistances?: any }) => (
  <div className={styles.statRow}>
    <span className={styles.statLabel}>{label}</span>
    <span className={styles.statValue}>
      <span className={classNames(styles.badge, styles.hp)} title="HP">{hp.toLocaleString()}</span>
      <span className={classNames(styles.badge, styles.ehp, 'hidden-xs')} title="EHP">{ehp.toLocaleString([], {maximumFractionDigits: 1})}</span>
    </span>
    {resistances ? <DamageTypesRow damageTypes={resistances}/> : <div/>}
  </div>
);

export const Defense = ({hp, ehp, armorResistances, shieldResistances, structureResistances}: DefenseProps) => {
  return (
    <div className={styles.statSection}>
      <Layer label="Shield" hp={hp.shield} ehp={ehp.shield} resistances={shieldResistances}/>
      <Layer label="Armor" hp={hp.armor} ehp={ehp.armor} resistances={armorResistances}/>
      <Layer label="Structure" hp={hp.structure} ehp={ehp.structure} resistances={structureResistances}/>
      <Layer label="Total" hp={hp.total} ehp={ehp.total}/>
    </div>
  );
};
