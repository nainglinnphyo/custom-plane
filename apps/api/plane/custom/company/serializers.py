# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers


from .models import Department, DepartmentMember, DepartmentRole


class DepartmentSerializer(serializers.ModelSerializer):
    """Expects a queryset annotated by ``services.annotate_departments``."""

    member_count = serializers.IntegerField(read_only=True)
    child_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "description", "parent", "member_count", "child_count", "created_at", "updated_at"]
        read_only_fields = fields


class DepartmentWriteSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Department
        fields = ["name", "description", "parent"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # resolve parents inside the workspace only, so a foreign id is indistinguishable from a missing one
        self.fields["parent"].queryset = Department.objects.filter(workspace=self.context["workspace"])

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate(self, attrs):
        workspace = self.context["workspace"]
        name = attrs.get("name", getattr(self.instance, "name", None))
        parent = attrs["parent"] if "parent" in attrs else getattr(self.instance, "parent", None)
        clash = Department.objects.filter(workspace=workspace, parent=parent, name__iexact=name)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({"name": "A department with this name already exists at this level."})
        return attrs


class MembershipSerializer(serializers.Serializer):
    """Works for both DepartmentMember and TeamMember rows."""

    id = serializers.UUIDField(read_only=True)
    member = serializers.UUIDField(source="member_id", read_only=True)
    display_name = serializers.CharField(source="member.display_name", read_only=True)
    first_name = serializers.CharField(source="member.first_name", read_only=True)
    last_name = serializers.CharField(source="member.last_name", read_only=True)
    role = serializers.CharField(read_only=True)


class MemberWriteSerializer(serializers.Serializer):
    member = serializers.UUIDField()
    role = serializers.ChoiceField(choices=DepartmentRole.choices, default=DepartmentRole.MEMBER.value)


class MemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=DepartmentRole.choices)


__all__ = [
    "DepartmentMember",
    "DepartmentSerializer",
    "DepartmentWriteSerializer",
    "MemberRoleSerializer",
    "MemberWriteSerializer",
    "MembershipSerializer",
]
