# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Django apps owned by Custom Plane.

``plane/settings/common.py`` splats this list into ``INSTALLED_APPS`` so that adding
a custom module never requires another edit to a core file: add its dotted path here.
"""

CUSTOM_INSTALLED_APPS = [
    "plane.custom.core",
    "plane.custom.milestones",
    "plane.custom.company",
    "plane.custom.teams",
]
