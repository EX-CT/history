import styles from '../styles/prose.module.css';

export default function Blog() {
  return (
    <div className={styles.prose}>
      <h1>Outage</h1>
      <p>Because of a fire in the data center of the french server provider OVH eve-incursions.de was down for about a day. Since I had a pretty fresh backup almost no data was lost and the service should be back to normal.</p>
      <p>Some of the features on the site are currently missing. I had planned to rewrite some of the code for some time and took this event to make that happen, but I could not get all the systems reimplemented in time. I will be adding the missing features at a later date.</p>
    </div>
  );
}
