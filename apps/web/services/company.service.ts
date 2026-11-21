/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TCompany, TDepartment, TMembersKind, TOrgMembership, TOrgRole, TTeam } from "@/components/company/types";
import { APIService } from "@/services/api.service";

type TDepartmentPayload = { name: string; description: string; parent: string | null };
type TTeamPayload = { name: string; description: string; department: string | null };

/** Client for the Custom Plane company / departments / teams API, mounted under `/api/custom/`. */
export class CompanyService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private path(workspaceSlug: string, rest: string) {
    return `/api/custom/workspaces/${workspaceSlug}/${rest}`;
  }

  private async unwrap<T>(request: Promise<{ data: T }>): Promise<T> {
    return request
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  getCompany(workspaceSlug: string): Promise<TCompany | null> {
    return this.unwrap(this.get(this.path(workspaceSlug, "company/")));
  }

  createCompany(workspaceSlug: string, name: string): Promise<TCompany> {
    return this.unwrap(this.post(this.path(workspaceSlug, "company/"), { name }));
  }

  getDepartments(workspaceSlug: string): Promise<TDepartment[]> {
    return this.unwrap(this.get(this.path(workspaceSlug, "departments/")));
  }

  createDepartment(workspaceSlug: string, data: TDepartmentPayload): Promise<TDepartment> {
    return this.unwrap(this.post(this.path(workspaceSlug, "departments/"), data));
  }

  updateDepartment(workspaceSlug: string, id: string, data: Partial<TDepartmentPayload>): Promise<TDepartment> {
    return this.unwrap(this.patch(this.path(workspaceSlug, `departments/${id}/`), data));
  }

  deleteDepartment(workspaceSlug: string, id: string): Promise<void> {
    return this.unwrap(this.delete(this.path(workspaceSlug, `departments/${id}/`)));
  }

  getTeams(workspaceSlug: string): Promise<TTeam[]> {
    return this.unwrap(this.get(this.path(workspaceSlug, "teams/")));
  }

  createTeam(workspaceSlug: string, data: TTeamPayload): Promise<TTeam> {
    return this.unwrap(this.post(this.path(workspaceSlug, "teams/"), data));
  }

  updateTeam(workspaceSlug: string, id: string, data: Partial<TTeamPayload>): Promise<TTeam> {
    return this.unwrap(this.patch(this.path(workspaceSlug, `teams/${id}/`), data));
  }

  deleteTeam(workspaceSlug: string, id: string): Promise<void> {
    return this.unwrap(this.delete(this.path(workspaceSlug, `teams/${id}/`)));
  }

  getMembers(workspaceSlug: string, kind: TMembersKind, id: string): Promise<TOrgMembership[]> {
    return this.unwrap(this.get(this.path(workspaceSlug, `${kind}/${id}/members/`)));
  }

  addMember(workspaceSlug: string, kind: TMembersKind, id: string, member: string, role: TOrgRole) {
    return this.unwrap<TOrgMembership>(this.post(this.path(workspaceSlug, `${kind}/${id}/members/`), { member, role }));
  }

  setMemberRole(workspaceSlug: string, kind: TMembersKind, id: string, userId: string, role: TOrgRole) {
    return this.unwrap<TOrgMembership>(
      this.patch(this.path(workspaceSlug, `${kind}/${id}/members/${userId}/`), { role })
    );
  }

  removeMember(workspaceSlug: string, kind: TMembersKind, id: string, userId: string): Promise<void> {
    return this.unwrap(this.delete(this.path(workspaceSlug, `${kind}/${id}/members/${userId}/`)));
  }
}
