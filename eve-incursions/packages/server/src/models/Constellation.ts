import {Entity, BaseEntity, PrimaryColumn, Column, ManyToOne, OneToMany, JoinColumn} from 'typeorm';
import { ObjectType, Field, ID } from "type-graphql";
import {Spawn} from './Spawn';
import {System} from './System';
import {Region} from './Region';

@Entity({
  name: 'mapconstellations'
})
@ObjectType()
export class Constellation extends BaseEntity {
  @Field(() => ID)
  @PrimaryColumn({name: 'constellationID'})
  id: number;

  @Field(() => String)
  @Column({name: 'constellationName'})
  name: string;

  @Column({name: 'regionID'})
  regionId: number;

  @Field(() => [Spawn])
  @OneToMany(() => Spawn, spawn => spawn.constellation)
  spawns: Promise<Spawn[]>;

  @Field(() => [System])
  @OneToMany(() => System, s => s.constellation, {lazy: true})
  systems: Promise<System[]>;

  @Field(() => Region)
  @ManyToOne(() => Region, r => r.constellations, {lazy: true})
  @JoinColumn({name: 'regionID'})
  region: Promise<Region>;
}
