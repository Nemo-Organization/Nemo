import { mockRecipients } from "../mocks/transfer.mock";
import type { Recipient } from "../types/transfer.types";

// TODO: replace with transfer API calls.
export async function getTransferRecipients(): Promise<Recipient[]> {
  return mockRecipients;
}
