import {System} from '../models/System';
import {Constellation} from '../models/Constellation';
import {Region} from '../models/Region';
import {fetchConstellation, fetchRegion, fetchSystem} from '../lib/esi';
import {AppDataSource} from '../lib/data-source';

export const ensureConstellationData = async (constellationIds: number[]) => {
  const uniqueIds = [...new Set(constellationIds)];

  for (const constellationId of uniqueIds) {
    try {
      await ensureConstellation(constellationId);
    } catch (e) {
      console.error(`Failed to ensure constellation ${constellationId}:`, e);
    }
  }
};

async function ensureConstellation(constellationId: number) {
  let dbConstellation = await Constellation.findOneBy({id: constellationId});

  if (!dbConstellation) {
    const esiConstellation = await fetchConstellation(constellationId);

    await ensureRegion(esiConstellation.region_id);

    dbConstellation = new Constellation();
    dbConstellation.id = constellationId;
    dbConstellation.name = esiConstellation.name;
    dbConstellation.regionId = esiConstellation.region_id;
    await dbConstellation.save();

    console.log(`Created constellation: ${esiConstellation.name} (${constellationId})`);
  }

  const esiConstellation = await fetchConstellation(constellationId);

  await AppDataSource.manager.transaction(async manager => {
    for (const systemId of esiConstellation.systems) {
      try {
        const esiSystem = await fetchSystem(systemId);
        let dbSystem = await System.findOneBy({id: systemId});

        if (!dbSystem) {
          dbSystem = new System();
          dbSystem.id = systemId;
          dbSystem.name = esiSystem.name;
          dbSystem.constellationId = constellationId;
          dbSystem.sovereigntyHolderID = 0;
          dbSystem.sovereigntyHolderName = '';
          dbSystem.isIsland = false;
          dbSystem.size = 0;
          dbSystem.security = esiSystem.security_status;
          dbSystem.type = 'not known';
          console.log(`Created system: ${esiSystem.name} (${systemId}) sec=${esiSystem.security_status.toFixed(2)}`);
        } else {
          dbSystem.security = esiSystem.security_status;
          dbSystem.name = esiSystem.name;
        }

        await manager.save(dbSystem);
      } catch (e) {
        console.error(`Failed to fetch/save system ${systemId}:`, e);
      }
    }
  });
}

async function ensureRegion(regionId: number) {
  const existing = await Region.findOneBy({id: regionId});
  if (existing) return;

  const esiRegion = await fetchRegion(regionId);
  const region = new Region();
  region.id = regionId;
  region.name = esiRegion.name;
  await region.save();
  console.log(`Created region: ${esiRegion.name} (${regionId})`);
}
