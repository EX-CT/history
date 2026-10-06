import {BaseEntity, Column, Entity, JoinColumn, ManyToOne, PrimaryGeneratedColumn} from 'typeorm';
import {Field, Float, ID, ObjectType} from 'type-graphql';
import {Spawn} from './Spawn';

@Entity({
  name: 'spawn_influence_logs'
})
@ObjectType()
export class InfluenceLogEntry extends BaseEntity {
  @Field(() => ID)
  @PrimaryGeneratedColumn()
  id: number;

  @Field(() => Float)
  @Column({type: "float"})
  influence: number;

  @Field(() => Date)
  @Column()
  date: Date;

  @Column({name: 'spawn_id'})
  spawnId: number;

  @Field(() => Spawn)
  @ManyToOne(() => Spawn, spawn => spawn.influenceLogs)
  @JoinColumn({name: 'spawn_id'})
  spawn: Promise<Spawn>;
}
