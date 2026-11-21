# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.db import models

from plane.db.models.base import BaseModel


class TeamRole(models.TextChoices):
    MEMBER = "member", "Member"
    LEAD = "lead", "Lead"


class CustomTeam(BaseModel):
    """A team of workspace members, optionally attached to a department.

    Deliberately separate from the upstream ``db.Team`` model (``teams`` table), which is defined but unused
    by upstream views, so that upstream changes to it cannot affect Custom Plane (see docs/03 open question 1).
    """

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="custom_teams")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        "custom_company.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="teams"
    )

    class Meta:
        db_table = "custom_teams"
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="custom_team_unique_name_workspace_when_deleted_at_null",
            ),
        ]

    def __str__(self):
        return self.name


class TeamMember(BaseModel):
    team = models.ForeignKey(CustomTeam, on_delete=models.CASCADE, related_name="memberships")
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="custom_team_memberships"
    )
    role = models.CharField(max_length=10, choices=TeamRole.choices, default=TeamRole.MEMBER)

    class Meta:
        db_table = "custom_team_members"
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["team", "member"],
                condition=models.Q(deleted_at__isnull=True),
                name="custom_team_member_unique_when_deleted_at_null",
            ),
        ]

    def __str__(self):
        return f"{self.member_id} in {self.team_id}"
