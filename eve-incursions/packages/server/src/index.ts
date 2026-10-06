import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";
import {buildSchema} from 'type-graphql';
import {SpawnResolver} from './resolvers/SpawnResolver';
import waitPort from 'wait-port';
import {CommunityResolver} from './resolvers/CommunityResolver';
import {SpawnLogResolver} from './resolvers/SpawnLogResolver';
import {RatResolver} from './resolvers/RatResolver';
import {AppDataSource} from './lib/data-source';

async function main() {
  await waitPort({host: process.env.MYSQL_HOST, port: 3306});
  await AppDataSource.initialize();
  const schema = await buildSchema({
    resolvers: [SpawnResolver, CommunityResolver, SpawnLogResolver, RatResolver]
  })
  const server = new ApolloServer({ schema })
  const { url } = await startStandaloneServer(server, { listen: { port: 4001 } });
  console.log(`Server has started at ${url}`)
}

main().catch(e => console.error(e));
