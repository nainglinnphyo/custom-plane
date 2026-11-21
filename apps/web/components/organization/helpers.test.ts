/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { flattenDepartmentTree, getApiErrorMessage, getDescendantIds, getParentOptions } from "./helpers";
import type { TDepartment } from "./types";

const dept = (id: string, name: string, parent: string | null = null): TDepartment => ({
  id,
  name,
  description: "",
  parent,
  member_count: 0,
  child_count: 0,
});

const sample = [
  dept("eng", "Engineering"),
  dept("ops", "Operations"),
  dept("plat", "Platform", "eng"),
  dept("web", "Web", "eng"),
  dept("sre", "SRE", "plat"),
];

describe("flattenDepartmentTree", () => {
  it("orders parents before children, siblings by name, with depth", () => {
    expect(flattenDepartmentTree(sample).map((d) => [d.id, d.depth])).toEqual([
      ["eng", 0],
      ["plat", 1],
      ["sre", 2],
      ["web", 1],
      ["ops", 0],
    ]);
  });

  it("treats departments with an unknown parent as roots instead of dropping them", () => {
    const result = flattenDepartmentTree([dept("a", "A", "ghost")]);
    expect(result).toHaveLength(1);
    expect(result[0].depth).toBe(0);
  });

  it("does not loop on cyclic data", () => {
    const result = flattenDepartmentTree([dept("a", "A", "b"), dept("b", "B", "a")]);
    expect(result.length).toBeLessThanOrEqual(2);
  });

  it("handles an empty list", () => {
    expect(flattenDepartmentTree([])).toEqual([]);
  });
});

describe("getDescendantIds / getParentOptions", () => {
  it("collects all descendants but not the node itself", () => {
    expect(getDescendantIds(sample, "eng")).toEqual(new Set(["plat", "sre", "web"]));
    expect(getDescendantIds(sample, "sre").size).toBe(0);
  });

  it("excludes the department and its subtree from parent options", () => {
    expect(getParentOptions(sample, "eng").map((d) => d.id)).toEqual(["ops"]);
    expect(getParentOptions(sample, "web").map((d) => d.id)).toEqual(["eng", "plat", "sre", "ops"]);
  });

  it("offers every department when creating", () => {
    expect(getParentOptions(sample)).toHaveLength(5);
  });
});

describe("getApiErrorMessage", () => {
  it("reads the first message from DRF-style and plain errors", () => {
    expect(getApiErrorMessage({ name: ["Taken."] }, "x")).toBe("Taken.");
    expect(getApiErrorMessage({ error: "Nope" }, "x")).toBe("Nope");
  });

  it("falls back for unknown shapes", () => {
    expect(getApiErrorMessage(undefined, "fb")).toBe("fb");
    expect(getApiErrorMessage({}, "fb")).toBe("fb");
    expect(getApiErrorMessage({ a: 1 }, "fb")).toBe("fb");
  });
});
