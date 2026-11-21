# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.db import models

from plane.db.models.project import ProjectBaseModel


class MilestoneStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    IN_PROGRESS = "in_progress", "In Progress"
    ACHIEVED = "achieved", "Achieved"
    MISSED = "missed", "Missed"


class DependencyType(models.TextChoices):
    FINISH_TO_START = "finish_to_start", "Finish to Start"


class Milestone(ProjectBaseModel):
    name = models.CharField(max_length=255, verbose_name="Milestone Name")
    description = models.TextField(blank=True, verbose_name="Milestone Description")
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    # Cached value, refreshed on writes and by the nightly task. API responses always
    # report the freshly derived status unless ``status_override`` is set.
    status = models.CharField(max_length=20, choices=MilestoneStatus.choices, default=MilestoneStatus.PLANNED)
    # When True the status was set manually by a project admin and is never derived.
    status_override = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custom_owned_milestones",
    )
    sort_order = models.FloatField(default=65535)

    class Meta:
        db_table = "custom_milestones"
        verbose_name = "Milestone"
        verbose_name_plural = "Milestones"
        ordering = ("due_date", "sort_order", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["project", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="custom_milestone_unique_name_project_when_deleted_at_null",
            ),
            models.CheckConstraint(
                condition=models.Q(start_date__isnull=True) | models.Q(due_date__gte=models.F("start_date")),
                name="custom_milestone_due_date_gte_start_date",
            ),
        ]

    def __str__(self):
        return f"{self.name} <{self.project_id}>"


class MilestoneIssue(ProjectBaseModel):
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name="milestone_issues")
    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="custom_milestone_links")

    class Meta:
        db_table = "custom_milestone_issues"
        verbose_name = "Milestone Issue"
        verbose_name_plural = "Milestone Issues"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["milestone", "issue"],
                condition=models.Q(deleted_at__isnull=True),
                name="custom_milestone_issue_unique_when_deleted_at_null",
            ),
        ]

    def __str__(self):
        return f"{self.milestone_id} <-> {self.issue_id}"


class MilestoneDependency(ProjectBaseModel):
    """``milestone`` cannot start until ``depends_on`` is finished (finish-to-start)."""

    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name="dependencies")
    depends_on = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name="dependents")
    dependency_type = models.CharField(
        max_length=20, choices=DependencyType.choices, default=DependencyType.FINISH_TO_START
    )

    class Meta:
        db_table = "custom_milestone_dependencies"
        verbose_name = "Milestone Dependency"
        verbose_name_plural = "Milestone Dependencies"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["milestone", "depends_on"],
                condition=models.Q(deleted_at__isnull=True),
                name="custom_milestone_dependency_unique_when_deleted_at_null",
            ),
            models.CheckConstraint(
                condition=~models.Q(milestone=models.F("depends_on")),
                name="custom_milestone_dependency_not_self",
            ),
        ]

    def __str__(self):
        return f"{self.milestone_id} depends on {self.depends_on_id}"
