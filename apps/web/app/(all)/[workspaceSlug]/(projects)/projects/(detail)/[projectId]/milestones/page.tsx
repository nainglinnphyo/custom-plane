/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
// components
import { MilestonesRoot } from "@/components/milestones";
import { PageHead } from "@/components/core/page-title";
// hooks
import { useProject } from "@/hooks/store/use-project";
import type { Route } from "./+types/page";

function ProjectMilestonesPage({ params }: Route.ComponentProps) {
  const { workspaceSlug, projectId } = params;
  const { t } = useTranslation();
  const { getProjectById } = useProject();
  const project = getProjectById(projectId);
  const pageTitle = project?.name ? `${project.name} - ${t("milestones")}` : undefined;

  return (
    <>
      <PageHead title={pageTitle} />
      <MilestonesRoot workspaceSlug={workspaceSlug} projectId={projectId} />
    </>
  );
}

export default observer(ProjectMilestonesPage);
