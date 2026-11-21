# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Business rules for milestones. Views and tasks call these; they never duplicate the rules."""

from datetime import date
from typing import Optional

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q

from plane.db.models import Issue
from plane.db.models.state import StateGroup

from .models import Milestone, MilestoneDependency, MilestoneIssue, MilestoneStatus


class MilestoneError(Exception):
    """Raised for rule violations; ``message`` is safe to return to API clients."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


# --------------------------------------------------------------------------- status


def derive_status(total: int, completed: int, cancelled: int, started: int, due_date: date, today: date) -> str:
    """Pure status rule.

    * no linked work items                     -> planned
    * all items done/cancelled, >=1 completed   -> achieved
    * otherwise, due date passed                -> missed
    * otherwise, any item started or completed  -> in_progress
    * otherwise                                 -> planned
    """
    if total == 0:
        return MilestoneStatus.PLANNED.value
    if completed >= 1 and completed + cancelled == total:
        return MilestoneStatus.ACHIEVED.value
    if due_date < today:
        return MilestoneStatus.MISSED.value
    if started + completed > 0:
        return MilestoneStatus.IN_PROGRESS.value
    return MilestoneStatus.PLANNED.value


def annotate_progress(queryset):
    """Annotate milestones with work-item counts and the at-risk flag in one query.

    Only visible work items count: soft-deleted, archived, draft and triage items are excluded,
    consistent with ``Issue.issue_objects``.
    """
    link = Q(
        milestone_issues__deleted_at__isnull=True,
        milestone_issues__issue__deleted_at__isnull=True,
        milestone_issues__issue__archived_at__isnull=True,
        milestone_issues__issue__is_draft=False,
    ) & ~Q(milestone_issues__issue__state__group=StateGroup.TRIAGE.value)

    open_late = Exists(
        MilestoneIssue.objects.filter(
            milestone=OuterRef("pk"),
            issue__deleted_at__isnull=True,
            issue__archived_at__isnull=True,
            issue__is_draft=False,
            issue__target_date__gt=OuterRef("due_date"),
        )
        .exclude(issue__state__group__in=[StateGroup.COMPLETED.value, StateGroup.CANCELLED.value])
        .exclude(issue__state__group=StateGroup.TRIAGE.value)
    )

    return queryset.annotate(
        total_issues=Count("milestone_issues", filter=link, distinct=True),
        completed_issues=Count(
            "milestone_issues",
            filter=link & Q(milestone_issues__issue__state__group=StateGroup.COMPLETED.value),
            distinct=True,
        ),
        cancelled_issues=Count(
            "milestone_issues",
            filter=link & Q(milestone_issues__issue__state__group=StateGroup.CANCELLED.value),
            distinct=True,
        ),
        started_issues=Count(
            "milestone_issues",
            filter=link & Q(milestone_issues__issue__state__group=StateGroup.STARTED.value),
            distinct=True,
        ),
        has_late_open_issue=open_late,
    )


def effective_status(milestone: Milestone, today: Optional[date] = None) -> str:
    """Status to show: the manual one if overridden, else derived from annotated counts."""
    if milestone.status_override:
        return milestone.status
    return derive_status(
        total=milestone.total_issues,
        completed=milestone.completed_issues,
        cancelled=milestone.cancelled_issues,
        started=milestone.started_issues,
        due_date=milestone.due_date,
        today=today or date.today(),
    )


def is_at_risk(milestone: Milestone, status: str) -> bool:
    """A milestone is at risk when it is not achieved and an open item is due after the milestone."""
    return status != MilestoneStatus.ACHIEVED.value and bool(milestone.has_late_open_issue)


def refresh_status(milestone_id) -> Optional[str]:
    """Persist the derived status for one milestone. Returns the new status (None if missing)."""
    milestone = annotate_progress(Milestone.objects.filter(pk=milestone_id)).first()
    if milestone is None or milestone.status_override:
        return milestone.status if milestone else None
    new_status = effective_status(milestone)
    if new_status != milestone.status:
        Milestone.objects.filter(pk=milestone.pk).update(status=new_status)
    return new_status


# ------------------------------------------------------------------------ work items


@transaction.atomic
def link_issues(milestone: Milestone, issue_ids) -> int:
    """Link work items of the milestone's own project. Returns the number newly linked.

    Raises ``MilestoneError`` if any id is not a visible work item of this project, so a caller
    cannot attach (or probe for) work items of another project or workspace.
    """
    issue_ids = {str(i) for i in issue_ids}
    valid = {
        str(pk)
        for pk in Issue.issue_objects.filter(
            id__in=issue_ids, project_id=milestone.project_id, workspace_id=milestone.workspace_id
        ).values_list("id", flat=True)
    }
    if valid != issue_ids:
        raise MilestoneError("One or more work items do not exist in this project.")

    existing = {
        str(pk)
        for pk in MilestoneIssue.objects.filter(milestone=milestone, issue_id__in=valid).values_list(
            "issue_id", flat=True
        )
    }
    new = valid - existing
    MilestoneIssue.objects.bulk_create(
        [
            MilestoneIssue(
                milestone=milestone, issue_id=i, project_id=milestone.project_id, workspace_id=milestone.workspace_id
            )
            for i in new
        ]
    )
    refresh_status(milestone.pk)
    return len(new)


def unlink_issue(milestone: Milestone, issue_id) -> bool:
    link = MilestoneIssue.objects.filter(milestone=milestone, issue_id=issue_id).first()
    if link is None:
        return False
    link.delete()
    refresh_status(milestone.pk)
    return True


# --------------------------------------------------------------------- dependencies


def _depends_transitively(start_id, target_id) -> bool:
    """True if ``start_id`` (transitively) depends on ``target_id``."""
    seen, stack = set(), [start_id]
    while stack:
        current = stack.pop()
        if current == target_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(MilestoneDependency.objects.filter(milestone_id=current).values_list("depends_on_id", flat=True))
    return False


@transaction.atomic
def add_dependency(milestone: Milestone, depends_on: Milestone) -> MilestoneDependency:
    if milestone.pk == depends_on.pk:
        raise MilestoneError("A milestone cannot depend on itself.")
    if milestone.project_id != depends_on.project_id:
        raise MilestoneError("Dependencies must be between milestones of the same project.")
    if MilestoneDependency.objects.filter(milestone=milestone, depends_on=depends_on).exists():
        raise MilestoneError("This dependency already exists.")
    # Adding milestone -> depends_on closes a cycle iff depends_on already depends on milestone.
    if _depends_transitively(depends_on.pk, milestone.pk):
        raise MilestoneError("This dependency would create a cycle.")
    return MilestoneDependency.objects.create(
        milestone=milestone, depends_on=depends_on, project_id=milestone.project_id, workspace_id=milestone.workspace_id
    )
