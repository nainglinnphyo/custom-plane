# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from plane.db.models import ProjectMember
from plane.db.models.project import ROLE

from .models import Milestone, MilestoneDependency, MilestoneStatus
from .services import effective_status, is_at_risk


class MilestoneSerializer(serializers.ModelSerializer):
    """Read serializer. Expects a queryset annotated by services.annotate_progress."""

    status = serializers.SerializerMethodField()
    is_at_risk = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    dependency_ids = serializers.SerializerMethodField()

    class Meta:
        model = Milestone
        fields = [
            "id",
            "project",
            "name",
            "description",
            "start_date",
            "due_date",
            "status",
            "status_override",
            "is_at_risk",
            "owner",
            "sort_order",
            "progress",
            "dependency_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_status(self, obj):
        return effective_status(obj)

    def get_is_at_risk(self, obj):
        return is_at_risk(obj, effective_status(obj))

    def get_progress(self, obj):
        total = obj.total_issues
        done = obj.completed_issues
        return {
            "total": total,
            "completed": done,
            "cancelled": obj.cancelled_issues,
            "started": obj.started_issues,
            "percent": round(100 * done / total) if total else 0,
        }

    def get_dependency_ids(self, obj):
        return [d.depends_on_id for d in obj.dependencies.all()]


class MilestoneWriteSerializer(serializers.ModelSerializer):
    # Passing a status sets a manual override; passing null clears it. Project admins only.
    status = serializers.ChoiceField(choices=MilestoneStatus.choices, required=False, allow_null=True)

    class Meta:
        model = Milestone
        fields = ["name", "description", "start_date", "due_date", "status", "owner", "sort_order"]
        extra_kwargs = {"name": {"max_length": 255}}

    def validate_name(self, value):
        return value.strip()

    def validate_owner(self, owner):
        project_id = self.context["project_id"]
        if owner and not ProjectMember.objects.filter(project_id=project_id, member=owner, is_active=True).exists():
            raise serializers.ValidationError("Owner must be an active member of the project.")
        return owner

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        due = attrs.get("due_date", getattr(self.instance, "due_date", None))
        if start and due and due < start:
            raise serializers.ValidationError({"due_date": "Due date cannot be before the start date."})

        name = attrs.get("name")
        if name is not None:
            clash = Milestone.objects.filter(project_id=self.context["project_id"], name__iexact=name)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError({"name": "A milestone with this name already exists in the project."})

        if "status" in attrs and self.context.get("role") != ROLE.ADMIN.value:
            raise serializers.ValidationError({"status": "Only project admins can set the status manually."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("status", None)  # overrides only make sense on existing milestones
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "status" in validated_data:
            manual = validated_data.pop("status")
            instance.status_override = manual is not None
            if manual is not None:
                instance.status = manual
        return super().update(instance, validated_data)


class MilestoneDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = MilestoneDependency
        fields = ["id", "milestone", "depends_on", "dependency_type"]
        read_only_fields = fields
