# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Business rules for companies and departments. Views call these; they never duplicate the rules."""

from django.db import transaction
from django.db.models import Count, Q

from plane.db.models import User, Workspace, WorkspaceMember

from .models import Department, DepartmentMember, DepartmentRole

MAX_DEPARTMENT_DEPTH = 8


class OrgError(Exception):
    """Raised for rule violations; ``message`` is safe to return to API clients."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


# ------------------------------------------------------------------ shared helpers


def ensure_workspace_member(workspace: Workspace, user_id) -> User:
    """Return the user if they are an active member of the workspace, else raise ``OrgError``.

    Used by every membership endpoint so that department/team rosters can never contain people from
    outside the workspace (or deactivated members).
    """
    membership = (
        WorkspaceMember.objects.filter(workspace=workspace, member_id=user_id, is_active=True)
        .select_related("member")
        .first()
    )
    if membership is None:
        raise OrgError("The user must be an active member of this workspace.")
    return membership.member


# ----------------------------------------------------------------------- departments


def annotate_departments(queryset):
    return queryset.annotate(
        member_count=Count("memberships", filter=Q(memberships__deleted_at__isnull=True), distinct=True),
        child_count=Count("children", filter=Q(children__deleted_at__isnull=True), distinct=True),
    )


def _ancestor_ids(department_id):
    """Ids from the given department up to its root (inclusive), cycle-safe."""
    chain, current, seen = [], department_id, set()
    while current is not None and current not in seen:
        seen.add(current)
        chain.append(current)
        current = Department.objects.filter(pk=current).values_list("parent_id", flat=True).first()
    return chain


def _subtree_height(department_id, seen=None) -> int:
    """Number of levels at and below the department (a leaf is 1)."""
    seen = seen or set()
    if department_id in seen:
        return 0
    seen.add(department_id)
    child_ids = Department.objects.filter(parent_id=department_id).values_list("pk", flat=True)
    return 1 + max((_subtree_height(c, seen) for c in child_ids), default=0)


def validate_parent(workspace: Workspace, parent, department=None) -> None:
    """Check a proposed parent: same workspace, no cycle, bounded depth."""
    if parent is None:
        return
    if parent.workspace_id != workspace.id:
        raise OrgError("The parent department must belong to the same workspace.")
    if department is not None:
        if parent.pk == department.pk or department.pk in _ancestor_ids(parent.pk):
            raise OrgError("A department cannot be moved under itself or one of its sub-departments.")
    depth_above = len(_ancestor_ids(parent.pk))
    height_below = _subtree_height(department.pk) if department is not None else 1
    if depth_above + height_below > MAX_DEPARTMENT_DEPTH:
        raise OrgError(f"Departments can be nested at most {MAX_DEPARTMENT_DEPTH} levels deep.")


def delete_department(department: Department) -> None:
    if Department.objects.filter(parent=department).exists():
        raise OrgError("Move or delete the sub-departments first.")
    with transaction.atomic():
        DepartmentMember.objects.filter(department=department).delete()
        department.delete()


@transaction.atomic
def add_department_member(department: Department, user_id, role: str = DepartmentRole.MEMBER.value) -> DepartmentMember:
    if role not in DepartmentRole.values:
        raise OrgError("Invalid role.")
    user = ensure_workspace_member(department.workspace, user_id)
    if DepartmentMember.objects.filter(department=department, member=user).exists():
        raise OrgError("This user is already in the department.")
    return DepartmentMember.objects.create(department=department, member=user, role=role)
