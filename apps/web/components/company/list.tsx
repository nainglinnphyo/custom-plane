/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { DeleteOutline, EditOutline, MembersOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import { flattenDepartmentTree } from "./helpers";
import type { TDepartment, TTeam } from "./types";

type TRow = {
  id: string;
  name: string;
  description: string;
  memberCount: number;
  depth: number;
  badge?: string;
};

type Props = {
  rows: TRow[];
  canEdit: boolean;
  onMembers: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
};

function OrgRows(props: Props) {
  const { rows, canEdit, onMembers, onEdit, onDelete } = props;
  const { t } = useTranslation();
  return (
    <ul className="flex flex-col divide-y divide-subtle rounded-lg border border-subtle bg-layer-1">
      {rows.map((row) => (
        <li key={row.id} className="flex items-center justify-between gap-3 px-4 py-3" data-testid="org-row">
          <div className="min-w-0" style={{ paddingLeft: `${row.depth * 20}px` }}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="truncate text-14 font-medium text-primary">{row.name}</span>
              {row.badge && (
                <span className="rounded bg-layer-3 px-1.5 py-0.5 text-11 text-secondary">{row.badge}</span>
              )}
              <span className="text-12 text-secondary">{t("company.members_count", { count: row.memberCount })}</span>
            </div>
            {row.description && <p className="mt-0.5 line-clamp-2 text-13 text-secondary">{row.description}</p>}
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <IconButton
              variant="ghost"
              size="sm"
              icon={<Icon icon={MembersOutline} />}
              aria-label={t("company.manage_members")}
              onClick={() => onMembers(row.id)}
            />
            {canEdit && (
              <>
                <IconButton
                  variant="ghost"
                  size="sm"
                  icon={<Icon icon={EditOutline} />}
                  aria-label={t("edit")}
                  onClick={() => onEdit(row.id)}
                />
                <IconButton
                  variant="ghost"
                  size="sm"
                  icon={<Icon icon={DeleteOutline} />}
                  aria-label={t("delete")}
                  onClick={() => onDelete(row.id)}
                />
              </>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

type DepartmentListProps = Omit<Props, "rows"> & { departments: TDepartment[] };

export function DepartmentList(props: DepartmentListProps) {
  const { departments, ...rest } = props;
  const rows = flattenDepartmentTree(departments).map((d) => ({
    id: d.id,
    name: d.name,
    description: d.description,
    memberCount: d.member_count,
    depth: d.depth,
  }));
  return <OrgRows rows={rows} {...rest} />;
}

type TeamListProps = Omit<Props, "rows"> & { teams: TTeam[]; departments: TDepartment[] };

export function TeamList(props: TeamListProps) {
  const { teams, departments, ...rest } = props;
  const nameById = new Map(departments.map((d) => [d.id, d.name]));
  const rows = [...teams]
    // oxlint-disable-next-line unicorn/no-array-sort -- toSorted is not in this app's TS lib target
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((team) => ({
      id: team.id,
      name: team.name,
      description: team.description,
      memberCount: team.member_count,
      depth: 0,
      badge: team.department ? nameById.get(team.department) : undefined,
    }));
  return <OrgRows rows={rows} {...rest} />;
}
