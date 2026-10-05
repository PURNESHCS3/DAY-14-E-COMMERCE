import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCartStore } from "../stores/cartStore";
import { getCart, addToCart, removeFromCart } from "../services/cart";
import { getProduct } from "../services/products";

export const cartQueryKey = ["cart"];

export function useCartQuery(enabled = true) {
  const setCart = useCartStore((state) => state.setCart);
  const query = useQuery({
    queryKey: cartQueryKey,
    queryFn: async () => {
      const { cart } = await getCart();
      setCart(cart);
      return cart;
    },
    enabled,
  });

  useEffect(() => {
    if (enabled && query.data) setCart(query.data);
    if (!enabled) setCart({});
  }, [enabled, query.data, setCart]);

  return query;
}

export function useCartItems(cart = {}) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: [...cartQueryKey, "items"],
    queryFn: async () =>
      Promise.all(
        Object.entries(cart).map(async ([productId, quantity]) => ({
          product: await queryClient.fetchQuery({
            queryKey: ["products", "detail", productId],
            queryFn: () => getProduct(productId),
          }),
          quantity,
        }))
      ),
    enabled: Boolean(cart),
  });
}

export function useAddToCart() {
  const queryClient = useQueryClient();
  const addItem = useCartStore((state) => state.addItem);
  const setCart = useCartStore((state) => state.setCart);

  return useMutation({
    mutationFn: ({ productId, quantity }) => addToCart(productId, quantity),
    onMutate: async ({ productId, quantity, product }) => {
      await queryClient.cancelQueries({ queryKey: cartQueryKey });
      const previousCart = queryClient.getQueryData(cartQueryKey);
      const previousItems = queryClient.getQueryData([...cartQueryKey, "items"]);
      const key = String(productId);
      const nextCart = {
        ...(previousCart || {}),
        [key]: (previousCart?.[key] || 0) + quantity,
      };

      addItem(productId, quantity);
      queryClient.setQueryData(cartQueryKey, nextCart);
      if (previousItems) {
        const itemIndex = previousItems.findIndex(
          ({ product: itemProduct }) => String(itemProduct.id) === key
        );
        queryClient.setQueryData(
          [...cartQueryKey, "items"],
          itemIndex === -1
            ? [...previousItems, { product, quantity }]
            : previousItems.map((item, index) =>
                index === itemIndex
                  ? { ...item, quantity: item.quantity + quantity }
                  : item
              )
        );
      }

      return { previousCart, previousItems };
    },
    onSuccess: ({ cart }) => {
      setCart(cart);
      queryClient.setQueryData(cartQueryKey, cart);
    },
    onError: (_error, _variables, context) => {
      if (context?.previousCart) {
        setCart(context.previousCart);
        queryClient.setQueryData(cartQueryKey, context.previousCart);
      } else {
        useCartStore.getState().clear();
        queryClient.removeQueries({ queryKey: cartQueryKey });
      }
      if (context?.previousItems) {
        queryClient.setQueryData(
          [...cartQueryKey, "items"],
          context.previousItems
        );
      }
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: cartQueryKey }),
  });
}

export function useRemoveFromCart() {
  const queryClient = useQueryClient();
  const removeItem = useCartStore((state) => state.removeItem);
  const setCart = useCartStore((state) => state.setCart);

  return useMutation({
    mutationFn: (productId) => removeFromCart(productId),
    onMutate: async (productId) => {
      await queryClient.cancelQueries({ queryKey: cartQueryKey });
      const previousCart = queryClient.getQueryData(cartQueryKey);
      const previousItems = queryClient.getQueryData([...cartQueryKey, "items"]);
      const nextCart = { ...(previousCart || {}) };
      delete nextCart[String(productId)];

      removeItem(productId);
      queryClient.setQueryData(cartQueryKey, nextCart);
      if (previousItems) {
        queryClient.setQueryData(
          [...cartQueryKey, "items"],
          previousItems.filter(
            ({ product }) => String(product.id) !== String(productId)
          )
        );
      }

      return { previousCart, previousItems };
    },
    onSuccess: ({ cart }) => {
      setCart(cart);
      queryClient.setQueryData(cartQueryKey, cart);
    },
    onError: (_error, _productId, context) => {
      if (context?.previousCart) {
        setCart(context.previousCart);
        queryClient.setQueryData(cartQueryKey, context.previousCart);
      }
      if (context?.previousItems) {
        queryClient.setQueryData(
          [...cartQueryKey, "items"],
          context.previousItems
        );
      }
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: cartQueryKey }),
  });
}
