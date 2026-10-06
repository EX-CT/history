import {BaseEntity, Column, Entity, JoinColumn, ManyToOne, PrimaryGeneratedColumn} from 'typeorm';
import {Field, ID, ObjectType} from 'type-graphql';
import {Spawn} from './Spawn';

@Entity({
  name: 'spawn_logs'
})
@ObjectType()
export class SpawnLog extends BaseEntity {
  @Field(() => ID)
  @PrimaryGeneratedColumn()
  id: number;

  @Field(() => String)
  @Column()
  state: string;

  @Field(() => Date)
  @Column()
  date: Date;

  @Column({name: 'spawn_id'})
  spawnId: number;

  @Field(() => Spawn)
  @ManyToOne(() => Spawn, c => c.logs)
  @JoinColumn({name: 'spawn_id'})
  spawn: Promise<Spawn>;
}
