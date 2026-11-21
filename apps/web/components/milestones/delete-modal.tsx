/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { MilestoneService } from "@/services/milestone.service";
import type { TMilestone } from "./types";

const milestoneService = new MilestoneService();

type Props = {
  data: TMilestone | null;
  isOpen: boolean;
  workspaceSlug: string;
  projectId: string;
  onClose: () => void;
  onDeleted: () => void;
};

export function DeleteMilestoneModal(props: Props) {
  const { data, isOpen, workspaceSlug, projectId, onClose, onDeleted } = props;
  const [isDeleting, setIsDeleting] = useState(false);
  const { t } = useTranslation();

  const handleDelete = async () => {
    if (!data) return;
    setIsDeleting(true);
    try {
      await milestoneService.deleteMilestone(workspaceSlug, projectId, data.id);
      setToast({ type: "success", title: t("success"), message: t("milestone.toast_deleted") });
      onDeleted();
      onClose();
    } catch {
      setToast({ type: "error", title: t("error"), message: t("something_went_wrong") });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <ConfirmDialog
      isOpen={isOpen}
      handleClose={onClose}
      handleSubmit={handleDelete}
      isSubmitting={isDeleting}
      title={t("milestone.delete_title")}
      content={
        <>
          <span className="font-medium break-all text-primary">{data?.name}</span>
          {" — "}
          {t("milestone.delete_description")}
        </>
      }
    />
  );
}
