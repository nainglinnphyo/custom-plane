# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.db import models

from plane.db.models.base import BaseModel


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
