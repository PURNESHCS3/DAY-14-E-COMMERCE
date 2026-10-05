import { create } from "zustand";

const normalizeCart = (cart) =>
  Object.fromEntries(
    Object.entries(cart || {}).map(([productId, quantity]) => [
      String(productId),
      Number(quantity),
    ])
  );

export const useCartStore = create((set) => ({
  quantities: {},
  hydrated: false,
  setCart: (cart) => set({ quantities: normalizeCart(cart), hydrated: true }),
  addItem: (productId, quantity = 1) =>
    set((state) => {
      const key = String(productId);
      return {
        quantities: {
          ...state.quantities,
          [key]: (state.quantities[key] || 0) + quantity,
        },
        hydrated: true,
      };
    }),
  removeItem: (productId) =>
    set((state) => {
      const quantities = { ...state.quantities };
      delete quantities[String(productId)];
      return { quantities, hydrated: true };
    }),
  clear: () => set({ quantities: {}, hydrated: false }),
}));
