# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import date, timedelta

import pytest

from plane.custom.milestones.models import Milestone, MilestoneDependency
from plane.custom.milestones.services import (
    MilestoneError,
    add_dependency,
    annotate_progress,
    derive_status,
    effective_status,
    is_at_risk,
    link_issues,
    refresh_status,
    unlink_issue,
)
from plane.db.models import Issue, Project, ProjectMember, State

pytestmark = pytest.mark.unit

TODAY = date(2026, 6, 15)
FUTURE = TODAY + timedelta(days=10)
PAST = TODAY - timedelta(days=1)


class TestDeriveStatus:
    @pytest.mark.parametrize(
        "total,completed,cancelled,started,due,expected",
        [
            (0, 0, 0, 0, FUTURE, "planned"),  # empty
            (0, 0, 0, 0, PAST, "planned"),  # empty and overdue stays planned
            (3, 3, 0, 0, PAST, "achieved"),  # all done, even if late
            (3, 2, 1, 0, FUTURE, "achieved"),  # done + cancelled
            (2, 0, 2, 0, FUTURE, "planned"),  # all cancelled is not achieved
            (3, 1, 0, 0, PAST, "missed"),  # open work and overdue
            (3, 1, 0, 0, FUTURE, "in_progress"),  # some completed
            (3, 0, 0, 1, FUTURE, "in_progress"),  # some started
            (3, 0, 0, 0, FUTURE, "planned"),  # nothing started
            (3, 0, 0, 0, PAST, "missed"),  # nothing started and overdue
            (3, 0, 0, 0, TODAY, "planned"),  # due today is not yet overdue
        ],
    )
    def test_rules(self, total, completed, cancelled, started, due, expected):
        assert derive_status(total, completed, cancelled, started, due, TODAY) == expected


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="P", identifier="P", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def states(db, project):
    def make(name, group):
        return State.objects.create(name=name, group=group, project=project, workspace=project.workspace)

    return {g: make(g, g) for g in ["backlog", "unstarted", "started", "completed", "cancelled"]}


@pytest.fixture
def make_issue(db, project, states):
    def _make(group="unstarted", **kwargs):
        return Issue.objects.create(
            name=f"issue-{group}", project=project, workspace=project.workspace, state=states[group], **kwargs
        )

    return _make


@pytest.fixture
def make_milestone(db, project):
    def _make(name="M", due=FUTURE, **kwargs):
        return Milestone.objects.create(name=name, due_date=due, project=project, **kwargs)

    return _make


def annotated(milestone):
    return annotate_progress(Milestone.objects.filter(pk=milestone.pk)).get()


@pytest.mark.django_db
class TestLinkingAndProgress:
    def test_counts_and_status_follow_issue_states(self, make_milestone, make_issue):
        m = make_milestone(due=date.today() + timedelta(days=30))
        issues = [make_issue("completed"), make_issue("started"), make_issue("unstarted"), make_issue("cancelled")]
        assert link_issues(m, [i.id for i in issues]) == 4

        a = annotated(m)
        assert (a.total_issues, a.completed_issues, a.cancelled_issues, a.started_issues) == (4, 1, 1, 1)
        assert effective_status(a) == "in_progress"
        assert refresh_status(m.pk) == "in_progress"
        m.refresh_from_db()
        assert m.status == "in_progress"

    def test_link_is_idempotent(self, make_milestone, make_issue):
        m, i = make_milestone(), make_issue()
        assert link_issues(m, [i.id]) == 1
        assert link_issues(m, [i.id]) == 0

    def test_foreign_project_issue_rejected(self, make_milestone, workspace, create_user, states):
        other = Project.objects.create(name="O", identifier="O", workspace=workspace, created_by=create_user)
        state = State.objects.create(name="s", group="backlog", project=other, workspace=workspace)
        foreign = Issue.objects.create(name="x", project=other, workspace=workspace, state=state)
        with pytest.raises(MilestoneError):
            link_issues(make_milestone(), [foreign.id])

    def test_unknown_issue_rejected_and_nothing_linked(self, make_milestone, make_issue):
        from uuid import uuid4

        m, good = make_milestone(), make_issue()
        with pytest.raises(MilestoneError):
            link_issues(m, [good.id, uuid4()])
        assert annotated(m).total_issues == 0

    def test_archived_and_draft_issues_not_counted(self, make_milestone, make_issue):
        from django.utils import timezone

        m = make_milestone()
        visible, archived, draft = make_issue(), make_issue(), make_issue()
        link_issues(m, [visible.id, archived.id, draft.id])
        Issue.objects.filter(pk=archived.pk).update(archived_at=timezone.now().date())
        Issue.objects.filter(pk=draft.pk).update(is_draft=True)
        assert annotated(m).total_issues == 1

    def test_unlink(self, make_milestone, make_issue):
        m, i = make_milestone(), make_issue()
        link_issues(m, [i.id])
        assert unlink_issue(m, i.id) is True
        assert unlink_issue(m, i.id) is False
        assert annotated(m).total_issues == 0

    def test_manual_override_is_not_rederived(self, make_milestone, make_issue):
        m = make_milestone(status="missed", status_override=True)
        link_issues(m, [make_issue("completed").id])
        m.refresh_from_db()
        assert m.status == "missed"
        assert effective_status(annotated(m)) == "missed"

    def test_at_risk_when_open_issue_due_after_milestone(self, make_milestone, make_issue):
        m = make_milestone(due=TODAY + timedelta(days=30))
        late = make_issue("started", target_date=TODAY + timedelta(days=60))
        link_issues(m, [late.id])
        a = annotated(m)
        assert is_at_risk(a, effective_status(a)) is True

    def test_not_at_risk_when_late_issue_is_completed(self, make_milestone, make_issue):
        m = make_milestone(due=TODAY + timedelta(days=30))
        link_issues(m, [make_issue("completed", target_date=TODAY + timedelta(days=60)).id])
        a = annotated(m)
        assert is_at_risk(a, effective_status(a)) is False


@pytest.mark.django_db
class TestDependencies:
    def test_self_dependency_rejected(self, make_milestone):
        m = make_milestone("A")
        with pytest.raises(MilestoneError):
            add_dependency(m, m)

    def test_duplicate_rejected(self, make_milestone):
        a, b = make_milestone("A"), make_milestone("B")
        add_dependency(a, b)
        with pytest.raises(MilestoneError):
            add_dependency(a, b)

    def test_direct_and_transitive_cycles_rejected(self, make_milestone):
        a, b, c = make_milestone("A"), make_milestone("B"), make_milestone("C")
        add_dependency(a, b)  # a depends on b
        add_dependency(b, c)  # b depends on c
        with pytest.raises(MilestoneError):
            add_dependency(b, a)  # direct cycle
        with pytest.raises(MilestoneError):
            add_dependency(c, a)  # transitive cycle
        assert MilestoneDependency.objects.count() == 2

    def test_diamond_is_allowed(self, make_milestone):
        a, b, c, d = (make_milestone(n) for n in "ABCD")
        add_dependency(a, b)
        add_dependency(a, c)
        add_dependency(b, d)
        add_dependency(c, d)
        assert MilestoneDependency.objects.count() == 4

    def test_cross_project_rejected(self, make_milestone, workspace, create_user):
        other = Project.objects.create(name="O", identifier="O", workspace=workspace, created_by=create_user)
        foreign = Milestone.objects.create(name="F", due_date=FUTURE, project=other)
        with pytest.raises(MilestoneError):
            add_dependency(make_milestone("A"), foreign)
