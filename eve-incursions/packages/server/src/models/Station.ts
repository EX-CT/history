import {AfterLoad, BaseEntity, Column, Entity, JoinColumn, ManyToOne, OneToMany, PrimaryGeneratedColumn} from 'typeorm';
import {Field, ID, ObjectType} from 'type-graphql';
import {System} from './System';
import {OperationService} from './OperationService';

@Entity({
  name: 'sta_stations'
})
@ObjectType()
export class Station extends BaseEntity {
  @Field(() => ID)
  @PrimaryGeneratedColumn({name: 'stationID'})
  id: string;

  @ManyToOne(() => System, system => system.stations)
  @JoinColumn({name: 'solarSystemID'})
  system: Promise<System>;

  @OneToMany(() => OperationService, os => os.station, {eager: true, lazy: true})
  operationServices: Promise<OperationService[]>;

  @Column({name: 'operationID'})
  operationID: number;

  @Field(() => String)
  @Column({name: 'stationName'})
  name: string;

  @Field(() => Boolean)
  hasRepairService: Promise<boolean>;

  @AfterLoad()
  private async setHasRepairService() {
    this.hasRepairService = OperationService.count({
      where: {
        operationId: this.operationID,
        serviceId: 4096
      }
    }).then(v => v > 0);
  }
}
