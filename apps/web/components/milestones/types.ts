/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Mirrors the Custom Plane milestones API (apps/api/plane/custom/milestones/serializers.py).

export type TMilestoneStatus = "planned" | "in_progress" | "achieved" | "missed";

export type TMilestoneProgress = {
  total: number;
  completed: number;
  cancelled: number;
  started: number;
  percent: number;
};

export type TMilestone = {
  id: string;
  project: string;
  name: string;
  description: string;
  start_date: string | null;
  due_date: string;
  status: TMilestoneStatus;
  status_override: boolean;
  is_at_risk: boolean;
  owner: string | null;
  sort_order: number;
  progress: TMilestoneProgress;
  dependency_ids: string[];
  created_at: string;
  updated_at: string;
};

export type TMilestoneFormValues = {
  name: string;
  description: string;
  start_date: string | null;
  due_date: string | null;
};

export type TMilestonePayload = {
  name: string;
  description: string;
  start_date: string | null;
  due_date: string;
};
