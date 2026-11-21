/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Dialog, DialogContent } from "@makeplane/propel/components/dialog";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { MilestoneService } from "@/services/milestone.service";
// local imports
import { MilestoneForm } from "./form";
import type { TMilestone, TMilestoneFormValues } from "./types";

const milestoneService = new MilestoneService();

type Props = {
  isOpen: boolean;
  handleClose: () => void;
  workspaceSlug: string;
  projectId: string;
  data?: TMilestone | null;
  /** Called after a successful save so the caller can revalidate its list. */
  onSaved: () => void;
};

/** The API reports validation problems as `{field: [messages]}` or `{error: message}`. */
const getErrorMessage = (error: unknown, fallback: string): string => {
  if (!error || typeof error !== "object") return fallback;
  const first = Object.values(error as Record<string, unknown>)[0];
  if (typeof first === "string") return first;
  if (Array.isArray(first) && typeof first[0] === "string") return first[0];
  return fallback;
};

export function MilestoneCreateUpdateModal(props: Props) {
  const { isOpen, handleClose, workspaceSlug, projectId, data, onSaved } = props;
  const { t } = useTranslation();

  const handleFormSubmit = async (values: TMilestoneFormValues) => {
    if (!values.due_date) return;
    const payload = {
      name: values.name.trim(),
      description: values.description,
      start_date: values.start_date,
      due_date: values.due_date,
    };
    try {
      if (data) await milestoneService.updateMilestone(workspaceSlug, projectId, data.id, payload);
      else await milestoneService.createMilestone(workspaceSlug, projectId, payload);
      setToast({ type: "success", title: t("success"), message: t("milestone.toast_saved") });
      onSaved();
      handleClose();
    } catch (error) {
      setToast({
        type: "error",
        title: t("error"),
        message: getErrorMessage(error, t("something_went_wrong")),
      });
    }
  };

  return (
    <Dialog
      open={isOpen}
      disablePointerDismissal
      onOpenChange={(open) => {
        if (!open) handleClose();
      }}
    >
      <DialogContent size="md">
        {/* keyed by milestone so the form's defaults reset when switching between milestones */}
        <MilestoneForm
          key={data?.id ?? "new"}
          data={data}
          handleFormSubmit={handleFormSubmit}
          handleClose={handleClose}
        />
      </DialogContent>
    </Dialog>
  );
}
