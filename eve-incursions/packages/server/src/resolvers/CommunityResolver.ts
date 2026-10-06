import {Resolver, Query} from 'type-graphql';
import {Community} from '../models/Community';

@Resolver()
export class CommunityResolver {
  @Query(() => [Community])
  activeCommunities() {
    return Community.find({where: {active: true}, order: {name: 'ASC'}});
  }
}
