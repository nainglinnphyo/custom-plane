/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
// components
import { OrganizationRoot } from "@/components/organization";
import { PageHead } from "@/components/core/page-title";
import type { Route } from "./+types/page";

function OrganizationPage({ params }: Route.ComponentProps) {
  const { t } = useTranslation();
  return (
    <>
      <PageHead title={t("organization.nav_label")} />
      <OrganizationRoot workspaceSlug={params.workspaceSlug} />
    </>
  );
}

export default observer(OrganizationPage);
