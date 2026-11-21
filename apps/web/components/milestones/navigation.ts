/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { MilestoneOutline } from "@makeplane/propel/icons";
import { EUserPermissions } from "@plane/constants";
import type { TNavigationItem } from "@/components/navigation/tab-navigation-root";

/**
 * The project navigation entry for Milestones. Kept in one place so the core navigation files only
 * need a one-line reference each (see use-navigation-items.ts, projects-list-item.tsx).
 */
export const getMilestonesNavigationItem = (workspaceSlug: string, projectId: string): TNavigationItem => ({
  i18n_key: "milestones",
  key: "milestones",
  name: "Milestones",
  href: `/${workspaceSlug}/projects/${projectId}/milestones`,
  icon: MilestoneOutline,
  access: [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
  shouldRender: true,
  sortOrder: 7,
});

/**
 * Custom Plane navigation entries in the shape of `ProjectNavigation`'s `additionalNavigationItems`
 * prop (an upstream injection point). A module-level function keeps its identity stable for the
 * component's `useMemo` dependencies.
 */
export const getCustomNavigationItems = (workspaceSlug: string, projectId: string): TNavigationItem[] => [
  getMilestonesNavigationItem(workspaceSlug, projectId),
];
