import {BaseEntity, Column, Entity, OneToMany, PrimaryColumn} from 'typeorm';
import {Field, ID, ObjectType} from 'type-graphql';
import {Constellation} from './Constellation';

@Entity({
  name: 'mapregions'
})
@ObjectType()
export class Region extends BaseEntity {
  @Field(() => ID)
  @PrimaryColumn({name: 'regionID'})
  id: number;

  @Field(() => String)
  @Column({name: 'regionName'})
  name: string;

  @OneToMany(() => Constellation, c => c.region)
  constellations: Promise<Constellation[]>;
}
