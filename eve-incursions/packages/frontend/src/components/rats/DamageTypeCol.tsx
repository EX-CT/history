import styles from './rats.module.css';

interface DamageTypeProps {
  type: 'em' | 'kinetic' | 'explosive' | 'thermal';
  label: string;
  percentage: number;
}

export const DamageTypeCol = ({type, label, percentage}: DamageTypeProps) => {
  return (
    <div className={styles.barCol} data-type={type} title={type}>
      <img className={styles.resiIcon} src={`/images/${type}.png`} alt={type}/>
      <div className={styles.bar}>
        <div className={styles.fill} style={{width: Math.min(100, percentage * 100) + '%'}}/>
        <div className={styles.barText}>{label}</div>
      </div>
    </div>
  );
};
