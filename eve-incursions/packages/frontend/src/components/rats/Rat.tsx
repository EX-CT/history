import {RatGroupsQuery} from '../../lib/graphql';
import {Ewar} from './Ewar';
import {Attack} from './Attack';
import {Defense} from './Defense';
import styles from './rats.module.css';

export const Rat = ({rat}: { rat: RatGroupsQuery["ratGroups"][0]["rats"][0] }) => {
  return (
    <article className={styles.card}>
      <h3 className={styles.name}>
        {rat.name}
        <Ewar ewar={rat.ewar}/>
      </h3>
      <div className={styles.body}>
        <img src={`/images/renders/256/${rat.graphicId}.jpg`} className={`${styles.render} hidden-xs`} alt={rat.name} title={rat.name}/>
        <div className={styles.stats}>
          <Attack attackTypes={rat.attackTypes} attackAlpha={rat.attackAlpha} attackType={rat.attackType} attackDuration={rat.attackDuration} attackTypeId={rat.attackTypeId}/>
          <Defense hp={rat.hp} ehp={rat.ehp} shieldResistances={rat.shieldResistances} armorResistances={rat.armorResistances} structureResistances={rat.structureResistances}/>
          <div className={styles.metaGrid}>
            <ul className={styles.metaList}>
              <li><span>Attack Range</span><b>{(rat.attackRange ?? 0).toLocaleString()} m</b></li>
              <li><span>Orbit Range</span><b>{rat.orbitRange.toLocaleString()} m</b></li>
              <li><span>Orbit Speed</span><b>{rat.orbitSpeed.toLocaleString()} m/s</b></li>
            </ul>
            <ul className={styles.metaList}>
              <li><span>Chase Speed</span><b>{rat.chaseSpeed.toLocaleString()} m/s</b></li>
              <li><span>Signature Radius</span><b>{rat.signatureRadius.toLocaleString()} m</b></li>
              <li><span>Scan Resolution</span><b>{rat.scanResolution.toLocaleString()} mm</b></li>
            </ul>
          </div>
        </div>
      </div>
    </article>
  );
};
