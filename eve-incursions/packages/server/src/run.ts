import "reflect-metadata";
import {updateSpawns} from './commands/updateSpawns';
import {updateSovereignty} from './commands/updateSovereignty';
import {updateRats} from './commands/updateRats';
import {calculateHSSpawn} from './commands/calculateHSSpawn';
import {redis} from './lib/redis';
import {updateSystems} from './commands/updateSystems';
import {AppDataSource} from './lib/data-source';

const run = async () => {
  await AppDataSource.initialize();

  if (process.argv.length < 3) {
    console.log('Not enough parameters');
  }

  const args = process.argv.slice(3);
  const command = process.argv[2];

  if (command === "updateSpawns") {
    const influenceLogs = args.indexOf('--influenceLogs') !== -1;
    await updateSpawns(influenceLogs);
  } else if (command === "updateSovereignty") {
    await updateSovereignty();
  } else if (command === "updateRats") {
    await updateRats();
  } else if (command === "calculateHSSpawn") {
    await calculateHSSpawn();
  } else if (command === "updateSystems") {
    await updateSystems();
  } else {
    console.log(`${command} not found`);
  }

  redis.disconnect();
  await AppDataSource.destroy();
};

run().catch(e => console.log(e));

