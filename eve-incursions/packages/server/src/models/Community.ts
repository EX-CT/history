import {BaseEntity, Column, Entity, PrimaryGeneratedColumn} from 'typeorm';
import {Field, ID, ObjectType} from 'type-graphql';

@Entity({
  name: 'communities'
})
@ObjectType()
export class Community extends BaseEntity {
  @Field(() => ID)
  @PrimaryGeneratedColumn()
  id: number;

  @Field(() => String)
  @Column({name: 'communityName'})
  name: string;

  @Field(() => String)
  @Column({name: 'communityTag'})
  tag: string;

  @Field(() => String)
  @Column()
  channel: string;

  @Field(() => String)
  @Column()
  language: string;

  @Field(() => String)
  @Column()
  tank: string;

  @Field()
  @Column()
  active: boolean;

  @Field(() => String)
  @Column()
  timezone: string;

  @Field()
  @Column({name: 'isHQ'})
  hq: boolean;

  @Field()
  @Column({name: 'isAS'})
  as: boolean;

  @Field()
  @Column({name: 'isVG'})
  vg: boolean;

}
