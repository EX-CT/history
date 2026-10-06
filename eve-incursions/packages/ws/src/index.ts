import { WebSocketServer } from 'ws';
import Redis from 'ioredis';

const wss = new WebSocketServer({ port: 4003 });
const redis = new Redis({host: 'redis'});

redis.subscribe('spawn.change').then(() => {
  redis.on('message', async (channel) => {
    if (channel !== 'spawn.change') return;

    const clients = wss.clients.values();
    for (const client of clients) {
      client.send("spawn.change");
    }
  });
});
