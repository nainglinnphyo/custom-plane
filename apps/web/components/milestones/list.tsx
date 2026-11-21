/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Badge } from "@makeplane/propel/components/badge";
import { Icon } from "@makeplane/propel/components/icon";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { DeleteOutline, EditOutline } from "@makeplane/propel/icons";
import { useTranslation } from "@plane/i18n";
import { cn, renderFormattedDate } from "@plane/utils";
// local imports
import {
  MILESTONE_BAR_CLASS,
  MILESTONE_STATUS_META,
  getBarPosition,
  getTimelineRange,
  getTodayPercent,
} from "./helpers";
import type { TMilestone } from "./types";

type Props = {
  milestones: TMilestone[];
  canEdit: boolean;
  onEdit: (milestone: TMilestone) => void;
  onDelete: (milestone: TMilestone) => void;
};

/** Milestones with a shared timeline: every row draws its own span on the same date axis. */
export function MilestoneList(props: Props) {
  const { milestones, canEdit, onEdit, onDelete } = props;
  const { t } = useTranslation();

  const range = getTimelineRange(milestones);
  const todayPercent = range ? getTodayPercent(range) : null;

  return (
    <ul className="flex flex-col gap-3">
      {milestones.map((milestone) => {
        const meta = MILESTONE_STATUS_META[milestone.status];
        const bar = range ? getBarPosition(milestone, range) : null;
        const { total, completed, percent } = milestone.progress;
        return (
          <li
            key={milestone.id}
            className="flex flex-col gap-3 rounded-lg border border-subtle bg-layer-1 p-4"
            data-testid="milestone-row"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="truncate text-14 font-medium text-primary">{milestone.name}</h3>
                  <Badge size="sm" variant={meta.variant} label={t(meta.i18nKey)} />
                  {milestone.is_at_risk && <Badge size="sm" variant="warning" label={t("common.at_risk")} />}
                </div>
                {milestone.description && (
                  <p className="mt-1 line-clamp-2 text-13 text-secondary">{milestone.description}</p>
                )}
              </div>
              {canEdit && (
                <div className="flex shrink-0 items-center gap-1">
                  <IconButton
                    variant="ghost"
                    size="sm"
                    icon={<Icon icon={EditOutline} />}
                    aria-label={t("edit")}
                    onClick={() => onEdit(milestone)}
                  />
                  <IconButton
                    variant="ghost"
                    size="sm"
                    icon={<Icon icon={DeleteOutline} />}
                    aria-label={t("delete")}
                    onClick={() => onDelete(milestone)}
                  />
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-12 text-secondary">
              <span>{t("milestone.due_on", { date: renderFormattedDate(milestone.due_date) })}</span>
              {total > 0 && <span>{t("module.details_drawer.progress.done", { completed, scope: total })}</span>}
            </div>

            {total > 0 && (
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-layer-3" aria-hidden="true">
                <div className="h-full rounded-full bg-success-primary" style={{ width: `${percent}%` }} />
              </div>
            )}

            {bar && (
              <div className="relative h-3 w-full rounded bg-layer-3" aria-hidden="true">
                {todayPercent !== null && (
                  <div className="absolute inset-y-0 w-px bg-accent-primary" style={{ left: `${todayPercent}%` }} />
                )}
                <div
                  className={cn("absolute inset-y-0.5 rounded", MILESTONE_BAR_CLASS[milestone.status])}
                  style={{ left: `${bar.leftPercent}%`, width: `${bar.widthPercent}%` }}
                />
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
