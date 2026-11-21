/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { layout, route } from "@react-router/dev/routes";
import type { RouteConfigEntry } from "@react-router/dev/routes";

// Custom Plane routes. `mergeRoutes` (see helper.ts) deep-merges layouts that share a file with
// the core routes, so these mirror the core nesting down to the project-detail layout.
export const extendedRoutes: RouteConfigEntry[] = [
  layout("./(all)/layout.tsx", [
    layout("./(all)/[workspaceSlug]/layout.tsx", [
      layout("./(all)/[workspaceSlug]/(projects)/layout.tsx", [
        layout("./(all)/[workspaceSlug]/(projects)/projects/(detail)/[projectId]/layout.tsx", [
          // Milestones
          layout("./(all)/[workspaceSlug]/(projects)/projects/(detail)/[projectId]/milestones/layout.tsx", [
            route(
              ":workspaceSlug/projects/:projectId/milestones",
              "./(all)/[workspaceSlug]/(projects)/projects/(detail)/[projectId]/milestones/page.tsx"
            ),
          ]),
        ]),
      ]),
    ]),
  ]),
];
