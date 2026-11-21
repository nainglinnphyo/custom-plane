/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { ConfirmDialog } from "@plane/blocks/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { OrganizationService } from "@/services/organization.service";
import { getApiErrorMessage } from "./helpers";

const organizationService = new OrganizationService();

type Props = {
  kind: "department" | "team";
  target: { id: string; name: string } | null;
  workspaceSlug: string;
  onClose: () => void;
  onDeleted: () => void;
};

export function DeleteEntityModal(props: Props) {
  const { kind, target, workspaceSlug, onClose, onDeleted } = props;
  const { t } = useTranslation();
  const [isDeleting, setIsDeleting] = useState(false);
  const isDepartment = kind === "department";

  const handleDelete = async () => {
    if (!target) return;
    setIsDeleting(true);
    try {
      if (isDepartment) await organizationService.deleteDepartment(workspaceSlug, target.id);
      else await organizationService.deleteTeam(workspaceSlug, target.id);
      setToast({ type: "success", title: t("success"), message: t("organization.toast_deleted") });
      onDeleted();
      onClose();
    } catch (error) {
      // e.g. a department that still has sub-departments
      setToast({ type: "error", title: t("error"), message: getApiErrorMessage(error, t("something_went_wrong")) });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <ConfirmDialog
      isOpen={!!target}
      handleClose={onClose}
      handleSubmit={handleDelete}
      isSubmitting={isDeleting}
      title={isDepartment ? t("organization.delete_department_title") : t("organization.delete_team_title")}
      content={
        <>
          <span className="font-medium break-all text-primary">{target?.name}</span>
          {" — "}
          {isDepartment ? t("organization.delete_department_description") : t("organization.delete_team_description")}
        </>
      }
    />
  );
}
