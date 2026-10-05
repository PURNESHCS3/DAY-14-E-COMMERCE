import { create } from "zustand";
import { useCartStore } from "./cartStore";
import { getCurrentUser, loginUser } from "../services/auth";
import { queryClient } from "../queryClient";

export const useAuthStore = create((set) => ({
  user: null,
  loading: true,
  setUser: (user) => set({ user }),
  setLoading: (loading) => set({ loading }),
  login: async (email, password) => {
    queryClient.removeQueries({ queryKey: ["cart"] });
    useCartStore.getState().clear();
    const tokens = await loginUser({ email, password });
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);

    try {
      const user = await getCurrentUser();
      set({ user });
      return user;
    } catch (error) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      queryClient.removeQueries({ queryKey: ["cart"] });
      useCartStore.getState().clear();
      throw error;
    }
  },
  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    queryClient.removeQueries({ queryKey: ["cart"] });
    useCartStore.getState().clear();
    set({ user: null });
  },
}));
