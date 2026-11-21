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
import { EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EUserWorkspaceRoles } from "@plane/types";
// components
import { DetailedEmptyState } from "@/components/empty-state/detailed-empty-state-root";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
// services
import { CompanyService } from "@/services/company.service";
// local imports
import { DeleteEntityModal } from "./delete-modal";
import { EntityModal } from "./entity-modal";
import { DepartmentList, TeamList } from "./list";
import { MembersModal } from "./members-modal";
import type { TDepartment, TMembersKind, TTeam } from "./types";

const companyService = new CompanyService();

type TTab = "departments" | "teams";

type Props = { workspaceSlug: string };

export const CompanyRoot = observer(function CompanyRoot(props: Props) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  const { allowPermissions } = useUserPermissions();
  const [tab, setTab] = useState<TTab>("departments");
  const [editing, setEditing] = useState<{ kind: "department" | "team"; data: TDepartment | TTeam | null } | null>(
    null
  );
  const [deleting, setDeleting] = useState<{ kind: "department" | "team"; id: string; name: string } | null>(null);
  const [membersFor, setMembersFor] = useState<{ kind: TMembersKind; id: string; name: string } | null>(null);

  const canEdit = allowPermissions([EUserWorkspaceRoles.ADMIN], EUserPermissionsLevel.WORKSPACE, workspaceSlug);
  const canRead = allowPermissions(
    [EUserWorkspaceRoles.ADMIN, EUserWorkspaceRoles.MEMBER],
    EUserPermissionsLevel.WORKSPACE,
    workspaceSlug
  );

  const departments = useSWR(canRead ? ["custom-departments", workspaceSlug] : null, () =>
    companyService.getDepartments(workspaceSlug)
  );
  const teams = useSWR(canRead ? ["custom-teams", workspaceSlug] : null, () => companyService.getTeams(workspaceSlug));

  if (!canRead) {
    return <div className="py-10 text-center text-13 text-secondary">{t("something_went_wrong")}</div>;
  }
  if (departments.isLoading || teams.isLoading) {
    return <div className="py-10 text-center text-13 text-secondary">{t("loading")}</div>;
  }
  if (departments.error || teams.error || !departments.data || !teams.data) {
    return <div className="py-10 text-center text-13 text-secondary">{t("something_went_wrong")}</div>;
  }

  const departmentList = departments.data;
  const teamList = teams.data;
  const isDepartmentTab = tab === "departments";
  const items = isDepartmentTab ? departmentList : teamList;

  const refreshAll = () => {
    void departments.mutate();
    void teams.mutate();
  };

  const openCreate = () => setEditing({ kind: isDepartmentTab ? "department" : "team", data: null });
  const findEntity = (id: string) => items.find((i) => i.id === id);

  const listProps = {
    canEdit,
    onMembers: (id: string) => {
      const entity = findEntity(id);
      if (entity) setMembersFor({ kind: tab, id, name: entity.name });
    },
    onEdit: (id: string) => {
      const entity = findEntity(id);
      if (entity) setEditing({ kind: isDepartmentTab ? "department" : "team", data: entity });
    },
    onDelete: (id: string) => {
      const entity = findEntity(id);
      if (entity) setDeleting({ kind: isDepartmentTab ? "department" : "team", id, name: entity.name });
    },
  };

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1" role="tablist">
          {(["departments", "teams"] as const).map((key) => (
            <Button
              key={key}
              role="tab"
              aria-selected={tab === key}
              variant={tab === key ? "secondary" : "ghost"}
              size="md"
              stretch="auto"
              label={key === "departments" ? t("company.departments") : t("common.teams")}
              onClick={() => setTab(key)}
            />
          ))}
        </div>
        {canEdit && items.length > 0 && (
          <Button
            variant="primary"
            size="md"
            stretch="auto"
            label={isDepartmentTab ? t("company.add_department") : t("company.add_team")}
            icon={<AddOutline className="size-4" />}
            onClick={openCreate}
          />
        )}
      </div>

      {items.length === 0 ? (
        <div className="flex w-full items-center justify-center py-12">
          <DetailedEmptyState
            title={isDepartmentTab ? t("company.empty_departments_title") : t("company.empty_teams_title")}
            description={
              isDepartmentTab ? t("company.empty_departments_description") : t("company.empty_teams_description")
            }
            primaryButton={
              canEdit
                ? {
                    text: isDepartmentTab ? t("company.add_department") : t("company.add_team"),
                    prependIcon: <AddOutline className="size-4" />,
                    onClick: openCreate,
                  }
                : undefined
            }
          />
        </div>
      ) : isDepartmentTab ? (
        <DepartmentList departments={departmentList} {...listProps} />
      ) : (
        <TeamList teams={teamList} departments={departmentList} {...listProps} />
      )}

      <EntityModal
        isOpen={!!editing}
        kind={editing?.kind ?? "department"}
        workspaceSlug={workspaceSlug}
        departments={departmentList}
        data={editing?.data ?? null}
        onClose={() => setEditing(null)}
        onSaved={refreshAll}
      />
      <DeleteEntityModal
        kind={deleting?.kind ?? "department"}
        target={deleting}
        workspaceSlug={workspaceSlug}
        onClose={() => setDeleting(null)}
        onDeleted={refreshAll}
      />
      {membersFor && (
        <MembersModal
          isOpen
          workspaceSlug={workspaceSlug}
          kind={membersFor.kind}
          entityId={membersFor.id}
          entityName={membersFor.name}
          canEdit={canEdit}
          onClose={() => setMembersFor(null)}
          onChanged={refreshAll}
        />
      )}
    </div>
  );
});
