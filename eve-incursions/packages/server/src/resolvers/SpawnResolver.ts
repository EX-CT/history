import {Query, Resolver, UseMiddleware} from 'type-graphql';
import {Spawn} from '../models/Spawn';
import {LastHsSpawn} from '../models/LastHsSpawn';
import {getRepository} from 'typeorm';

@Resolver()
export class SpawnResolver {
  @Query(() => [Spawn])
  spawns() {
    return Spawn.find({take: 10});
  }

  @Query(() => [Spawn])
  activeSpawns() {
    return Spawn.find({where: {active: true}});
  }

  @Query(() => LastHsSpawn)
  async lastHighSecSpawn() {
    let date = null;
    const hasActiveHSSpawn = await Spawn
      .createQueryBuilder('spawn')
      .leftJoin("spawn.constellation", "constellation")
      .leftJoin("constellation.systems", "system")
      .where("ROUND(system.security, 1) >= 0.5")
      .andWhere("system.type = 'Staging'")
      .andWhere("spawn.active = 1")
      .getCount();

    console.log(hasActiveHSSpawn)

    if (hasActiveHSSpawn === 0) {
      const lastSpawn = await Spawn
        .createQueryBuilder('spawn')
        .select("spawn.endedAt")
        .leftJoin("spawn.constellation", "constellation")
        .leftJoin("constellation.systems", "system")
        .where("ROUND(system.security, 1) >= 0.5")
        .andWhere("system.type = 'Staging'")
        .andWhere("spawn.active = 0")
        .orderBy("spawn.endedAt", "DESC")
        .getOne();
      date = lastSpawn?.endedAt;
    }

    return {date};
  }
}
