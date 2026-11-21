/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Mirrors the Custom Plane company/teams API (apps/api/plane/custom/{company,teams}).

export type TOrgRole = "member" | "lead";

export type TCompanyWorkspace = { id: string; slug: string; name: string; is_primary: boolean };

export type TCompany = {
  id: string;
  name: string;
  slug: string;
  settings: Record<string, unknown>;
  workspaces: TCompanyWorkspace[];
};

export type TDepartment = {
  id: string;
  name: string;
  description: string;
  parent: string | null;
  member_count: number;
  child_count: number;
};

export type TTeam = {
  id: string;
  name: string;
  description: string;
  department: string | null;
  member_count: number;
};

export type TOrgMembership = {
  id: string;
  /** user id */
  member: string;
  display_name: string;
  first_name: string;
  last_name: string;
  role: TOrgRole;
};

export type TMembersKind = "departments" | "teams";
