/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import type { TMilestone, TMilestonePayload } from "@/components/milestones/types";
import { APIService } from "@/services/api.service";

/** Client for the Custom Plane milestones API, mounted under `/api/custom/`. */
export class MilestoneService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string, projectId: string) {
    return `/api/custom/workspaces/${workspaceSlug}/projects/${projectId}/milestones/`;
  }

  async getMilestones(workspaceSlug: string, projectId: string): Promise<TMilestone[]> {
    return this.get(this.base(workspaceSlug, projectId))
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createMilestone(workspaceSlug: string, projectId: string, data: TMilestonePayload): Promise<TMilestone> {
    return this.post(this.base(workspaceSlug, projectId), data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateMilestone(
    workspaceSlug: string,
    projectId: string,
    milestoneId: string,
    data: Partial<TMilestonePayload>
  ): Promise<TMilestone> {
    return this.patch(`${this.base(workspaceSlug, projectId)}${milestoneId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async deleteMilestone(workspaceSlug: string, projectId: string, milestoneId: string): Promise<void> {
    return this.delete(`${this.base(workspaceSlug, projectId)}${milestoneId}/`)
      .then(() => undefined)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
