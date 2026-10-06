import { GraphQLClient, RequestOptions } from 'graphql-request';
import gql from 'graphql-tag';
export type Maybe<T> = T | null;
export type InputMaybe<T> = Maybe<T>;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
export type MakeEmpty<T extends { [key: string]: unknown }, K extends keyof T> = { [_ in K]?: never };
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
type GraphQLClientRequestHeaders = RequestOptions['requestHeaders'];
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
  ID: { input: string; output: string; }
  String: { input: string; output: string; }
  Boolean: { input: boolean; output: boolean; }
  Int: { input: number; output: number; }
  Float: { input: number; output: number; }
  DateTimeISO: { input: any; output: any; }
};

export type Community = {
  __typename?: 'Community';
  active: Scalars['Boolean']['output'];
  as: Scalars['Boolean']['output'];
  channel: Scalars['String']['output'];
  hq: Scalars['Boolean']['output'];
  id: Scalars['ID']['output'];
  language: Scalars['String']['output'];
  name: Scalars['String']['output'];
  tag: Scalars['String']['output'];
  tank: Scalars['String']['output'];
  timezone: Scalars['String']['output'];
  vg: Scalars['Boolean']['output'];
};

export type Constellation = {
  __typename?: 'Constellation';
  id: Scalars['ID']['output'];
  name: Scalars['String']['output'];
  region: Region;
  spawns: Array<Spawn>;
  systems: Array<System>;
};

export type DamageTypes = {
  __typename?: 'DamageTypes';
  em: Scalars['Float']['output'];
  explosive: Scalars['Float']['output'];
  kinetic: Scalars['Float']['output'];
  thermal: Scalars['Float']['output'];
};

export type Ewar = {
  __typename?: 'Ewar';
  id: Scalars['Float']['output'];
  name: Scalars['String']['output'];
  values: Array<EwarValues>;
};

export type EwarValues = {
  __typename?: 'EwarValues';
  name: Scalars['String']['output'];
  unit?: Maybe<Scalars['String']['output']>;
  value: Scalars['Float']['output'];
};

export type Hp = {
  __typename?: 'HP';
  armor: Scalars['Float']['output'];
  shield: Scalars['Float']['output'];
  structure: Scalars['Float']['output'];
  total: Scalars['Float']['output'];
};

export type InfluenceLogEntry = {
  __typename?: 'InfluenceLogEntry';
  date: Scalars['DateTimeISO']['output'];
  id: Scalars['ID']['output'];
  influence: Scalars['Float']['output'];
  spawn: Spawn;
};

export type LastHsSpawn = {
  __typename?: 'LastHsSpawn';
  date?: Maybe<Scalars['DateTimeISO']['output']>;
};

export type PaginatedSpawnLogResponse = {
  __typename?: 'PaginatedSpawnLogResponse';
  hasMore: Scalars['Boolean']['output'];
  items: Array<SpawnLog>;
  total: Scalars['Int']['output'];
};

export type Query = {
  __typename?: 'Query';
  activeCommunities: Array<Community>;
  activeSpawns: Array<Spawn>;
  lastHighSecSpawn: LastHsSpawn;
  ratGroups: Array<RatGroup>;
  spawnLogs: PaginatedSpawnLogResponse;
  spawns: Array<Spawn>;
};


export type QuerySpawnLogsArgs = {
  page?: Scalars['Int']['input'];
};

export type Rat = {
  __typename?: 'Rat';
  armorResistances: DamageTypes;
  attackAlpha?: Maybe<Scalars['Float']['output']>;
  attackDuration?: Maybe<Scalars['Float']['output']>;
  attackMultiplier?: Maybe<Scalars['Float']['output']>;
  attackRange?: Maybe<Scalars['Float']['output']>;
  attackType?: Maybe<Scalars['String']['output']>;
  attackTypeId?: Maybe<Scalars['Float']['output']>;
  attackTypes: DamageTypes;
  chaseSpeed: Scalars['Float']['output'];
  ehp: Hp;
  ewar: Array<Ewar>;
  graphicId: Scalars['Float']['output'];
  groupId: Scalars['Float']['output'];
  hp: Hp;
  id: Scalars['Float']['output'];
  name: Scalars['String']['output'];
  orbitRange: Scalars['Float']['output'];
  orbitSpeed: Scalars['Float']['output'];
  scanResolution: Scalars['Float']['output'];
  shieldResistances: DamageTypes;
  signatureRadius: Scalars['Float']['output'];
  structureResistances: DamageTypes;
};

export type RatGroup = {
  __typename?: 'RatGroup';
  id: Scalars['ID']['output'];
  name: Scalars['String']['output'];
  rats: Array<Rat>;
};

export type Region = {
  __typename?: 'Region';
  id: Scalars['ID']['output'];
  name: Scalars['String']['output'];
};

export type Spawn = {
  __typename?: 'Spawn';
  active: Scalars['Boolean']['output'];
  boss: Scalars['Boolean']['output'];
  constellation: Constellation;
  endedAt?: Maybe<Scalars['DateTimeISO']['output']>;
  establishedAt: Scalars['DateTimeISO']['output'];
  id: Scalars['ID']['output'];
  influence: Scalars['Float']['output'];
  influenceLogArray: Array<Scalars['Float']['output']>;
  influenceLogs: Array<InfluenceLogEntry>;
  lastStateChangeDate: Scalars['DateTimeISO']['output'];
  logs: Array<SpawnLog>;
  stagingSystem: System;
  state: Scalars['String']['output'];
};

export type SpawnLog = {
  __typename?: 'SpawnLog';
  date: Scalars['DateTimeISO']['output'];
  id: Scalars['ID']['output'];
  spawn: Spawn;
  state: Scalars['String']['output'];
};

export type Station = {
  __typename?: 'Station';
  hasRepairService: Scalars['Boolean']['output'];
  id: Scalars['ID']['output'];
  name: Scalars['String']['output'];
};

export type System = {
  __typename?: 'System';
  constellation: Constellation;
  hasRepairStation: Scalars['Boolean']['output'];
  id: Scalars['ID']['output'];
  isIsland: Scalars['Boolean']['output'];
  name: Scalars['String']['output'];
  security: Scalars['Float']['output'];
  securityArea: Scalars['String']['output'];
  size: Scalars['Float']['output'];
  sovereigntyHolderID: Scalars['Float']['output'];
  sovereigntyHolderName: Scalars['String']['output'];
  stations: Array<Station>;
  type: Scalars['String']['output'];
};

export type ActiveCommunitiesQueryVariables = Exact<{ [key: string]: never; }>;


export type ActiveCommunitiesQuery = { __typename?: 'Query', activeCommunities: Array<{ __typename?: 'Community', name: string, tag: string, channel: string, language: string, tank: string, timezone: string, hq: boolean, as: boolean, vg: boolean }> };

export type SpawnLogsQueryVariables = Exact<{
  page?: InputMaybe<Scalars['Int']['input']>;
}>;


export type SpawnLogsQuery = { __typename?: 'Query', spawnLogs: { __typename?: 'PaginatedSpawnLogResponse', total: number, items: Array<{ __typename?: 'SpawnLog', state: string, date: any, spawn: { __typename?: 'Spawn', constellation: { __typename?: 'Constellation', name: string, region: { __typename?: 'Region', name: string } }, stagingSystem: { __typename?: 'System', name: string, sovereigntyHolderID: number, sovereigntyHolderName: string } } }> } };

export type ActiveSpawnsQueryVariables = Exact<{ [key: string]: never; }>;


export type ActiveSpawnsQuery = { __typename?: 'Query', activeSpawns: Array<{ __typename?: 'Spawn', state: string, id: string, influence: number, boss: boolean, establishedAt: any, endedAt?: any | null, influenceLogArray: Array<number>, lastStateChangeDate: any, stagingSystem: { __typename?: 'System', sovereigntyHolderID: number, sovereigntyHolderName: string, name: string, security: number, securityArea: string }, constellation: { __typename?: 'Constellation', name: string, region: { __typename?: 'Region', name: string }, systems: Array<{ __typename?: 'System', name: string, size: number, security: number, type: string, securityArea: string, stations: Array<{ __typename?: 'Station', hasRepairService: boolean, name: string }> }> } }>, lastHighSecSpawn: { __typename?: 'LastHsSpawn', date?: any | null } };

export type RatGroupsQueryVariables = Exact<{ [key: string]: never; }>;


export type RatGroupsQuery = { __typename?: 'Query', ratGroups: Array<{ __typename?: 'RatGroup', id: string, name: string, rats: Array<{ __typename?: 'Rat', name: string, graphicId: number, attackType?: string | null, attackAlpha?: number | null, attackMultiplier?: number | null, attackDuration?: number | null, attackTypeId?: number | null, attackRange?: number | null, orbitRange: number, orbitSpeed: number, chaseSpeed: number, signatureRadius: number, scanResolution: number, hp: { __typename?: 'HP', total: number, shield: number, structure: number, armor: number }, ehp: { __typename?: 'HP', total: number, shield: number, structure: number, armor: number }, attackTypes: { __typename?: 'DamageTypes', kinetic: number, thermal: number, em: number, explosive: number }, shieldResistances: { __typename?: 'DamageTypes', kinetic: number, thermal: number, em: number, explosive: number }, armorResistances: { __typename?: 'DamageTypes', kinetic: number, thermal: number, em: number, explosive: number }, structureResistances: { __typename?: 'DamageTypes', kinetic: number, thermal: number, em: number, explosive: number }, ewar: Array<{ __typename?: 'Ewar', id: number, name: string, values: Array<{ __typename?: 'EwarValues', name: string, value: number, unit?: string | null }> }> }> }> };


export const ActiveCommunitiesDocument = gql`
    query activeCommunities {
  activeCommunities {
    name
    tag
    channel
    language
    tank
    timezone
    hq
    as
    vg
  }
}
    `;
export const SpawnLogsDocument = gql`
    query spawnLogs($page: Int) {
  spawnLogs(page: $page) {
    items {
      state
      date
      spawn {
        constellation {
          name
          region {
            name
          }
        }
        stagingSystem {
          name
          sovereigntyHolderID
          sovereigntyHolderName
        }
      }
    }
    total
  }
}
    `;
export const ActiveSpawnsDocument = gql`
    query activeSpawns {
  activeSpawns {
    state
    id
    influence
    boss
    establishedAt
    endedAt
    influenceLogArray
    lastStateChangeDate
    stagingSystem {
      sovereigntyHolderID
      sovereigntyHolderName
      name
      security
      securityArea
    }
    constellation {
      name
      region {
        name
      }
      systems {
        name
        size
        security
        type
        securityArea
        name
        stations {
          hasRepairService
          name
        }
      }
    }
  }
  lastHighSecSpawn {
    date
  }
}
    `;
export const RatGroupsDocument = gql`
    query ratGroups {
  ratGroups {
    id
    name
    rats {
      name
      graphicId
      hp {
        total
        shield
        structure
        armor
      }
      ehp {
        total
        shield
        structure
        armor
      }
      attackType
      attackAlpha
      attackMultiplier
      attackDuration
      attackTypeId
      attackTypes {
        kinetic
        thermal
        em
        explosive
      }
      shieldResistances {
        kinetic
        thermal
        em
        explosive
      }
      armorResistances {
        kinetic
        thermal
        em
        explosive
      }
      structureResistances {
        kinetic
        thermal
        em
        explosive
      }
      attackRange
      orbitRange
      orbitSpeed
      chaseSpeed
      signatureRadius
      scanResolution
      ewar {
        id
        name
        values {
          name
          value
          unit
        }
      }
    }
  }
}
    `;

export type SdkFunctionWrapper = <T>(action: (requestHeaders?:Record<string, string>) => Promise<T>, operationName: string, operationType?: string, variables?: any) => Promise<T>;


const defaultWrapper: SdkFunctionWrapper = (action, _operationName, _operationType, _variables) => action();

export function getSdk(client: GraphQLClient, withWrapper: SdkFunctionWrapper = defaultWrapper) {
  return {
    activeCommunities(variables?: ActiveCommunitiesQueryVariables, requestHeaders?: GraphQLClientRequestHeaders, signal?: RequestInit['signal']): Promise<ActiveCommunitiesQuery> {
      return withWrapper((wrappedRequestHeaders) => client.request<ActiveCommunitiesQuery>({ document: ActiveCommunitiesDocument, variables, requestHeaders: { ...requestHeaders, ...wrappedRequestHeaders }, signal }), 'activeCommunities', 'query', variables);
    },
    spawnLogs(variables?: SpawnLogsQueryVariables, requestHeaders?: GraphQLClientRequestHeaders, signal?: RequestInit['signal']): Promise<SpawnLogsQuery> {
      return withWrapper((wrappedRequestHeaders) => client.request<SpawnLogsQuery>({ document: SpawnLogsDocument, variables, requestHeaders: { ...requestHeaders, ...wrappedRequestHeaders }, signal }), 'spawnLogs', 'query', variables);
    },
    activeSpawns(variables?: ActiveSpawnsQueryVariables, requestHeaders?: GraphQLClientRequestHeaders, signal?: RequestInit['signal']): Promise<ActiveSpawnsQuery> {
      return withWrapper((wrappedRequestHeaders) => client.request<ActiveSpawnsQuery>({ document: ActiveSpawnsDocument, variables, requestHeaders: { ...requestHeaders, ...wrappedRequestHeaders }, signal }), 'activeSpawns', 'query', variables);
    },
    ratGroups(variables?: RatGroupsQueryVariables, requestHeaders?: GraphQLClientRequestHeaders, signal?: RequestInit['signal']): Promise<RatGroupsQuery> {
      return withWrapper((wrappedRequestHeaders) => client.request<RatGroupsQuery>({ document: RatGroupsDocument, variables, requestHeaders: { ...requestHeaders, ...wrappedRequestHeaders }, signal }), 'ratGroups', 'query', variables);
    }
  };
}
export type Sdk = ReturnType<typeof getSdk>;