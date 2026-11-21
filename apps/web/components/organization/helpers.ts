/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TDepartment } from "./types";

export type TDepartmentNode = TDepartment & { depth: number };

/**
 * Departments in tree order (parents before their children, siblings by name) with their depth.
 * A department whose parent is missing from the list is treated as a root, so a partial list never
 * drops rows.
 */
export const flattenDepartmentTree = (departments: TDepartment[]): TDepartmentNode[] => {
  const ids = new Set(departments.map((d) => d.id));
  const byParent = new Map<string | null, TDepartment[]>();
  for (const d of departments) {
    const key = d.parent && ids.has(d.parent) ? d.parent : null;
    const siblings = byParent.get(key) ?? [];
    siblings.push(d);
    byParent.set(key, siblings);
  }
  const result: TDepartmentNode[] = [];
  const visit = (parent: string | null, depth: number, seen: Set<string>) => {
    // oxlint-disable-next-line unicorn/no-array-sort -- toSorted is not in this app's TS lib target
    const siblings = [...(byParent.get(parent) ?? [])].sort((a, b) => a.name.localeCompare(b.name));
    for (const d of siblings) {
      if (seen.has(d.id)) continue; // defensive: never loop on bad data
      seen.add(d.id);
      result.push({ ...d, depth });
      visit(d.id, depth + 1, seen);
    }
  };
  visit(null, 0, new Set());
  return result;
};

/** Ids of every department below `id` (not including `id`). */
export const getDescendantIds = (departments: TDepartment[], id: string): Set<string> => {
  const children = new Map<string, string[]>();
  for (const d of departments) {
    if (!d.parent) continue;
    children.set(d.parent, [...(children.get(d.parent) ?? []), d.id]);
  }
  const result = new Set<string>();
  const stack = [...(children.get(id) ?? [])];
  while (stack.length > 0) {
    const current = stack.pop()!;
    if (result.has(current)) continue;
    result.add(current);
    stack.push(...(children.get(current) ?? []));
  }
  return result;
};

/** Departments a department may be moved under: not itself and not one of its own descendants. */
export const getParentOptions = (departments: TDepartment[], editingId?: string): TDepartmentNode[] => {
  const blocked = editingId ? getDescendantIds(departments, editingId) : new Set<string>();
  if (editingId) blocked.add(editingId);
  return flattenDepartmentTree(departments).filter((d) => !blocked.has(d.id));
};

/** The API reports problems as `{field: [messages]}` or `{error: message}`. */
export const getApiErrorMessage = (error: unknown, fallback: string): string => {
  if (!error || typeof error !== "object") return fallback;
  const first = Object.values(error as Record<string, unknown>)[0];
  if (typeof first === "string") return first;
  if (Array.isArray(first) && typeof first[0] === "string") return first[0];
  return fallback;
};
