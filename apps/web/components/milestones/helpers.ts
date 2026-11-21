/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TMilestone, TMilestoneStatus } from "./types";

const DAY_MS = 24 * 60 * 60 * 1000;
/** A milestone with no start date (or a one-day span) still needs a visible marker. */
const MIN_BAR_PERCENT = 1.5;

/** Parse an API `YYYY-MM-DD` date as a local calendar day (avoids the UTC-midnight off-by-one). */
export const parseApiDate = (value: string): Date => {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
};

export type TTimelineRange = { start: Date; end: Date; totalDays: number };

/**
 * The span the timeline should cover: earliest start (or due) date to latest due date, padded by
 * a day on each side. Returns `null` when there is nothing to draw.
 */
export const getTimelineRange = (milestones: TMilestone[]): TTimelineRange | null => {
  if (milestones.length === 0) return null;
  let min = Infinity;
  let max = -Infinity;
  for (const m of milestones) {
    const due = parseApiDate(m.due_date).getTime();
    const start = m.start_date ? parseApiDate(m.start_date).getTime() : due;
    min = Math.min(min, start, due);
    max = Math.max(max, start, due);
  }
  const start = new Date(min - DAY_MS);
  const end = new Date(max + DAY_MS);
  return { start, end, totalDays: Math.round((end.getTime() - start.getTime()) / DAY_MS) };
};

export type TBarPosition = { leftPercent: number; widthPercent: number };

/** Position of a milestone's bar inside the range, in percent of the track width. */
export const getBarPosition = (milestone: TMilestone, range: TTimelineRange): TBarPosition => {
  const span = range.end.getTime() - range.start.getTime();
  const due = parseApiDate(milestone.due_date).getTime();
  const start = milestone.start_date ? parseApiDate(milestone.start_date).getTime() : due;
  // the bar covers the whole due day
  const left = ((start - range.start.getTime()) / span) * 100;
  const right = ((due + DAY_MS - range.start.getTime()) / span) * 100;
  const widthPercent = Math.max(MIN_BAR_PERCENT, right - left);
  const leftPercent = Math.min(Math.max(0, left), 100 - widthPercent);
  return { leftPercent, widthPercent };
};

/** Position of "today" inside the range, or `null` when today falls outside it. */
export const getTodayPercent = (range: TTimelineRange, today: Date = new Date()): number | null => {
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  if (t < range.start.getTime() || t > range.end.getTime()) return null;
  return ((t - range.start.getTime()) / (range.end.getTime() - range.start.getTime())) * 100;
};

export type TStatusBadgeVariant = "neutral" | "info" | "success" | "danger";

export const MILESTONE_STATUS_META: Record<TMilestoneStatus, { i18nKey: string; variant: TStatusBadgeVariant }> = {
  planned: { i18nKey: "common.planned", variant: "neutral" },
  in_progress: { i18nKey: "common.in_progress", variant: "info" },
  achieved: { i18nKey: "common.completed", variant: "success" },
  missed: { i18nKey: "milestone.status_missed", variant: "danger" },
};

/** Tailwind class for the timeline bar of a status. */
export const MILESTONE_BAR_CLASS: Record<TMilestoneStatus, string> = {
  planned: "bg-accent-primary opacity-50",
  in_progress: "bg-info-primary",
  achieved: "bg-success-primary",
  missed: "bg-danger-primary",
};
