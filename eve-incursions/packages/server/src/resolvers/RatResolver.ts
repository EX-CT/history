import {Query, Resolver} from 'type-graphql';
import {RatGroup} from '../models/Rats';

@Resolver()
export class RatResolver {
  @Query(() => [RatGroup])
  ratGroups() {
    return RatGroup.find({order: {id: 'DESC'}});
  }
}
