import {DamageTypes, Ewar, HP, Rat, RatGroup} from '../models/Rats';

export const updateRats = async () => {
  const groupIds = [1052,1053,1054,1056];
  const excludeTypeIds = [3490,3487,3486,3511];

  for await (const groupId of groupIds) {
    const res = await fetch(`https://esi.evetech.net/latest/universe/groups/${groupId}/`, {
      headers: {
        'User-Agent': 'eve-incursions.de@lars.naurath@gmail.de'
      }
    });

    const group = await res.json();
    const rats: Rat[] = [];
    for await (const typeId of group.types) {
      if (excludeTypeIds.includes(typeId)) continue;

      const res = await fetch(`https://esi.evetech.net/latest/universe/types/${typeId}/`, {
        headers: {
          'User-Agent': 'eve-incursions.de@lars.naurath@gmail.de'
        }
      });
      const type = await res.json();
      const rat: Partial<Rat> = {};
      rat.id = type.type_id;
      rat.name = type.name;
      rat.graphicId = type.graphic_id;

      const attributes = type.dogma_attributes;
      const attackTypes: DamageTypes = {em: 0, explosive: 0, kinetic: 0, thermal: 0};
      const shieldResistances: DamageTypes = {em: 0, explosive: 0, kinetic: 0, thermal: 0};
      const armorResistances: DamageTypes = {em: 0, explosive: 0, kinetic: 0, thermal: 0};
      const structureResistances: DamageTypes = {em: 0, explosive: 0, kinetic: 0, thermal: 0};
      const hp: HP = {armor: 0, shield: 0, structure: 0, total: 0};
      const ewar: Record<'jam' | "scram" | "neut" | "paint" | "web" | "ecm" | "remote" | "ogb", Ewar> = {
        ecm: {
          id: 27678,
          name: "Remote ECM Burst",
          values: []
        },
        jam: {
          id: 1957,
          name: "Jammer",
          values: []
        },
        neut: {
          id: 533,
          name: "Energy Neutralizer",
          values: []
        },
        ogb: {
          id: 20124,
          name: "OGB",
          values: []
        },
        paint: {
          id: 12709,
          name: "Target Painter",
          values: []
        },
        remote: {
          id: 3586,
          name: "Remote Shield",
          values: []
        },
        scram: {
          id: 447,
          name: "Warp Scrambler",
          values: []
        },
        web: {
          id: 526,
          name: "Stasis Webifier",
          values: []
        }
      };

      for (const {attribute_id: id, value: rawValue} of attributes) {
        const value = Number(rawValue);
        switch (id) {
          case 64:
            if (rat.attackType !== "Missile") {
              rat.attackType = 'Laser';
              rat.attackMultiplier = value;
            }
            break;
          case 51:
            rat.attackDuration = value / 1000;
            break;
          case 245:
            rat.attackTypeId = value;
            break;
          case 114:
            attackTypes.em = value;
            break;
          case 116:
            attackTypes.explosive = value;
            break;
          case 117:
            attackTypes.kinetic = value;
            break;
          case 118:
            attackTypes.thermal = value;
            break;
          case 212:
            rat.attackMultiplier = value;
            break;
          case 507:
            rat.attackType = "Missile";
            rat.attackTypeId = value;

            const res = await fetch(`https://esi.evetech.net/latest/universe/types/${value}/`, {
              headers: {
                'User-Agent': 'eve-incursions.de@lars.naurath@gmail.de'
              }
            });
            const missileType = await res.json();
            for (const attribute of missileType.dogma_attributes) {
              if (attribute.attribute_id === 116) attackTypes.explosive = Number(attribute.value);
              if (attribute.attribute_id === 117) attackTypes.kinetic = Number(attribute.value);
            }

            break;
          case 506:
            rat.attackDuration = value / 1000;
            break;
          case 265:
            hp.armor = value;
            break;
          case 267:
            armorResistances.em = 1 - value;
            break;
          case 268:
            armorResistances.explosive = 1 - value;
            break
          case 269:
            armorResistances.kinetic = 1 - value;
            break
          case 270:
            armorResistances.thermal = 1 - value;
            break
          case 263:
            hp.shield = value;
            break
          case 271:
            shieldResistances.em = 1 - value;
            break
          case 272:
            shieldResistances.explosive = 1 - value;
            break
          case 273:
            shieldResistances.kinetic = 1 - value;
            break
          case 274:
            shieldResistances.thermal = 1 - value;
            break
          case 9:
            hp.structure = value;
            break
          case 552:
            rat.signatureRadius = value;
            break;
          case 508:
            rat.orbitSpeed = value;
            break;
          case 416:
            rat.orbitRange = value;
            break;
          case 564:
            rat.scanResolution = value;
            break;
          case 37:
            rat.chaseSpeed = value;
            break;
          case 247:
            rat.attackRange = value;
            break;
          case 929:
            ewar.jam.values.push({name: "Duration", value: value / 1000, unit: "s"});
            break;
          case 936:
            ewar.jam.values.push({name: "Optimal", value, unit: "m"});
            break;
          case 103:
            ewar.scram.values.push({name: "Range", value, unit: "m"});
            break;
          case 505:
            ewar.scram.values.push({name: "Duration", value: value / 1000, unit: "s"});
            break;
          case 105:
            ewar.scram.values.push({name: "Strength", value});
            break;
          case 98:
            ewar.neut.values.push({name: "Range", value, unit: "m"});
            break;
          case 942:
            ewar.neut.values.push({name: "Duration", value: value / 1000, unit: "s"});
            break;
          case 97:
            ewar.neut.values.push({name: "Amount", value, unit: "GJ"});
            break;
          case 941:
            ewar.paint.values.push({name: "Range", value, unit: "m"});
            break;
          case 945:
            ewar.paint.values.push({name: "Duration", value: value / 1000, unit: "s"});
            break;
          case 954:
            ewar.paint.values.push({name: "FallOff", value, unit: "m"});
            break;
          case 514:
            ewar.web.values.push({name: "Range", value, unit: "m"});
            break;
          case 513:
            ewar.web.values.push({name: "Duration", value: value / 1000, unit: "s"});
            break;
          case 20:
            ewar.web.values.push({name: "Factor", value, unit: "%"});
            break;
          case 1658:
            ewar.ecm.values.push({name: "Duration", value: value / 1000, unit: "s"});
            break;
          case 1659:
            ewar.ecm.values.push({name: "Min. Duration", value: value / 1000, unit: "s"});
            break;
          case 1458:
            ewar.remote.values.push({name: "Duration", value: value / 1000, unit: "s"});
            break;
          case 1460:
            ewar.remote.values.push({name: "Amount", value, unit: "hp"});
            break;
          case 1464:
            ewar.remote.values.push({name: "Range", value, unit: "m"});
            break;
          case 1671:
            ewar.ogb.values.push({name: "Bonus", value, unit: "%"});
            break;
        }
      }

      rat.shieldResistances = shieldResistances;
      rat.armorResistances = armorResistances;
      rat.structureResistances = structureResistances;

      const armorEHP = hp.armor * (1 / (1 - ((armorResistances.thermal + armorResistances.kinetic + armorResistances.explosive + armorResistances.em) / 4)));
      const shieldEHP = hp.shield * (1 / (1 - ((shieldResistances.thermal + shieldResistances.kinetic + shieldResistances.explosive + shieldResistances.em) / 4)));
      const ehp: HP = {
        structure: hp.structure,
        armor: armorEHP,
        shield: shieldEHP,
        total: shieldEHP + armorEHP + hp.structure
      };

      hp.total = hp.structure + hp.shield + hp.armor;

      rat.hp = hp;
      rat.ehp = ehp;
      let alpha = 0;
      for (const [key, value] of Object.entries(attackTypes)) {
        const multVal = rat.attackType === "Missile" && (key === "em" || key === "thermal") ? 0 : (value ?? 0) * (rat.attackMultiplier ?? 1);
        attackTypes[key as keyof DamageTypes] = multVal;
        alpha += multVal;
      }

      rat.attackAlpha = alpha;
      rat.attackTypes = attackTypes;

      rat.ewar = Object.entries(ewar).filter(([key, {id, values}]) => values.length > 0 && (id !== 526 || values.length > 2)).map(([k, v]) => v);
      rats.push(rat as Rat);
    }


    let dbGroup = await RatGroup.findOneBy({id: groupId});
    if (!dbGroup) dbGroup = new RatGroup();

    dbGroup.id = groupId
    dbGroup.name = group.name;
    dbGroup.rats = rats;
    await dbGroup.save();
  }
};
