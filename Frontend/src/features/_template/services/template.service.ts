import { mockTemplateItems } from "../mocks/template.mock";
import type { TemplateItem } from "../types/template.types";

// TODO: replace the mock with a real request (fetch / server action / API client).
export async function getTemplateItems(): Promise<TemplateItem[]> {
  return mockTemplateItems;
}

// TODO: add create / update / delete functions.
