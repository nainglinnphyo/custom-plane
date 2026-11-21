# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest

from plane.custom.company.models import Company, CompanyWorkspace, Department, DepartmentMember
from plane.custom.company.services import (
    MAX_DEPARTMENT_DEPTH,
    OrgError,
    add_department_member,
    create_company,
    delete_department,
    ensure_workspace_member,
    get_company_for_workspace,
    link_workspace,
    unlink_workspace,
    validate_parent,
)
from plane.db.models import User, Workspace, WorkspaceMember

pytestmark = pytest.mark.unit


def make_user(prefix="u"):
    uid = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{uid}@plane.so", username=f"{prefix}_{uid}")


def make_workspace(owner, slug=None, role=20):
    ws = Workspace.objects.create(name="W", owner=owner, slug=slug or f"ws-{uuid4().hex[:8]}")
    WorkspaceMember.objects.create(workspace=ws, member=owner, role=role)
    return ws


@pytest.fixture
def dept(db, workspace):
    def _make(name="D", parent=None, ws=None):
        return Department.objects.create(name=name, parent=parent, workspace=ws or workspace)

    return _make


@pytest.mark.django_db
class TestCompany:
    def test_create_attaches_primary_workspace_and_unique_slug(self, workspace, create_user):
        company = create_company(workspace, "Acme Corp")
        assert company.slug == "acme-corp"
        link = CompanyWorkspace.objects.get(company=company)
        assert link.workspace_id == workspace.id and link.is_primary
        second_ws = make_workspace(create_user)
        assert create_company(second_ws, "Acme Corp").slug == "acme-corp-2"

    def test_workspace_cannot_join_two_companies(self, workspace):
        create_company(workspace, "A")
        with pytest.raises(OrgError):
            create_company(workspace, "B")

    def test_link_requires_admin_of_target(self, workspace, create_user):
        company = create_company(workspace, "A")
        other_owner = make_user()
        foreign = make_workspace(other_owner)
        with pytest.raises(OrgError):
            link_workspace(company, foreign, create_user)  # create_user is not a member of foreign
        WorkspaceMember.objects.create(workspace=foreign, member=create_user, role=15)
        with pytest.raises(OrgError):
            link_workspace(company, foreign, create_user)  # member, not admin
        WorkspaceMember.objects.filter(workspace=foreign, member=create_user).update(role=20)
        link = link_workspace(company, foreign, create_user)
        assert link.is_primary is False

    def test_link_rejects_workspace_already_in_a_company(self, workspace, create_user):
        company = create_company(workspace, "A")
        other = make_workspace(create_user)
        create_company(other, "B")
        with pytest.raises(OrgError):
            link_workspace(company, other, create_user)

    def test_unlink_promotes_new_primary_and_deletes_empty_company(self, workspace, create_user):
        company = create_company(workspace, "A")
        second = make_workspace(create_user)
        link_workspace(company, second, create_user)
        unlink_workspace(workspace)  # was primary
        assert CompanyWorkspace.objects.get(workspace=second).is_primary is True
        assert get_company_for_workspace(workspace) is None
        unlink_workspace(second)
        assert not Company.objects.filter(pk=company.pk).exists()

    def test_unlink_without_company_raises(self, workspace):
        with pytest.raises(OrgError):
            unlink_workspace(workspace)


@pytest.mark.django_db
class TestDepartmentTree:
    def test_parent_must_be_in_same_workspace(self, workspace, create_user, dept):
        foreign_ws = make_workspace(make_user())
        foreign = dept("F", ws=foreign_ws)
        with pytest.raises(OrgError):
            validate_parent(workspace, foreign)

    def test_cycles_are_rejected(self, workspace, dept):
        a = dept("A")
        b = dept("B", parent=a)
        c = dept("C", parent=b)
        for child, bad_parent in [(a, a), (a, b), (a, c), (b, c)]:
            with pytest.raises(OrgError):
                validate_parent(workspace, bad_parent, child)
        validate_parent(workspace, a, c)  # moving c up under a is fine

    def test_depth_limit(self, workspace, dept):
        node = dept("L1")
        for i in range(2, MAX_DEPARTMENT_DEPTH + 1):
            node = dept(f"L{i}", parent=node)
        with pytest.raises(OrgError):
            validate_parent(workspace, node)  # a new child would be level MAX+1

    def test_moving_a_subtree_counts_its_height(self, workspace, dept):
        chain = dept("R1")
        for i in range(2, MAX_DEPARTMENT_DEPTH):
            chain = dept(f"R{i}", parent=chain)  # MAX-1 levels deep
        sub = dept("S1")
        dept("S2", parent=sub)
        dept("S3", parent=Department.objects.get(name="S2"))  # subtree height 3
        with pytest.raises(OrgError):
            validate_parent(workspace, chain, sub)

    def test_delete_refused_with_children_and_removes_memberships(self, workspace, create_user, dept):
        parent = dept("P")
        child = dept("C", parent=parent)
        with pytest.raises(OrgError):
            delete_department(parent)
        add_department_member(child, create_user.id)
        delete_department(child)
        assert not DepartmentMember.objects.filter(department=child).exists()
        delete_department(parent)
        assert not Department.objects.filter(pk=parent.pk).exists()


@pytest.mark.django_db
class TestDepartmentMembers:
    def test_only_active_workspace_members(self, workspace, dept):
        d = dept()
        stranger = make_user()
        with pytest.raises(OrgError):
            add_department_member(d, stranger.id)
        inactive = make_user()
        WorkspaceMember.objects.create(workspace=workspace, member=inactive, role=15, is_active=False)
        with pytest.raises(OrgError):
            add_department_member(d, inactive.id)

    def test_member_of_another_workspace_rejected(self, workspace, dept):
        foreign_owner = make_user()
        make_workspace(foreign_owner)
        with pytest.raises(OrgError):
            add_department_member(dept(), foreign_owner.id)

    def test_duplicates_and_bad_roles_rejected(self, workspace, create_user, dept):
        d = dept()
        add_department_member(d, create_user.id, "lead")
        with pytest.raises(OrgError):
            add_department_member(d, create_user.id)
        other = make_user()
        WorkspaceMember.objects.create(workspace=workspace, member=other, role=15)
        with pytest.raises(OrgError):
            add_department_member(d, other.id, "boss")

    def test_ensure_workspace_member_returns_user(self, workspace, create_user):
        assert ensure_workspace_member(workspace, create_user.id).id == create_user.id
