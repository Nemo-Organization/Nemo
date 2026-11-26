import { mockHomeItems } from "../mocks/home.mock";
import type { HomeItem } from "../types/home.types";

// TODO: replace with API call.
export async function getHomeItems(): Promise<HomeItem[]> {
  return mockHomeItems;
}
