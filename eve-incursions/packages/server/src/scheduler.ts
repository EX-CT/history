import {scheduleJob} from 'node-schedule';
import {updateSpawns} from './commands/updateSpawns';
import waitPort from 'wait-port';
import {updateSovereignty} from './commands/updateSovereignty';
import {AppDataSource} from './lib/data-source';

waitPort({host: process.env.MYSQL_HOST, port: 3306}).then(async () => {
  await AppDataSource.initialize();

  scheduleJob('5,10,15,20,25,30,35,40,45,50,55 * * * *', async () => {
    await updateSpawns();
  });

  scheduleJob('0 * * * *', async () => {
    await updateSpawns(true);
  });

  scheduleJob('30 * * * *', async () => {
    await updateSovereignty();
  });
}).catch(e => console.error(e));



