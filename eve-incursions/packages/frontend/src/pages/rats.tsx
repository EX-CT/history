import {GraphQLClient} from 'graphql-request';
import {getSdk, RatGroupsQuery} from '../lib/graphql';
import {Rat} from '../components/rats/Rat';
import styles from '../components/rats/rats.module.css';

export const getStaticProps = async () => {
  const client = new GraphQLClient('http://server:4001');
  const sdk = getSdk(client);
  const {ratGroups} = await sdk.ratGroups();

  return {props: {ratGroups}};
};


export default function Rats({ratGroups}: RatGroupsQuery) {
  return (
    <>
      <h1>Sansha Rats</h1>
      {ratGroups.map(({name, rats}) => {
        const sorted = [...rats].sort((r1, r2) => r1.name.localeCompare(r2.name));
        return (
          <section key={name}>
            <h2 className={styles.groupTitle}>{name}</h2>
            {sorted.map(rat => <Rat key={rat.name} rat={rat}/>)}
          </section>
        );
      })}
    </>
  );
}
