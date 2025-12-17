import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface QubeOrderState {
  // Map of userId -> array of qube IDs in order
  orderByUser: Record<string, string[]>;
  setQubeOrder: (userId: string, qubeIds: string[]) => void;
  getQubeOrder: (userId: string) => string[];
}

export const useQubeOrder = create<QubeOrderState>()(
  persist(
    (set, get) => ({
      orderByUser: {},
      setQubeOrder: (userId: string, qubeIds: string[]) =>
        set((state) => ({
          orderByUser: {
            ...state.orderByUser,
            [userId]: qubeIds,
          },
        })),
      getQubeOrder: (userId: string) => {
        const state = get();
        return state.orderByUser[userId] || [];
      },
    }),
    {
      name: 'qubes-order-storage',
    }
  )
);
