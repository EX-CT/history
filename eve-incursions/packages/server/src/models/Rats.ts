import {Field, ID, ObjectType} from 'type-graphql';
import {BaseEntity, Column, Entity, PrimaryGeneratedColumn} from 'typeorm';

@ObjectType()
export class HP {
  @Field()
  total: number;

  @Field()
  shield: number;

  @Field()
  armor: number;

  @Field()
  structure: number;
}

@ObjectType()
export class DamageTypes {
  @Field()
  kinetic: number;

  @Field()
  thermal: number;

  @Field()
  em: number;

  @Field()
  explosive: number;
}

@ObjectType()
export class EwarValues {
  @Field()
  name: string;

  @Field()
  value: number;

  @Field({nullable: true})
  unit?: string;
}

@ObjectType()
export class Ewar {
  @Field()
  id: number;

  @Field()
  name: string;

  @Field(() => [EwarValues])
  values: EwarValues[];
}


@ObjectType()
export class Rat {
  @Field()
  name: string;

  @Field()
  id: number;

  @Field()
  graphicId: number;

  @Field()
  groupId: number;

  @Field(() => HP)
  hp: HP;

  @Field(() => HP)
  ehp: HP;

  @Field({nullable: true})
  attackTypeId: number;

  @Field({nullable: true})
  attackType: 'Laser' | 'Missile';

  @Field({nullable: true})
  attackMultiplier: number;

  @Field({nullable: true})
  attackDuration: number;

  @Field({nullable: true})
  attackAlpha: number;

  @Field(() => DamageTypes)
  attackTypes: DamageTypes;

  @Field(() => DamageTypes)
  shieldResistances: DamageTypes;

  @Field(() => DamageTypes)
  armorResistances: DamageTypes;

  @Field(() => DamageTypes)
  structureResistances: DamageTypes;

  @Field({nullable: true})
  attackRange: number;

  @Field()
  orbitRange: number;

  @Field()
  orbitSpeed: number;

  @Field()
  chaseSpeed: number;

  @Field()
  signatureRadius: number;

  @Field()
  scanResolution: number;

  @Field(() => [Ewar])
  ewar: Ewar[];
}

@Entity({name: 'rat_groups'})
@ObjectType()
export class RatGroup extends BaseEntity {
  @PrimaryGeneratedColumn()
  @Field(() => ID)
  id: number;

  @Field()
  @Column()
  name: string;

  @Field(() => [Rat])
  @Column('simple-json')
  rats: Rat[];
}
