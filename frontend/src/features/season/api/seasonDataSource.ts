import { backendSeasonRepository } from "@/features/season/api/backendSeasonRepository";
import type { SeasonRepository } from "@/features/season/api/seasonRepository";

export const seasonRepository: SeasonRepository = backendSeasonRepository;
