# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from plane.custom.company.models import Department

from .models import CustomTeam


class TeamSerializer(serializers.ModelSerializer):
    """Expects a queryset annotated by ``services.annotate_teams``."""

    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CustomTeam
        fields = ["id", "name", "description", "department", "member_count", "created_at", "updated_at"]
        read_only_fields = fields


class TeamWriteSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=False, allow_null=True)

    class Meta:
        model = CustomTeam
        fields = ["name", "description", "department"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # departments resolve inside the workspace only
        self.fields["department"].queryset = Department.objects.filter(workspace=self.context["workspace"])

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate(self, attrs):
        name = attrs.get("name")
        if name is not None:
            clash = CustomTeam.objects.filter(workspace=self.context["workspace"], name__iexact=name)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError({"name": "A team with this name already exists."})
        return attrs
