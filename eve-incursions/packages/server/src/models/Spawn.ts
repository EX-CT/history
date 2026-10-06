import {BaseEntity, Column, CreateDateColumn, Entity, ManyToOne, OneToMany, PrimaryGeneratedColumn, UpdateDateColumn} from 'typeorm';
import {Field, Float, ID, ObjectType} from 'type-graphql';
import {Constellation} from './Constellation';
import {System} from './System';
import {InfluenceLogEntry} from './InfluenceLogEntry';
import {SpawnLog} from './SpawnLog';
import {AppDataSource} from '../lib/data-source';

@Entity({
  name: 'spawns'
})
@ObjectType()
export class Spawn extends BaseEntity {
  @Field(() => ID)
  @PrimaryGeneratedColumn()
  id: number;

  @Field(() => String)
  @Column({})
  state: string;

  @Field(() => Boolean)
  @Column({})
  active: boolean;

  @Field(() => Boolean)
  @Column({name: 'hasBoss'})
  boss: boolean;

  @Field(() => Date)
  @Column({name: 'established_at'})
  establishedAt: Date;

  @Field(() => Date, {nullable: true})
  @Column({name: 'ended_at'})
  endedAt: Date;

  @Field(() => Number)
  @Column({type: "float"})
  influence: number;

  @Column()
  constellationId: number;

  @CreateDateColumn({name: 'created_at'})
  createdAt: Date;

  @UpdateDateColumn({name: 'updated_at'})
  updatedAt: Date;

  @Column()
  type: number;

  @Field(() => Constellation)
  @ManyToOne(() => Constellation, c => c.spawns, {lazy: true})
  constellation: Promise<Constellation>;

  @Field(() => [InfluenceLogEntry])
  @OneToMany(() => InfluenceLogEntry, il => il.spawn, {lazy: true})
  influenceLogs: Promise<InfluenceLogEntry[]>;

  @Field(() => [SpawnLog])
  @OneToMany(() => SpawnLog, sl => sl.spawn, {lazy: true})
  logs: Promise<SpawnLog[]>;

  @Field(() => System)
  get stagingSystem() {
    return this.setStagingSystem();
  }

  private async setStagingSystem() {
    const constellation = await this.constellation;
    const systems = await constellation.systems;
    for (const system of systems ?? []) {
      if (system.type === 'Staging') {
        return system;
      }
    }
  }

  @Field(() => [Float])
  get influenceLogArray(): Promise<number[]> {
    return (async () => {
      const maxEntries = 72;

      const influenceLogs = await AppDataSource.manager.find(InfluenceLogEntry, {
        where: {spawn: {id: this.id}},
        order: {date: 'DESC'},
        take: maxEntries
      });

      const missing = maxEntries - influenceLogs.length;
      const filler = missing ? (Array(missing).fill(0)) : [];
      return [...filler, ...influenceLogs.map(i => i.influence * 100).reverse()] as number[];
    })();
  }

  @Field(() => Date)
  get lastStateChangeDate(): Promise<Date | undefined> {
    return (async () => {
      const lastSpawnLog = await AppDataSource.manager.findOne(SpawnLog, {
        where: {spawn: {id: this.id}},
        order: {date: 'DESC'}
      });

      return lastSpawnLog?.date ?? new Date();
    })();
  }
}
