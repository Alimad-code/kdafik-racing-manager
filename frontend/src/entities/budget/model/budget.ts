import { z } from "zod";

export const budgetSpendingCategorySchema = z.enum([
  "drivers",
  "team",
  "car-construction",
  "setup",
  "repair"
]);

export const budgetTransactionSchema = z.object({
  id: z.string(),
  category: budgetSpendingCategorySchema,
  label: z.string(),
  amountMillions: z.number().nonnegative()
});

export const budgetStateSchema = z.object({
  startingMillions: z.number().nonnegative(),
  spentMillions: z.number().nonnegative(),
  availableMillions: z.number().nonnegative(),
  repairReserveMillions: z.number().nonnegative(),
  setupReserveMillions: z.number().nonnegative(),
  freeMillions: z.number().nonnegative(),
  transactions: z.array(budgetTransactionSchema)
});

export type BudgetSpendingCategory = z.infer<typeof budgetSpendingCategorySchema>;
export type BudgetTransaction = z.infer<typeof budgetTransactionSchema>;
export type BudgetState = z.infer<typeof budgetStateSchema>;
