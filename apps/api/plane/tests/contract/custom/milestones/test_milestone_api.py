# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import date, timedelta
import uuid
from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.custom.milestones.models import Milestone
from plane.db.models import Issue, Project, ProjectMember, State, User, Workspace, WorkspaceMember

pytestmark = pytest.mark.contract

FUTURE = (date.today() + timedelta(days=30)).isoformat()


def _user(prefix):
    uid = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{uid}@plane.so", username=f"{prefix}_{uid}")


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="P", identifier="PRJ", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def state(db, project):
    return State.objects.create(name="Todo", group="unstarted", project=project, workspace=project.workspace)


@pytest.fixture
def issue(db, project, state):
    return Issue.objects.create(name="Task", project=project, workspace=project.workspace, state=state)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def member_client(workspace, project, role, **project_kwargs):
    user = _user(f"role{role}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    ProjectMember.objects.create(project=project, member=user, role=role, is_active=True)
    return client_for(user), user


def base(workspace, project):
    return f"/api/custom/workspaces/{workspace.slug}/projects/{project.id}"


@pytest.mark.django_db
class TestCrud:
    def test_create_list_retrieve_update_delete(self, session_client, workspace, project):
        url = f"{base(workspace, project)}/milestones/"
        r = session_client.post(
            url, {"name": "Beta", "due_date": FUTURE, "start_date": date.today().isoformat()}, format="json"
        )
        assert r.status_code == status.HTTP_201_CREATED, r.data
        assert r.data["status"] == "planned" and r.data["progress"]["total"] == 0
        mid = r.data["id"]

        assert len(session_client.get(url).data) == 1
        assert session_client.get(f"{url}{mid}/").data["name"] == "Beta"

        r = session_client.patch(f"{url}{mid}/", {"name": "Beta 2"}, format="json")
        assert r.status_code == 200 and r.data["name"] == "Beta 2"

        assert session_client.delete(f"{url}{mid}/").status_code == 204
        assert session_client.get(url).data == []
        assert session_client.get(f"{url}{mid}/").status_code == 404

    def test_put_not_routed(self, session_client, workspace, project):
        m = Milestone.objects.create(name="A", due_date=date.today(), project=project)
        r = session_client.put(f"{base(workspace, project)}/milestones/{m.id}/", {"name": "x"}, format="json")
        assert r.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_validation(self, session_client, workspace, project):
        url = f"{base(workspace, project)}/milestones/"
        assert session_client.post(url, {"name": "X"}, format="json").status_code == 400  # due_date required
        bad = {"name": "X", "start_date": "2026-05-02", "due_date": "2026-05-01"}
        assert session_client.post(url, bad, format="json").status_code == 400
        assert session_client.post(url, {"name": "Dup", "due_date": FUTURE}, format="json").status_code == 201
        assert session_client.post(url, {"name": "dup", "due_date": FUTURE}, format="json").status_code == 400

    def test_owner_must_be_project_member(self, session_client, workspace, project):
        outsider = _user("out")
        r = session_client.post(
            f"{base(workspace, project)}/milestones/",
            {"name": "O", "due_date": FUTURE, "owner": str(outsider.id)},
            format="json",
        )
        assert r.status_code == 400

    def test_status_override_admin_only_and_clearable(self, session_client, workspace, project):
        url = f"{base(workspace, project)}/milestones/"
        mid = session_client.post(url, {"name": "S", "due_date": FUTURE}, format="json").data["id"]

        r = session_client.patch(f"{url}{mid}/", {"status": "achieved"}, format="json")
        assert r.status_code == 200 and r.data["status"] == "achieved" and r.data["status_override"] is True

        r = session_client.patch(f"{url}{mid}/", {"status": None}, format="json")
        assert r.data["status"] == "planned" and r.data["status_override"] is False

        member, _ = member_client(workspace, project, 15)
        r = member.patch(f"{url}{mid}/", {"status": "missed"}, format="json")
        assert r.status_code == 400


@pytest.mark.django_db
class TestPermissions:
    def test_anonymous_rejected(self, workspace, project):
        r = APIClient().get(f"{base(workspace, project)}/milestones/")
        assert r.status_code in (401, 403)

    def test_non_member_forbidden_for_every_verb(self, workspace, project):
        outsider = client_for(_user("outsider"))
        url = f"{base(workspace, project)}/milestones/"
        assert outsider.get(url).status_code == 403
        assert outsider.post(url, {"name": "X", "due_date": FUTURE}, format="json").status_code == 403
        assert outsider.get(f"{base(workspace, project)}/timeline/").status_code == 403

    def test_workspace_member_not_in_project_forbidden(self, workspace, project):
        user = _user("wsonly")
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
        assert client_for(user).get(f"{base(workspace, project)}/milestones/").status_code == 403

    def test_member_can_write_guest_read_only(self, workspace, project):
        url = f"{base(workspace, project)}/milestones/"
        member, _ = member_client(workspace, project, 15)
        assert member.post(url, {"name": "M", "due_date": FUTURE}, format="json").status_code == 201

        Project.objects.filter(pk=project.pk).update(guest_view_all_features=True)
        guest, _ = member_client(workspace, project, 5)
        assert guest.get(url).status_code == 200
        assert guest.post(url, {"name": "G", "due_date": FUTURE}, format="json").status_code == 403

    def test_restricted_guest_cannot_read(self, workspace, project):
        Project.objects.filter(pk=project.pk).update(guest_view_all_features=False)
        guest, _ = member_client(workspace, project, 5)
        assert guest.get(f"{base(workspace, project)}/milestones/").status_code == 403

    def test_inactive_member_forbidden(self, workspace, project):
        client, user = member_client(workspace, project, 15)
        ProjectMember.objects.filter(project=project, member=user).update(is_active=False)
        assert client.get(f"{base(workspace, project)}/milestones/").status_code == 403


@pytest.fixture
def other_tenant(db):
    owner = _user("victim")
    ws = Workspace.objects.create(name="Victim", owner=owner, slug=f"victim-{uuid4().hex[:6]}")
    WorkspaceMember.objects.create(workspace=ws, member=owner, role=20)
    project = Project.objects.create(name="V", identifier="VIC", workspace=ws, created_by=owner)
    ProjectMember.objects.create(project=project, member=owner, role=20, is_active=True)
    state = State.objects.create(name="s", group="backlog", project=project, workspace=ws)
    return {
        "ws": ws,
        "project": project,
        "milestone": Milestone.objects.create(name="Secret", due_date=date.today(), project=project),
        "issue": Issue.objects.create(name="Secret issue", project=project, workspace=ws, state=state),
    }


@pytest.mark.django_db
class TestTenantIsolation:
    def test_cannot_read_or_touch_foreign_milestone_via_own_project_url(
        self, session_client, workspace, project, other_tenant
    ):
        mid = other_tenant["milestone"].id
        url = f"{base(workspace, project)}/milestones/{mid}/"
        assert session_client.get(url).status_code == 404
        assert session_client.patch(url, {"name": "pwned"}, format="json").status_code == 404
        assert session_client.delete(url).status_code == 404
        other_tenant["milestone"].refresh_from_db()
        assert other_tenant["milestone"].name == "Secret" and other_tenant["milestone"].deleted_at is None

    def test_cannot_use_foreign_project_in_url(self, session_client, other_tenant):
        url = f"/api/custom/workspaces/{other_tenant['ws'].slug}/projects/{other_tenant['project'].id}/milestones/"
        assert session_client.get(url).status_code == 403

    def test_cannot_link_foreign_issue(self, session_client, workspace, project, other_tenant):
        m = Milestone.objects.create(name="Mine", due_date=date.today(), project=project)
        r = session_client.post(
            f"{base(workspace, project)}/milestones/{m.id}/issues/",
            {"issue_ids": [str(other_tenant["issue"].id)]},
            format="json",
        )
        assert r.status_code == 400
        assert not m.milestone_issues.exists()

    def test_cannot_depend_on_foreign_milestone(self, session_client, workspace, project, other_tenant):
        m = Milestone.objects.create(name="Mine", due_date=date.today(), project=project)
        r = session_client.post(
            f"{base(workspace, project)}/milestones/{m.id}/dependencies/",
            {"depends_on": str(other_tenant["milestone"].id)},
            format="json",
        )
        assert r.status_code == 400

    def test_timeline_only_returns_own_project(self, session_client, workspace, project, other_tenant):
        Milestone.objects.create(name="Mine", due_date=date.today(), project=project)
        data = session_client.get(f"{base(workspace, project)}/timeline/").data
        assert [m["name"] for m in data["milestones"]] == ["Mine"]


@pytest.mark.django_db
class TestIssuesAndDependencies:
    def test_link_list_unlink_and_progress(self, session_client, workspace, project, issue):
        url = f"{base(workspace, project)}/milestones/"
        mid = session_client.post(url, {"name": "M", "due_date": FUTURE}, format="json").data["id"]

        r = session_client.post(f"{url}{mid}/issues/", {"issue_ids": [str(issue.id)]}, format="json")
        assert r.status_code == 201 and r.data == {"added": 1}

        listed = session_client.get(f"{url}{mid}/issues/").data
        assert [str(i["id"]) for i in listed] == [str(issue.id)] and listed[0]["state_group"] == "unstarted"
        assert session_client.get(f"{url}{mid}/").data["progress"]["total"] == 1

        assert session_client.delete(f"{url}{mid}/issues/{issue.id}/").status_code == 204
        assert session_client.delete(f"{url}{mid}/issues/{issue.id}/").status_code == 404
        assert session_client.get(f"{url}{mid}/").data["progress"]["total"] == 0

    @pytest.mark.parametrize("payload", [{}, {"issue_ids": []}, {"issue_ids": "x"}, {"issue_ids": ["not-a-uuid"]}])
    def test_bad_issue_payloads(self, session_client, workspace, project, payload):
        m = Milestone.objects.create(name="M", due_date=date.today(), project=project)
        r = session_client.post(f"{base(workspace, project)}/milestones/{m.id}/issues/", payload, format="json")
        assert r.status_code == 400

    def test_dependencies_and_timeline(self, session_client, workspace, project):
        url = f"{base(workspace, project)}/milestones/"
        a = session_client.post(url, {"name": "A", "due_date": FUTURE}, format="json").data["id"]
        b = session_client.post(url, {"name": "B", "due_date": FUTURE}, format="json").data["id"]

        r = session_client.post(f"{url}{a}/dependencies/", {"depends_on": b}, format="json")
        assert r.status_code == 201
        dep_id = r.data["id"]
        assert (
            session_client.post(f"{url}{b}/dependencies/", {"depends_on": a}, format="json").status_code == 400
        )  # cycle
        assert (
            session_client.post(f"{url}{a}/dependencies/", {"depends_on": a}, format="json").status_code == 400
        )  # self

        timeline = session_client.get(f"{base(workspace, project)}/timeline/").data
        assert len(timeline["milestones"]) == 2
        assert [(str(e["milestone"]), str(e["depends_on"])) for e in timeline["dependencies"]] == [(a, b)]
        assert next(m for m in timeline["milestones"] if m["id"] == a)["dependency_ids"] == [uuid.UUID(b)]

        assert session_client.delete(f"{url}{a}/dependencies/{dep_id}/").status_code == 204
        assert session_client.get(f"{base(workspace, project)}/timeline/").data["dependencies"] == []

    def test_query_count_does_not_grow_with_milestones(
        self, session_client, workspace, project, django_assert_max_num_queries
    ):
        for i in range(15):
            Milestone.objects.create(name=f"M{i}", due_date=date.today(), project=project)
        with django_assert_max_num_queries(12):
            assert session_client.get(f"{base(workspace, project)}/timeline/").status_code == 200
