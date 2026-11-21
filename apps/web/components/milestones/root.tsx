/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import { AddOutline } from "@makeplane/propel/icons";
import { EUserPermissionsLevel, PROJECT_MILESTONES } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EUserProjectRoles } from "@plane/types";
// components
import { DetailedEmptyState } from "@/components/empty-state/detailed-empty-state-root";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
// services
import { MilestoneService } from "@/services/milestone.service";
// local imports
import { DeleteMilestoneModal } from "./delete-modal";
import { MilestoneList } from "./list";
import { MilestoneCreateUpdateModal } from "./modal";
import type { TMilestone } from "./types";

const milestoneService = new MilestoneService();

type Props = {
  workspaceSlug: string;
  projectId: string;
};

export const MilestonesRoot = observer(function MilestonesRoot(props: Props) {
  const { workspaceSlug, projectId } = props;
  // states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<TMilestone | null>(null);
  const [deleting, setDeleting] = useState<TMilestone | null>(null);
  // hooks
  const { t } = useTranslation();
  const { allowPermissions, getProjectRoleByWorkspaceSlugAndProjectId } = useUserPermissions();
  // derived values
  const canEdit = allowPermissions(
    [EUserProjectRoles.ADMIN, EUserProjectRoles.MEMBER],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug,
    projectId
  );
  const projectRole = getProjectRoleByWorkspaceSlugAndProjectId(workspaceSlug, projectId);

  const {
    data: milestones,
    error,
    isLoading,
    mutate,
  } = useSWR(PROJECT_MILESTONES(projectId, projectRole), () =>
    milestoneService.getMilestones(workspaceSlug, projectId)
  );

  const openCreate = () => {
    setEditing(null);
    setIsModalOpen(true);
  };

  if (isLoading) {
    return <div className="py-10 text-center text-13 text-secondary">{t("loading")}</div>;
  }
  if (error || !milestones) {
    return <div className="py-10 text-center text-13 text-secondary">{t("something_went_wrong")}</div>;
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4">
      {milestones.length === 0 ? (
        <div className="flex h-full w-full items-center justify-center py-16">
          <DetailedEmptyState
            title={t("milestone.empty_title")}
            description={t("milestone.empty_description")}
            primaryButton={
              canEdit
                ? { text: t("milestone.add"), prependIcon: <AddOutline className="size-4" />, onClick: openCreate }
                : undefined
            }
          />
        </div>
      ) : (
        <>
          {canEdit && (
            <div className="flex justify-end">
              <Button
                variant="primary"
                size="md"
                stretch="auto"
                label={t("milestone.add")}
                onClick={openCreate}
                icon={<AddOutline className="size-4" />}
              />
            </div>
          )}
          <MilestoneList
            milestones={milestones}
            canEdit={canEdit}
            onEdit={(milestone) => {
              setEditing(milestone);
              setIsModalOpen(true);
            }}
            onDelete={setDeleting}
          />
        </>
      )}

      <MilestoneCreateUpdateModal
        isOpen={isModalOpen}
        handleClose={() => {
          setIsModalOpen(false);
          setEditing(null);
        }}
        workspaceSlug={workspaceSlug}
        projectId={projectId}
        data={editing}
        onSaved={() => void mutate()}
      />
      <DeleteMilestoneModal
        isOpen={!!deleting}
        data={deleting}
        workspaceSlug={workspaceSlug}
        projectId={projectId}
        onClose={() => setDeleting(null)}
        onDeleted={() => void mutate()}
      />
    </div>
  );
});
