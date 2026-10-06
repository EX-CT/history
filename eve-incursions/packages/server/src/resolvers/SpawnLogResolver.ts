import {Arg, Int, ObjectType, Query, Resolver} from 'type-graphql';
import {SpawnLog} from '../models/SpawnLog';
import {PaginatedResponse} from '../generic-types/PaginatedResponse.type';

@ObjectType()
class PaginatedSpawnLogResponse extends PaginatedResponse(SpawnLog) {
}

@Resolver()
export class SpawnLogResolver {
  @Query(() => PaginatedSpawnLogResponse)
  async spawnLogs(@Arg('page', () => Int, {defaultValue: 1}) page: number): Promise<PaginatedSpawnLogResponse> {
    const perPage = 20;
    const skip = perPage * (page - 1);

    const [data, count] = await SpawnLog.findAndCount({take: perPage, order: {date: 'DESC'}, skip});

    return {items: data, total: count, hasMore: true};
  }
}
