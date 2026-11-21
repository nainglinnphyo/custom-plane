/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { InputField } from "@makeplane/propel/components/input-field";
import { SelectField } from "@makeplane/propel/components/select-field";
import { TextAreaField } from "@makeplane/propel/components/text-area-field";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { CompanyService } from "@/services/company.service";
// local imports
import { getApiErrorMessage, getParentOptions } from "./helpers";
import type { TDepartment, TTeam } from "./types";

const companyService = new CompanyService();
const NONE = "__none__";

type Props = {
  kind: "department" | "team";
  isOpen: boolean;
  workspaceSlug: string;
  /** all departments of the workspace: parent options for departments, department options for teams */
  departments: TDepartment[];
  data?: TDepartment | TTeam | null;
  onClose: () => void;
  onSaved: () => void;
};

/** One dialog for creating/editing either a department (with a parent) or a team (with a department). */
export function EntityModal(props: Props) {
  const { kind, isOpen, workspaceSlug, departments, data, onClose, onSaved } = props;
  return (
    <Dialog
      open={isOpen}
      disablePointerDismissal
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="md">
        {/* keyed so the form state resets between records */}
        <EntityForm
          key={data?.id ?? "new"}
          kind={kind}
          workspaceSlug={workspaceSlug}
          departments={departments}
          data={data}
          onClose={onClose}
          onSaved={onSaved}
        />
      </DialogContent>
    </Dialog>
  );
}

function EntityForm(props: Omit<Props, "isOpen">) {
  const { kind, workspaceSlug, departments, data, onClose, onSaved } = props;
  const { t } = useTranslation();
  const isDepartment = kind === "department";
  const initialLink = data ? (isDepartment ? (data as TDepartment).parent : (data as TTeam).department) : null;
  const [name, setName] = useState(data?.name ?? "");
  const [description, setDescription] = useState(data?.description ?? "");
  const [link, setLink] = useState<string>(initialLink ?? NONE);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const linkOptions = [
    { value: NONE, label: isDepartment ? t("company.top_level") : t("none") },
    ...(isDepartment ? getParentOptions(departments, data?.id) : departments).map((d) => ({
      value: d.id,
      label: "depth" in d ? `${"– ".repeat(d.depth as number)}${d.name}` : d.name,
    })),
  ];

  const title = isDepartment
    ? data
      ? t("company.edit_department")
      : t("company.add_department")
    : data
      ? t("company.edit_team")
      : t("company.add_team");

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    const linkValue = link === NONE ? null : link;
    try {
      if (isDepartment) {
        const payload = { name: name.trim(), description, parent: linkValue };
        if (data) await companyService.updateDepartment(workspaceSlug, data.id, payload);
        else await companyService.createDepartment(workspaceSlug, payload);
      } else {
        const payload = { name: name.trim(), description, department: linkValue };
        if (data) await companyService.updateTeam(workspaceSlug, data.id, payload);
        else await companyService.createTeam(workspaceSlug, payload);
      }
      setToast({ type: "success", title: t("success"), message: t("company.toast_saved") });
      onSaved();
      onClose();
    } catch (error) {
      setToast({ type: "error", title: t("error"), message: getApiErrorMessage(error, t("something_went_wrong")) });
    } finally {
      setIsSubmitting(false);
    }
  };

  const namePlaceholder = isDepartment ? t("company.department_name_placeholder") : t("company.team_name_placeholder");

  return (
    <form className="flex min-h-0 flex-1 flex-col" onSubmit={handleSubmit}>
      <DialogMain>
        <DialogHeader>
          <DialogHeading>
            <DialogTitle>{title}</DialogTitle>
          </DialogHeading>
        </DialogHeader>
        <DialogBody tabIndex={0}>
          <div className="space-y-3">
            <InputField
              size="xl"
              orientation="vertical"
              name="name"
              type="text"
              placeholder={namePlaceholder}
              aria-label={namePlaceholder}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <TextAreaField
              size="xl"
              autoResize
              maxRows={6}
              name="description"
              placeholder={t("description")}
              aria-label={t("description")}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <SelectField
              size="lg"
              aria-label={isDepartment ? t("company.parent_department") : t("company.department")}
              label={isDepartment ? t("company.parent_department") : t("company.department")}
              value={link}
              onValueChange={(value) => {
                if (value !== null) setLink(value);
              }}
              options={linkOptions}
            />
          </div>
        </DialogBody>
      </DialogMain>
      <DialogActions>
        <Button variant="secondary" size="md" stretch="auto" onClick={onClose} label={t("cancel")} />
        <Button
          variant="primary"
          size="md"
          stretch="auto"
          type="submit"
          disabled={!name.trim()}
          loading={isSubmitting}
          label={isSubmitting ? t("saving") : t("save")}
        />
      </DialogActions>
    </form>
  );
}
