# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.db import models

from plane.db.models.base import BaseModel


class Company(BaseModel):
    """A grouping of workspaces for reporting roll-ups only (D2). It is NOT a tenant boundary."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "custom_companies"
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(deleted_at__isnull=True),
                name="custom_company_unique_slug_when_deleted_at_null",
            ),
        ]

    def __str__(self):
        return self.name


class CompanyWorkspace(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="workspace_links")
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="custom_company_links")
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "custom_company_workspaces"
        verbose_name = "Company Workspace"
        verbose_name_plural = "Company Workspaces"
        ordering = ("-is_primary", "created_at")
        constraints = [
            # a workspace belongs to at most one company
            models.UniqueConstraint(
                fields=["workspace"],
                condition=models.Q(deleted_at__isnull=True),
                name="custom_company_workspace_unique_workspace_when_deleted_at_null",
            ),
            # at most one primary workspace per company
            models.UniqueConstraint(
                fields=["company"],
                condition=models.Q(is_primary=True, deleted_at__isnull=True),
                name="custom_company_workspace_one_primary_when_deleted_at_null",
            ),
        ]

    def __str__(self):
        return f"{self.company_id} <-> {self.workspace_id}"


class DepartmentRole(models.TextChoices):
    MEMBER = "member", "Member"
    LEAD = "lead", "Lead"


class Department(BaseModel):
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="custom_departments")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")

    class Meta:
        db_table = "custom_departments"
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ("name",)
        constraints = [
            # sibling names are unique; NULL parents need their own constraint (NULL != NULL in SQL)
            models.UniqueConstraint(
                fields=["workspace", "name"],
                condition=models.Q(parent__isnull=True, deleted_at__isnull=True),
                name="custom_department_unique_root_name_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "parent", "name"],
                condition=models.Q(parent__isnull=False, deleted_at__isnull=True),
                name="custom_department_unique_child_name_when_deleted_at_null",
            ),
            models.CheckConstraint(
                condition=~models.Q(parent=models.F("id")),
                name="custom_department_not_own_parent",
            ),
        ]

    def __str__(self):
        return self.name


class DepartmentMember(BaseModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="memberships")
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="custom_department_memberships"
    )
    role = models.CharField(max_length=10, choices=DepartmentRole.choices, default=DepartmentRole.MEMBER)

    class Meta:
        db_table = "custom_department_members"
        verbose_name = "Department Member"
        verbose_name_plural = "Department Members"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["department", "member"],
                condition=models.Q(deleted_at__isnull=True),
                name="custom_department_member_unique_when_deleted_at_null",
            ),
        ]

    def __str__(self):
        return f"{self.member_id} in {self.department_id}"
