/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { EUserWorkspaceRoles } from "@plane/types";
import type { IWorkspaceSidebarNavigationItem } from "./workspace";

/**
 * Custom Plane entries for the workspace sidebar. Kept out of workspace.ts so that file only needs a
 * single spread (`...CUSTOM_WORKSPACE_SIDEBAR_NAVIGATION_ITEMS_LINKS`) to include them.
 */
export const CUSTOM_WORKSPACE_SIDEBAR_NAVIGATION_ITEMS_LINKS: IWorkspaceSidebarNavigationItem[] = [
  {
    key: "organization",
    labelTranslationKey: "organization.nav_label",
    href: `/organization/`,
    access: [EUserWorkspaceRoles.ADMIN, EUserWorkspaceRoles.MEMBER],
    highlight: (pathname: string, url: string) => pathname.includes(url),
  },
];
