"use client";

import { useMutation, type UseMutationOptions } from "@tanstack/react-query";
import { useRef } from "react";

import { IdempotentAction } from "./idempotency";

/**
 * A write action with its own Idempotency-Key: the same input retried (the "Try again" button) sends the same
 * key, so the backend does the work once. `write` receives the key to put in the Idempotency-Key header.
 * Never retried automatically; the person decides.
 */
export function useWrite<Input, Output>(
  write: (input: Input, idempotencyKey: string) => Promise<Output>,
  options: Omit<UseMutationOptions<Output, unknown, Input>, "mutationFn" | "retry"> = {},
) {
  const action = useRef(new IdempotentAction<Input>());
  return useMutation<Output, unknown, Input>({
    ...options,
    retry: false,
    mutationFn: async (input) => {
      const result = await write(input, action.current.keyFor(input));
      action.current.done();
      return result;
    },
  });
}
