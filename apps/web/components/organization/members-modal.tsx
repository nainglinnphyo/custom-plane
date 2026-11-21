/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { Button } from "@makeplane/propel/components/button";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogHeading,
  DialogMain,
  DialogTitle,
} from "@makeplane/propel/components/dialog";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { SelectField } from "@makeplane/propel/components/select-field";
import { DeleteOutline } from "@makeplane/propel/icons";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { OrganizationService } from "@/services/organization.service";
// local imports
import { getApiErrorMessage } from "./helpers";
import type { TMembersKind, TOrgRole } from "./types";

const organizationService = new OrganizationService();

type Props = {
  isOpen: boolean;
  workspaceSlug: string;
  kind: TMembersKind;
  entityId: string;
  entityName: string;
  canEdit: boolean;
  onClose: () => void;
  /** roster changed: lets the list refresh its member counts */
  onChanged: () => void;
};

export const MembersModal = observer(function MembersModal(props: Props) {
  const { isOpen, workspaceSlug, kind, entityId, entityName, canEdit, onClose, onChanged } = props;
  const { t } = useTranslation();
  const {
    workspace: { workspaceMemberIds, fetchWorkspaceMembers },
    getUserDetails,
  } = useMember();
  const [newMember, setNewMember] = useState<string | null>(null);
  const [newRole, setNewRole] = useState<TOrgRole>("member");
  const [isAdding, setIsAdding] = useState(false);

  const { data: roster, mutate } = useSWR(isOpen ? ["custom-members", kind, entityId] : null, () =>
    organizationService.getMembers(workspaceSlug, kind, entityId)
  );
  // the workspace member list may not be in the store yet (it is when the members settings page was visited)
  useSWR(isOpen && !workspaceMemberIds ? ["custom-workspace-members", workspaceSlug] : null, () =>
    fetchWorkspaceMembers(workspaceSlug)
  );

  const roleOptions = [
    { value: "lead", label: t("lead") },
    { value: "member", label: t("common.member") },
  ];

  const candidates = useMemo(() => {
    const taken = new Set((roster ?? []).map((m) => m.member));
    return (workspaceMemberIds ?? [])
      .filter((id) => !taken.has(id))
      .map((id) => ({ value: id, label: getUserDetails(id)?.display_name ?? id }));
  }, [roster, workspaceMemberIds, getUserDetails]);

  const run = async (action: () => Promise<unknown>) => {
    try {
      await action();
      await mutate();
      onChanged();
    } catch (error) {
      setToast({ type: "error", title: t("error"), message: getApiErrorMessage(error, t("something_went_wrong")) });
    }
  };

  const handleAdd = async () => {
    if (!newMember) return;
    setIsAdding(true);
    await run(() => organizationService.addMember(workspaceSlug, kind, entityId, newMember, newRole));
    setNewMember(null);
    setIsAdding(false);
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent size="md">
        <DialogMain>
          <DialogHeader>
            <DialogHeading>
              <DialogTitle>
                {t("organization.manage_members")} — {entityName}
              </DialogTitle>
            </DialogHeading>
          </DialogHeader>
          <DialogBody tabIndex={0}>
            <div className="space-y-4">
              {canEdit && (
                <div className="flex flex-wrap items-end gap-2">
                  <div className="min-w-48 flex-1">
                    <SelectField
                      size="lg"
                      aria-label={t("organization.select_member")}
                      placeholder={t("organization.select_member")}
                      value={newMember}
                      onValueChange={(value) => setNewMember(value)}
                      options={candidates}
                    />
                  </div>
                  <SelectField
                    size="lg"
                    aria-label={t("role")}
                    value={newRole}
                    onValueChange={(value) => {
                      if (value === "lead" || value === "member") setNewRole(value);
                    }}
                    options={roleOptions}
                  />
                  <Button
                    variant="primary"
                    size="md"
                    stretch="auto"
                    label={t("add_member")}
                    disabled={!newMember}
                    loading={isAdding}
                    onClick={() => void handleAdd()}
                  />
                </div>
              )}
              {roster && roster.length === 0 && (
                <p className="text-13 text-secondary">{t("organization.no_members")}</p>
              )}
              <ul className="flex flex-col divide-y divide-subtle">
                {(roster ?? []).map((row) => (
                  <li key={row.id} className="flex items-center justify-between gap-3 py-2" data-testid="member-row">
                    <span className="truncate text-13 text-primary">{row.display_name || row.member}</span>
                    <div className="flex items-center gap-2">
                      {canEdit ? (
                        <SelectField
                          size="md"
                          aria-label={t("role")}
                          value={row.role}
                          onValueChange={(value) => {
                            if (value !== "lead" && value !== "member") return;
                            void run(() =>
                              organizationService.setMemberRole(workspaceSlug, kind, entityId, row.member, value)
                            );
                          }}
                          options={roleOptions}
                        />
                      ) : (
                        <span className="text-12 text-secondary">
                          {row.role === "lead" ? t("lead") : t("common.member")}
                        </span>
                      )}
                      {canEdit && (
                        <IconButton
                          variant="ghost"
                          size="sm"
                          icon={<Icon icon={DeleteOutline} />}
                          aria-label={t("remove")}
                          onClick={() =>
                            void run(() => organizationService.removeMember(workspaceSlug, kind, entityId, row.member))
                          }
                        />
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </DialogBody>
        </DialogMain>
      </DialogContent>
    </Dialog>
  );
});
