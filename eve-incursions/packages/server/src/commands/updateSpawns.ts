import {Spawn} from '../models/Spawn';
import {System} from '../models/System';
import {SpawnLog} from '../models/SpawnLog';
import {capitalize} from '../lib/utils';
import {InfluenceLogEntry} from '../models/InfluenceLogEntry';
import {In, Not} from 'typeorm';
import {redis} from '../lib/redis';
import {AppDataSource} from '../lib/data-source';
import {ensureConstellationData} from './ensureConstellationData';
import {esiRequest} from '../lib/esi';

interface APISpawns {
  constellation_id: number;
  faction_id: number;
  has_boss: boolean;
  infested_solar_systems: number[];
  influence: number;
  staging_solar_system_id: number;
  state: string;
  type: string

}

export interface SpawnChangeEvent {
  spawns: {
    id: number;
    securityArea: System["securityArea"];
    security: number;
    state: string;
    stagingSystemName: string;
    sovereigntyHolderId: number;
    regionName: string;
    constellationName: string;
    updatedAt: string;
  }[],
  influenceLogs: boolean
}

const handleSpawnChange = async (spawnIds: number[], influenceLogs: boolean) => {
  if (spawnIds.length === 0 && !influenceLogs) return;

  const spawns = await Spawn.find({where: {id: In(spawnIds)}});

  const eventSpawns: SpawnChangeEvent["spawns"] = [];
  for await (const spawn of spawns) {
    const stagingSystem = await spawn.stagingSystem;
    const constellation = await stagingSystem?.constellation;
    const region = await constellation?.region;

    if (!stagingSystem || !constellation || !region) continue;

    eventSpawns.push({
      id: spawn.id,
      security: stagingSystem.security,
      securityArea: stagingSystem.securityArea,
      constellationName: constellation.name,
      regionName: region.name,
      sovereigntyHolderId: stagingSystem.sovereigntyHolderID,
      stagingSystemName: stagingSystem.name,
      state: spawn.state,
      updatedAt: spawn.updatedAt.toISOString()
    })
  }

  const event: SpawnChangeEvent = {
    spawns: eventSpawns,
    influenceLogs
  }

  redis.publish('spawn.change', JSON.stringify(event)).then();
};

export const updateSpawns = async (doInfluenceLogs = false) => {
  const spawns = await esiRequest<APISpawns[]>('/incursions/');
  const changedSpawnIds: number[] = [];

  let changed = false;

  if (!Array.isArray(spawns)) return;

  await ensureConstellationData(spawns.map(s => s.constellation_id));

  await AppDataSource.manager.transaction(async manager => {
    const updatedSpawns = [];

    for await (const spawn of spawns) {
      let dbSpawn = await Spawn.findOne({where: {constellationId: spawn.constellation_id, active: true}});

      if (!dbSpawn) {
        dbSpawn = new Spawn();
        dbSpawn.constellationId = spawn.constellation_id;
        dbSpawn.active = true;
        dbSpawn.type = 0;
        dbSpawn.establishedAt = new Date();

        let stagingSystem = await System.findOne({where: {constellationId: spawn.constellation_id, type: 'Staging'}});

        if (!stagingSystem || stagingSystem.id !== spawn.staging_solar_system_id) {
          const newStagingSystem = await System.findOneBy({id: spawn.staging_solar_system_id});
          if (!newStagingSystem) return;

          newStagingSystem.type = 'Staging';
          await manager.save(newStagingSystem);

          if (stagingSystem) {
            stagingSystem.type = 'not known';
            await manager.save(stagingSystem);
          }

          stagingSystem = newStagingSystem;
        }
      }

      const oldState = dbSpawn.state ?? '';
      dbSpawn.influence = spawn.influence;
      dbSpawn.boss = spawn.has_boss;
      dbSpawn.state = capitalize(spawn.state);

      await manager.save(dbSpawn);

      updatedSpawns.push(dbSpawn.id);

      if (oldState.toLocaleLowerCase() !== spawn.state.toLocaleLowerCase()) {
        const spawnLog = new SpawnLog();
        spawnLog.spawnId = dbSpawn.id;
        spawnLog.date = new Date();
        spawnLog.state = capitalize(spawn.state);
        await manager.save(spawnLog);
        changed = true;
        changedSpawnIds.push(dbSpawn.id);
      }

      if (doInfluenceLogs) {
        const influenceLog = new InfluenceLogEntry();
        influenceLog.influence = spawn.influence;
        influenceLog.spawnId = dbSpawn.id;
        influenceLog.date = new Date();
        await manager.save(influenceLog);
        changed = true;
      }
    }

    const endedSpawns = await Spawn.find({where: {active: true, id: Not(In(updatedSpawns))}});

    for (const endedSpawn of endedSpawns) {
      changed = true;
      endedSpawn.state = 'Ended';
      endedSpawn.active = false;
      endedSpawn.endedAt = new Date();
      await manager.save(endedSpawn);

      changedSpawnIds.push(endedSpawn.id);

      const endedSpawnLog = new SpawnLog();
      endedSpawnLog.state = 'Ended';
      endedSpawnLog.date = new Date();
      endedSpawnLog.spawnId = endedSpawn.id;
      await manager.save(endedSpawnLog);
    }

  });

  if (changed) await redis.del('spawns');
  await handleSpawnChange(changedSpawnIds, doInfluenceLogs);
};
