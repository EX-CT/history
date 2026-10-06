import {GraphQLClient} from 'graphql-request';
import {ActiveSpawnsQuery, getSdk} from '../lib/graphql';
import {Spawn} from '../components/spawn/spawn';
import {LastHsSpawn} from '../components/spawn/lastHsSpawn';
import {redis} from '../lib/redis';
import {useRouter} from 'next/router';
import useWebSocket from 'react-use-websocket';
import styles from '../styles/home.module.css';

export const getServerSideProps = async () => {
  const cache = await redis.get('spawns');
  if (cache !== null && (!process.env.NODE_ENV || process.env.NODE_ENV !== 'development')) {
    return {props: JSON.parse(cache)};
  } else {
    const client = new GraphQLClient('http://server:4001');
    const sdk = getSdk(client);
    const {activeSpawns, lastHighSecSpawn} = await sdk.activeSpawns();

    await redis.set('spawns', JSON.stringify({activeSpawns, lastHighSecSpawn}));

    return {props: {activeSpawns, lastHighSecSpawn}};
  }
};


export default function Home({activeSpawns, lastHighSecSpawn: {date}}: ActiveSpawnsQuery) {
  const router = useRouter();
  const {} = useWebSocket(typeof window === "undefined" ? null : `wss://${window?.location.host}/ws`, {
    onMessage: (e) => {
      console.log(e.data)
      router.replace(router.asPath);
    }
  });

  return (
    <>
      <LastHsSpawn date={date} />
      <div className={styles.grid}>{
        [...activeSpawns].sort((s1, s2) => s2.stagingSystem.security - s1.stagingSystem.security).map((spawn) => {
          return (<Spawn key={spawn.id} spawn={spawn}/>);
        })
      }</div>
    </>
  );
}

