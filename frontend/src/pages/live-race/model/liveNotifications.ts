import { createBroadcastQueue, type BroadcastQueueState } from "./liveBroadcast";
import type { RadioMessage } from "./useLiveRace";

export const RADIO_DURATION_MS = 7000;

export interface LiveNotificationState {
  radioMessage: RadioMessage | null;
  broadcastQueue: BroadcastQueueState;
}

export function createLiveNotificationState(): LiveNotificationState {
  return { radioMessage: null, broadcastQueue: createBroadcastQueue() };
}

export function replaceRadioMessage(message: RadioMessage | null, next: RadioMessage) {
  return next;
}

export function expireRadioMessage(message: RadioMessage | null, nowMs: number) {
  return message && nowMs - message.timestamp >= RADIO_DURATION_MS ? null : message;
}
