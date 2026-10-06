export const classNames = (...classes: (string | undefined | boolean)[]): string => {
  return classes.filter(c => c).join(' ');
}

export const dotlanTransform = (name: string) => name.replace(/ /g, '_');
