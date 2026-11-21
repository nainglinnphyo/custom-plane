# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.custom.company.models import Department
from plane.db.models import User, Workspace, WorkspaceMember

pytestmark = pytest.mark.contract


def make_user(prefix="u"):
    uid = uuid4().hex[:8]
    return User.objects.create(
        email=f"{prefix}-{uid}@plane.so", username=f"{prefix}_{uid}", display_name=f"{prefix}{uid}"
    )


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def role_client(workspace, role):
    user = make_user(f"r{role}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return client_for(user), user


def make_workspace(owner=None, role=20):
    owner = owner or make_user("owner")
    ws = Workspace.objects.create(name="Other", owner=owner, slug=f"ws-{uuid4().hex[:8]}")
    WorkspaceMember.objects.create(workspace=ws, member=owner, role=role)
    return ws, owner


def url(workspace, path):
    return f"/api/custom/workspaces/{workspace.slug}/{path}"


@pytest.mark.django_db
class TestPermissionMatrix:
    @pytest.mark.parametrize("path", ["company/", "departments/", "teams/"])
    def test_anonymous_and_non_members_rejected(self, workspace, path):
        assert APIClient().get(url(workspace, path)).status_code in (401, 403)
        assert client_for(make_user("out")).get(url(workspace, path)).status_code == 403

    @pytest.mark.parametrize("path", ["departments/", "teams/"])
    def test_guest_cannot_read_directory(self, workspace, path):
        guest, _ = role_client(workspace, 5)
        assert guest.get(url(workspace, path)).status_code == 403

    @pytest.mark.parametrize("path", ["departments/", "teams/"])
    def test_member_reads_but_cannot_write(self, workspace, path):
        member, _ = role_client(workspace, 15)
        assert member.get(url(workspace, path)).status_code == 200
        assert member.post(url(workspace, path), {"name": "X"}, format="json").status_code == 403

    def test_member_cannot_touch_company(self, workspace):
        member, _ = role_client(workspace, 15)
        assert member.post(url(workspace, "company/"), {"name": "X"}, format="json").status_code == 403

    def test_inactive_member_rejected(self, workspace):
        client, user = role_client(workspace, 20)
        WorkspaceMember.objects.filter(workspace=workspace, member=user).update(is_active=False)
        assert client.get(url(workspace, "departments/")).status_code == 403


@pytest.mark.django_db
class TestCompanyApi:
    def test_lifecycle(self, session_client, workspace):
        assert session_client.get(url(workspace, "company/")).data is None
        r = session_client.post(url(workspace, "company/"), {"name": "Acme"}, format="json")
        assert r.status_code == 201 and r.data["slug"] == "acme"
        assert [w["slug"] for w in r.data["workspaces"]] == [workspace.slug]
        assert session_client.post(url(workspace, "company/"), {"name": "Again"}, format="json").status_code == 400
        assert (
            session_client.patch(url(workspace, "company/"), {"name": "Acme Inc"}, format="json").data["name"]
            == "Acme Inc"
        )
        assert session_client.delete(url(workspace, "company/")).status_code == 204
        assert session_client.get(url(workspace, "company/")).data is None
        assert session_client.delete(url(workspace, "company/")).status_code == 404

    def test_name_required(self, session_client, workspace):
        assert session_client.post(url(workspace, "company/"), {"name": "  "}, format="json").status_code == 400
        assert session_client.post(url(workspace, "company/"), {}, format="json").status_code == 400

    def test_link_workspace_requires_admin_of_both(self, session_client, workspace, create_user):
        session_client.post(url(workspace, "company/"), {"name": "Acme"}, format="json")
        foreign, _ = make_workspace()
        body = {"workspace_slug": foreign.slug}
        assert session_client.post(url(workspace, "company/workspaces/"), body, format="json").status_code == 400
        # a missing workspace gets the same answer as a forbidden one
        r_missing = session_client.post(
            url(workspace, "company/workspaces/"), {"workspace_slug": "nope"}, format="json"
        )
        assert r_missing.status_code == 400
        WorkspaceMember.objects.create(workspace=foreign, member=create_user, role=20)
        r = session_client.post(url(workspace, "company/workspaces/"), body, format="json")
        assert r.status_code == 201
        assert {w["slug"] for w in r.data["workspaces"]} == {workspace.slug, foreign.slug}

    def test_company_does_not_leak_workspaces_the_viewer_is_not_in(self, session_client, workspace, create_user):
        session_client.post(url(workspace, "company/"), {"name": "Acme"}, format="json")
        foreign, foreign_admin = make_workspace()
        WorkspaceMember.objects.create(workspace=foreign, member=create_user, role=20)
        session_client.post(url(workspace, "company/workspaces/"), {"workspace_slug": foreign.slug}, format="json")
        # a plain member of `workspace` only sees `workspace` in the company
        member, _ = role_client(workspace, 15)
        slugs = [w["slug"] for w in member.get(url(workspace, "company/")).data["workspaces"]]
        assert slugs == [workspace.slug]


@pytest.mark.django_db
class TestDepartmentApi:
    def test_crud_and_counts(self, session_client, workspace):
        base = url(workspace, "departments/")
        eng = session_client.post(base, {"name": "Engineering", "description": "Builds"}, format="json")
        assert eng.status_code == 201 and eng.data["member_count"] == 0
        sub = session_client.post(base, {"name": "Platform", "parent": str(eng.data["id"])}, format="json").data
        assert str(sub["parent"]) == str(eng.data["id"])

        listed = session_client.get(base).data
        assert {d["name"]: d["child_count"] for d in listed} == {"Engineering": 1, "Platform": 0}

        r = session_client.patch(f"{base}{sub['id']}/", {"description": "Infra"}, format="json")
        assert r.status_code == 200 and r.data["description"] == "Infra"
        assert session_client.get(f"{base}{sub['id']}/").data["name"] == "Platform"

        assert session_client.delete(f"{base}{eng.data['id']}/").status_code == 400  # has a child
        assert session_client.delete(f"{base}{sub['id']}/").status_code == 204
        assert session_client.delete(f"{base}{eng.data['id']}/").status_code == 204
        assert session_client.get(base).data == []

    def test_name_uniqueness_per_level_case_insensitive(self, session_client, workspace):
        base = url(workspace, "departments/")
        a = session_client.post(base, {"name": "Ops"}, format="json").data
        assert session_client.post(base, {"name": "ops"}, format="json").status_code == 400
        # same name under a different parent is fine
        assert session_client.post(base, {"name": "Ops", "parent": str(a["id"])}, format="json").status_code == 201
        assert session_client.post(base, {"name": "Ops", "parent": str(a["id"])}, format="json").status_code == 400

    def test_move_rejects_cycles(self, session_client, workspace):
        base = url(workspace, "departments/")
        a = session_client.post(base, {"name": "A"}, format="json").data
        b = session_client.post(base, {"name": "B", "parent": str(a["id"])}, format="json").data
        assert session_client.patch(f"{base}{a['id']}/", {"parent": str(b["id"])}, format="json").status_code == 400
        assert session_client.patch(f"{base}{a['id']}/", {"parent": str(a["id"])}, format="json").status_code == 400
        assert session_client.patch(f"{base}{b['id']}/", {"parent": None}, format="json").status_code == 200

    def test_blank_name_rejected(self, session_client, workspace):
        assert session_client.post(url(workspace, "departments/"), {"name": " "}, format="json").status_code == 400


@pytest.mark.django_db
class TestDepartmentMembersApi:
    def test_add_list_role_remove(self, session_client, workspace, create_user):
        dept = session_client.post(url(workspace, "departments/"), {"name": "Eng"}, format="json").data
        base = url(workspace, f"departments/{dept['id']}/members/")
        member, member_user = role_client(workspace, 15)

        r = session_client.post(base, {"member": str(member_user.id), "role": "lead"}, format="json")
        assert r.status_code == 201 and r.data["role"] == "lead" and r.data["display_name"] == member_user.display_name
        assert session_client.post(base, {"member": str(member_user.id)}, format="json").status_code == 400  # duplicate

        assert [str(m["member"]) for m in session_client.get(base).data] == [str(member_user.id)]
        assert session_client.get(url(workspace, "departments/")).data[0]["member_count"] == 1

        r = session_client.patch(f"{base}{member_user.id}/", {"role": "member"}, format="json")
        assert r.status_code == 200 and r.data["role"] == "member"
        assert session_client.patch(f"{base}{member_user.id}/", {"role": "boss"}, format="json").status_code == 400

        assert session_client.delete(f"{base}{member_user.id}/").status_code == 204
        assert session_client.delete(f"{base}{member_user.id}/").status_code == 404
        assert session_client.get(base).data == []

    def test_member_role_can_read_roster(self, session_client, workspace):
        dept = session_client.post(url(workspace, "departments/"), {"name": "Eng"}, format="json").data
        member, _ = role_client(workspace, 15)
        assert member.get(url(workspace, f"departments/{dept['id']}/members/")).status_code == 200

    @pytest.mark.parametrize("bad", [{}, {"member": "not-a-uuid"}, {"member": str(uuid4())}])
    def test_bad_member_payloads(self, session_client, workspace, bad):
        dept = session_client.post(url(workspace, "departments/"), {"name": "Eng"}, format="json").data
        r = session_client.post(url(workspace, f"departments/{dept['id']}/members/"), bad, format="json")
        assert r.status_code == 400


@pytest.fixture
def foreign(db):
    ws, owner = make_workspace()
    dept = Department.objects.create(name="Secret", workspace=ws)
    return {"ws": ws, "owner": owner, "dept": dept}


@pytest.mark.django_db
class TestTenantIsolation:
    def test_cannot_use_foreign_department_via_own_slug(self, session_client, workspace, foreign):
        base = url(workspace, f"departments/{foreign['dept'].id}/")
        assert session_client.get(base).status_code == 404
        assert session_client.patch(base, {"name": "pwned"}, format="json").status_code == 404
        assert session_client.delete(base).status_code == 404
        assert session_client.get(base + "members/").status_code == 404
        foreign["dept"].refresh_from_db()
        assert foreign["dept"].name == "Secret" and foreign["dept"].deleted_at is None

    def test_cannot_read_foreign_workspace_directory(self, session_client, foreign):
        assert session_client.get(url(foreign["ws"], "departments/")).status_code == 403

    def test_foreign_parent_looks_like_a_missing_one(self, session_client, workspace, foreign):
        r = session_client.post(
            url(workspace, "departments/"), {"name": "X", "parent": str(foreign["dept"].id)}, format="json"
        )
        assert r.status_code == 400
        assert not Department.objects.filter(workspace=workspace, name="X").exists()

    def test_cannot_add_user_from_another_workspace(self, session_client, workspace, foreign):
        dept = session_client.post(url(workspace, "departments/"), {"name": "Eng"}, format="json").data
        r = session_client.post(
            url(workspace, f"departments/{dept['id']}/members/"), {"member": str(foreign["owner"].id)}, format="json"
        )
        assert r.status_code == 400

    def test_lists_only_own_workspace(self, session_client, workspace, foreign):
        Department.objects.create(name="Mine", workspace=workspace)
        assert [d["name"] for d in session_client.get(url(workspace, "departments/")).data] == ["Mine"]

    def test_query_count_is_flat(self, session_client, workspace, django_assert_max_num_queries):
        for i in range(12):
            Department.objects.create(name=f"D{i}", workspace=workspace)
        with django_assert_max_num_queries(8):
            assert session_client.get(url(workspace, "departments/")).status_code == 200


@pytest.mark.django_db
def test_company_endpoints_do_not_break_core(session_client):
    assert session_client.get("/api/instances/").status_code == status.HTTP_200_OK
