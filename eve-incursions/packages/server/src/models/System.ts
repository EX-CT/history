import {BaseEntity, Column, Entity, ManyToOne, OneToMany, PrimaryColumn} from 'typeorm';
import {Field, ID, ObjectType} from 'type-graphql';
import {Constellation} from './Constellation';
import {Station} from './Station';

@Entity({
  name: 'solar_systems'
})
@ObjectType()
export class System extends BaseEntity {
  @Field(() => ID)
  @PrimaryColumn({name: 'solarSystemID'})
  id: number;

  @Field(() => String)
  @Column({name: 'solarSystemName'})
  name: string;

  @Field(() => Constellation)
  @ManyToOne(() => Constellation, c => c.systems, {lazy: true})
  constellation: Promise<Constellation>;

  @Field(() => [Station])
  @OneToMany(() => Station, station => station.system, {lazy: true})
  stations: Promise<Station[]>;

  @Column({name: 'constellationID'})
  constellationId: number;

  @Field(() => Number)
  @Column()
  sovereigntyHolderID: number;

  @Field(() => String)
  @Column()
  sovereigntyHolderName: string;

  @Field(() => Boolean)
  @Column()
  isIsland: boolean;

  @Field(() => Number)
  @Column({
    name: 'systemSize',
    transformer: {
      from: value => value != null && !isNaN(parseInt(value)) ? (parseInt(value) + 17) * 2 : 0,
      to: value => value
    }
  })
  size: number;

  @Field(() => Number)
  @Column({
    type: "float",
    transformer: {
      from: value => (value > 0) ? +parseFloat(value).toFixed(1) : +parseFloat(value).toFixed(2),
      to: value => value
    }
  })
  security: number;

  @Field(() => String)
  @Column({name: 'systemType'})
  type: string;

  @Field(() => Boolean)
  hasRepairStation: boolean = false;

  @Field(() => String)
  get securityArea() {
    if (this.security <= 0) {
      return 'null';
    } else if (this.security >= 0.5) {
      return 'high';
    } else {
      return 'low';
    }
  }

}
