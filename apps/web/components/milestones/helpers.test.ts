/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { MILESTONE_STATUS_META, getBarPosition, getTimelineRange, getTodayPercent, parseApiDate } from "./helpers";
import type { TMilestone } from "./types";

const make = (overrides: Partial<TMilestone> = {}): TMilestone => ({
  id: "m1",
  project: "p1",
  name: "M",
  description: "",
  start_date: null,
  due_date: "2026-06-10",
  status: "planned",
  status_override: false,
  is_at_risk: false,
  owner: null,
  sort_order: 65535,
  progress: { total: 0, completed: 0, cancelled: 0, started: 0, percent: 0 },
  dependency_ids: [],
  created_at: "",
  updated_at: "",
  ...overrides,
});

describe("parseApiDate", () => {
  it("parses as a local calendar day, not UTC midnight", () => {
    const d = parseApiDate("2026-03-05");
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 2, 5]);
    expect(d.getHours()).toBe(0);
  });
});

describe("getTimelineRange", () => {
  it("returns null without milestones", () => {
    expect(getTimelineRange([])).toBeNull();
  });

  it("spans earliest start to latest due date, padded by a day each side", () => {
    const range = getTimelineRange([
      make({ id: "a", start_date: "2026-06-01", due_date: "2026-06-10" }),
      make({ id: "b", start_date: null, due_date: "2026-06-20" }),
    ])!;
    expect(range.start).toEqual(new Date(2026, 4, 31));
    expect(range.end).toEqual(new Date(2026, 5, 21));
    expect(range.totalDays).toBe(21);
  });

  it("handles a single milestone with no start date", () => {
    const range = getTimelineRange([make()])!;
    expect(range.totalDays).toBe(2);
  });
});

describe("getBarPosition", () => {
  const milestones = [
    make({ id: "a", start_date: "2026-06-01", due_date: "2026-06-10" }),
    make({ id: "b", start_date: null, due_date: "2026-06-20" }),
  ];
  const range = getTimelineRange(milestones)!;

  it("keeps every bar inside the track", () => {
    for (const m of milestones) {
      const { leftPercent, widthPercent } = getBarPosition(m, range);
      expect(leftPercent).toBeGreaterThanOrEqual(0);
      expect(leftPercent + widthPercent).toBeLessThanOrEqual(100.0001);
    }
  });

  it("covers the whole due day and orders bars chronologically", () => {
    const a = getBarPosition(milestones[0], range);
    const b = getBarPosition(milestones[1], range);
    // a: Jun 1..Jun 10 inclusive = 10 days of a 21 day range
    expect(a.widthPercent).toBeCloseTo((10 / 21) * 100, 5);
    expect(a.leftPercent).toBeCloseTo((1 / 21) * 100, 5);
    expect(b.leftPercent).toBeGreaterThan(a.leftPercent);
  });

  it("gives a start-less milestone a minimum visible width", () => {
    const wide = getTimelineRange([
      make({ id: "a", start_date: "2026-01-01", due_date: "2026-12-31" }),
      make({ id: "b", due_date: "2026-06-15" }),
    ])!;
    expect(getBarPosition(make({ due_date: "2026-06-15" }), wide).widthPercent).toBeGreaterThanOrEqual(1.5);
  });
});

describe("getTodayPercent", () => {
  const range = getTimelineRange([make({ start_date: "2026-06-01", due_date: "2026-06-30" })])!;

  it("is null outside the range", () => {
    expect(getTodayPercent(range, new Date(2026, 0, 1))).toBeNull();
    expect(getTodayPercent(range, new Date(2027, 0, 1))).toBeNull();
  });

  it("is a percentage inside the range", () => {
    const p = getTodayPercent(range, new Date(2026, 5, 15, 13, 30))!;
    expect(p).toBeGreaterThan(0);
    expect(p).toBeLessThan(100);
  });
});

describe("MILESTONE_STATUS_META", () => {
  it("covers every status with an i18n key", () => {
    expect(Object.keys(MILESTONE_STATUS_META)).toHaveLength(4);
    expect(Object.keys(MILESTONE_STATUS_META)).toEqual(
      expect.arrayContaining(["achieved", "in_progress", "missed", "planned"])
    );
    for (const meta of Object.values(MILESTONE_STATUS_META)) expect(meta.i18nKey).toMatch(/^(common|milestone)\./);
  });
});
