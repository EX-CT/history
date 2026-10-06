import {MoreThan} from 'typeorm';
import {Spawn} from '../models/Spawn';

export const calculateHSSpawn = async () => {
  const spawns = await Spawn.find({where: {establishedAt: MoreThan<any>('2020-01-01')}, order: {establishedAt: 'ASC'}});

  let lastDate: Date | null = null;
  const diffs = [];
  for await (const spawn of spawns) {
    const staging = await spawn.stagingSystem;
    if (!staging || staging.security < 0.5) continue;

    if (lastDate !== null) {
      diffs.push((spawn.establishedAt.getTime() - lastDate.getTime()) / (1000 * 3600));
    }
    lastDate = spawn.endedAt;
  }

  console.log('min', Math.min(...diffs));
  console.log('max', Math.max(...diffs));
  console.log('avg', diffs.reduce((c, v) => c + v, 0) / diffs.length);
}
