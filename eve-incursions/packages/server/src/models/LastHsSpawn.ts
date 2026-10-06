import {Field, ObjectType} from 'type-graphql';

@ObjectType()
export class LastHsSpawn {
  @Field({nullable: true})
  date: Date;
}
