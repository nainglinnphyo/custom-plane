# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest

from plane.custom.company.models import Department, DepartmentMember
from plane.custom.company.services import (
    MAX_DEPARTMENT_DEPTH,
    OrgError,
    add_department_member,
    delete_department,
    ensure_workspace_member,
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
