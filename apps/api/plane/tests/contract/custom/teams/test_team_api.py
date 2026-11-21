# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.custom.company.models import Department
from plane.custom.teams.models import CustomTeam
from plane.db.models import User, Workspace, WorkspaceMember

pytestmark = pytest.mark.contract


def make_user(prefix="u"):
    uid = uuid4().hex[:8]
    return User.objects.create(
        email=f"{prefix}-{uid}@plane.so", username=f"{prefix}_{uid}", display_name=f"{prefix}{uid}"
    )


def role_client(workspace, role):
    user = make_user(f"r{role}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def url(workspace, path):
    return f"/api/custom/workspaces/{workspace.slug}/{path}"


@pytest.fixture
def foreign(db):
    owner = make_user("owner")
    ws = Workspace.objects.create(name="Other", owner=owner, slug=f"ws-{uuid4().hex[:8]}")
    WorkspaceMember.objects.create(workspace=ws, member=owner, role=20)
    return {
        "ws": ws,
        "owner": owner,
        "dept": Department.objects.create(name="Secret", workspace=ws),
        "team": CustomTeam.objects.create(name="Secret team", workspace=ws),
    }


@pytest.mark.django_db
class TestTeamApi:
    def test_crud_with_department(self, session_client, workspace):
        dept = Department.objects.create(name="Eng", workspace=workspace)
        base = url(workspace, "teams/")
        r = session_client.post(
            base, {"name": "Platform", "description": "Infra", "department": str(dept.id)}, format="json"
        )
        assert r.status_code == 201 and str(r.data["department"]) == str(dept.id) and r.data["member_count"] == 0
        team_id = r.data["id"]

        assert [t["name"] for t in session_client.get(base).data] == ["Platform"]
        r = session_client.patch(f"{base}{team_id}/", {"department": None}, format="json")
        assert r.status_code == 200 and r.data["department"] is None
        assert session_client.delete(f"{base}{team_id}/").status_code == 204
        assert session_client.get(f"{base}{team_id}/").status_code == 404

    def test_name_unique_case_insensitive_and_required(self, session_client, workspace):
        base = url(workspace, "teams/")
        assert session_client.post(base, {"name": "Core"}, format="json").status_code == 201
        assert session_client.post(base, {"name": "core"}, format="json").status_code == 400
        assert session_client.post(base, {"name": " "}, format="json").status_code == 400

    def test_deleting_a_department_keeps_its_teams(self, session_client, workspace):
        dept = Department.objects.create(name="Eng", workspace=workspace)
        team = session_client.post(
            url(workspace, "teams/"), {"name": "T", "department": str(dept.id)}, format="json"
        ).data
        session_client.delete(url(workspace, f"departments/{dept.id}/"))
        assert str(session_client.get(url(workspace, f"teams/{team['id']}/")).data["id"]) == str(team["id"])

    def test_members(self, session_client, workspace):
        team = session_client.post(url(workspace, "teams/"), {"name": "T"}, format="json").data
        base = url(workspace, f"teams/{team['id']}/members/")
        _, user = role_client(workspace, 15)
        r = session_client.post(base, {"member": str(user.id), "role": "lead"}, format="json")
        assert r.status_code == 201 and r.data["role"] == "lead"
        assert session_client.post(base, {"member": str(user.id)}, format="json").status_code == 400
        assert session_client.get(url(workspace, "teams/")).data[0]["member_count"] == 1
        assert session_client.patch(f"{base}{user.id}/", {"role": "member"}, format="json").data["role"] == "member"
        assert session_client.delete(f"{base}{user.id}/").status_code == 204
        assert session_client.get(base).data == []


@pytest.mark.django_db
class TestTeamPermissionsAndIsolation:
    def test_member_reads_only(self, session_client, workspace):
        team = session_client.post(url(workspace, "teams/"), {"name": "T"}, format="json").data
        member, user = role_client(workspace, 15)
        assert member.get(url(workspace, f"teams/{team['id']}/")).status_code == 200
        assert member.patch(url(workspace, f"teams/{team['id']}/"), {"name": "x"}, format="json").status_code == 403
        assert (
            member.post(
                url(workspace, f"teams/{team['id']}/members/"), {"member": str(user.id)}, format="json"
            ).status_code
            == 403
        )
        assert member.delete(url(workspace, f"teams/{team['id']}/")).status_code == 403

    def test_foreign_team_unreachable_through_own_slug(self, session_client, workspace, foreign):
        base = url(workspace, f"teams/{foreign['team'].id}/")
        assert session_client.get(base).status_code == 404
        assert session_client.patch(base, {"name": "pwned"}, format="json").status_code == 404
        assert session_client.delete(base).status_code == 404
        foreign["team"].refresh_from_db()
        assert foreign["team"].name == "Secret team" and foreign["team"].deleted_at is None

    def test_foreign_department_rejected(self, session_client, workspace, foreign):
        r = session_client.post(
            url(workspace, "teams/"), {"name": "T", "department": str(foreign["dept"].id)}, format="json"
        )
        assert r.status_code == 400
        assert not CustomTeam.objects.filter(workspace=workspace, name="T").exists()

    def test_cannot_add_foreign_user(self, session_client, workspace, foreign):
        team = session_client.post(url(workspace, "teams/"), {"name": "T"}, format="json").data
        r = session_client.post(
            url(workspace, f"teams/{team['id']}/members/"), {"member": str(foreign["owner"].id)}, format="json"
        )
        assert r.status_code == 400

    def test_cannot_read_foreign_directory(self, session_client, foreign):
        assert session_client.get(url(foreign["ws"], "teams/")).status_code == 403
