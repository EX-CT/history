import {ClassType, Field, Int, ObjectType} from 'type-graphql';

export function PaginatedResponse<TItemsFieldValue extends object>(
  itemsFieldValue: ClassType<TItemsFieldValue>,
) {
  @ObjectType()
  abstract class PaginatedResponseClass {
    @Field(type => [itemsFieldValue])
    items: TItemsFieldValue[];

    @Field(type => Int)
    total: number;

    @Field()
    hasMore: boolean;
  }
  return PaginatedResponseClass;
}
