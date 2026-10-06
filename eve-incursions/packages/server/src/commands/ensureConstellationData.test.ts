import {describe, it, expect, vi, beforeEach} from 'vitest';

const {mockSave, mockFindOneBy, mockTransactionSave} = vi.hoisted(() => ({
  mockSave: vi.fn(),
  mockFindOneBy: vi.fn(),
  mockTransactionSave: vi.fn(),
}));

vi.mock('../lib/esi', () => ({
  fetchRegion: vi.fn(),
  fetchConstellation: vi.fn(),
  fetchSystem: vi.fn(),
}));

vi.mock('../lib/data-source', () => ({
  AppDataSource: {
    manager: {
      transaction: vi.fn(async (cb: any) => cb({save: mockTransactionSave})),
    },
  },
}));

vi.mock('../models/Region', () => {
  return {
    Region: class MockRegion {
      static findOneBy = mockFindOneBy;
      save = mockSave;
      id: number = 0;
      name: string = '';
    },
  };
});

vi.mock('../models/Constellation', () => {
  return {
    Constellation: class MockConstellation {
      static findOneBy = mockFindOneBy;
      save = mockSave;
      id: number = 0;
      name: string = '';
      regionId: number = 0;
    },
  };
});

vi.mock('../models/System', () => {
  return {
    System: class MockSystem {
      static findOneBy = mockFindOneBy;
      id: number = 0;
      name: string = '';
      security: number = 0;
      constellationId: number = 0;
      sovereigntyHolderID: number = 0;
      sovereigntyHolderName: string = '';
      isIsland: boolean = false;
      size: number = 0;
      type: string = '';
    },
  };
});

import {ensureConstellationData} from './ensureConstellationData';
import {fetchConstellation, fetchRegion, fetchSystem} from '../lib/esi';

const mockedFetchConstellation = vi.mocked(fetchConstellation);
const mockedFetchRegion = vi.mocked(fetchRegion);
const mockedFetchSystem = vi.mocked(fetchSystem);

describe('ensureConstellationData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFindOneBy.mockResolvedValue(null);
  });

  it('fetches constellation, region, and systems from ESI when not in DB', async () => {
    mockedFetchConstellation.mockResolvedValue({
      constellation_id: 20000001,
      name: 'Test Constellation',
      region_id: 10000001,
      systems: [30000001, 30000002],
    });

    mockedFetchRegion.mockResolvedValue({
      region_id: 10000001,
      name: 'Test Region',
    });

    mockedFetchSystem
      .mockResolvedValueOnce({
        system_id: 30000001,
        name: 'System A',
        security_status: 0.5,
        constellation_id: 20000001,
      })
      .mockResolvedValueOnce({
        system_id: 30000002,
        name: 'System B',
        security_status: -0.3,
        constellation_id: 20000001,
      });

    await ensureConstellationData([20000001]);

    expect(mockedFetchRegion).toHaveBeenCalledWith(10000001);
    expect(mockedFetchConstellation).toHaveBeenCalledWith(20000001);
    expect(mockedFetchSystem).toHaveBeenCalledWith(30000001);
    expect(mockedFetchSystem).toHaveBeenCalledWith(30000002);
  });

  it('does not fetch region if constellation already exists in DB', async () => {
    mockFindOneBy.mockImplementation(async (where: any) => {
      if (where.id === 20000001) return {id: 20000001, name: 'Existing'};
      return null;
    });

    mockedFetchConstellation.mockResolvedValue({
      constellation_id: 20000001,
      name: 'Test Constellation',
      region_id: 10000001,
      systems: [30000001],
    });

    mockedFetchSystem.mockResolvedValue({
      system_id: 30000001,
      name: 'System A',
      security_status: 0.8,
      constellation_id: 20000001,
    });

    await ensureConstellationData([20000001]);

    expect(mockedFetchRegion).not.toHaveBeenCalled();
  });

  it('deduplicates constellation IDs', async () => {
    mockFindOneBy.mockResolvedValue({id: 20000001, name: 'Existing'});

    mockedFetchConstellation.mockResolvedValue({
      constellation_id: 20000001,
      name: 'Test',
      region_id: 10000001,
      systems: [],
    });

    await ensureConstellationData([20000001, 20000001, 20000001]);

    expect(mockedFetchConstellation).toHaveBeenCalledTimes(1);
  });

  it('continues processing if one constellation fails', async () => {
    mockedFetchConstellation
      .mockRejectedValueOnce(new Error('ESI error'))
      .mockResolvedValue({
        constellation_id: 20000002,
        name: 'Good Constellation',
        region_id: 10000001,
        systems: [],
      });

    mockedFetchRegion.mockResolvedValue({
      region_id: 10000001,
      name: 'Region',
    });

    await ensureConstellationData([20000001, 20000002]);

    expect(mockedFetchConstellation).toHaveBeenCalledWith(20000001);
    expect(mockedFetchConstellation).toHaveBeenCalledWith(20000002);
  });

  it('always fetches system data to update security status', async () => {
    const existingSystem = {
      id: 30000001,
      name: 'Old Name',
      security: 0.5,
      constellationId: 20000001,
    };

    mockFindOneBy.mockImplementation(async (where: any) => {
      if (where.id === 20000001) return {id: 20000001, name: 'Constellation'};
      if (where.id === 30000001) return {...existingSystem};
      return null;
    });

    mockedFetchConstellation.mockResolvedValue({
      constellation_id: 20000001,
      name: 'Constellation',
      region_id: 10000001,
      systems: [30000001],
    });

    mockedFetchSystem.mockResolvedValue({
      system_id: 30000001,
      name: 'New Name',
      security_status: 0.3,
      constellation_id: 20000001,
    });

    await ensureConstellationData([20000001]);

    expect(mockedFetchSystem).toHaveBeenCalledWith(30000001);
  });

  it('saves new systems with correct defaults', async () => {
    mockedFetchConstellation.mockResolvedValue({
      constellation_id: 20000001,
      name: 'Constellation',
      region_id: 10000001,
      systems: [30000001],
    });

    mockedFetchRegion.mockResolvedValue({
      region_id: 10000001,
      name: 'Region',
    });

    mockedFetchSystem.mockResolvedValue({
      system_id: 30000001,
      name: 'New System',
      security_status: 0.7,
      constellation_id: 20000001,
    });

    await ensureConstellationData([20000001]);

    expect(mockTransactionSave).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 30000001,
        name: 'New System',
        security: 0.7,
        constellationId: 20000001,
        sovereigntyHolderID: 0,
        sovereigntyHolderName: '',
        isIsland: false,
        size: 0,
        type: 'not known',
      })
    );
  });
});
