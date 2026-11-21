/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Button } from "@makeplane/propel/components/button";
import { InputField } from "@makeplane/propel/components/input-field";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { CompanyService } from "@/services/company.service";
import { getApiErrorMessage } from "./helpers";
import type { TCompany } from "./types";

const companyService = new CompanyService();

type Props = {
  workspaceSlug: string;
  company: TCompany | null;
  canEdit: boolean;
  onCreated: () => void;
};

export function CompanySection(props: Props) {
  const { workspaceSlug, company, canEdit, onCreated } = props;
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    setIsCreating(true);
    try {
      await companyService.createCompany(workspaceSlug, name.trim());
      setToast({ type: "success", title: t("success"), message: t("company.toast_saved") });
      setName("");
      onCreated();
    } catch (error) {
      setToast({ type: "error", title: t("error"), message: getApiErrorMessage(error, t("something_went_wrong")) });
    } finally {
      setIsCreating(false);
    }
  };

  if (!company) {
    return (
      <section className="rounded-lg border border-subtle bg-layer-1 p-4" data-testid="company-empty">
        <h2 className="text-14 font-medium text-primary">{t("company.no_company_title")}</h2>
        <p className="mt-1 text-13 text-secondary">{t("company.no_company_description")}</p>
        {canEdit && (
          <form className="mt-3 flex flex-wrap items-center gap-2" onSubmit={handleCreate}>
            <div className="min-w-56 flex-1">
              <InputField
                size="lg"
                orientation="vertical"
                name="company-name"
                type="text"
                placeholder={t("company.company_name_placeholder")}
                aria-label={t("company.company_name_placeholder")}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <Button
              variant="primary"
              size="md"
              stretch="auto"
              type="submit"
              disabled={!name.trim()}
              loading={isCreating}
              label={t("company.create_company")}
            />
          </form>
        )}
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-subtle bg-layer-1 p-4" data-testid="company-card">
      <h2 className="text-16 font-semibold text-primary">{company.name}</h2>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className="text-12 text-secondary">{t("workspaces")}:</span>
        {company.workspaces.map((workspace) => (
          <span key={workspace.id} className="rounded bg-layer-3 px-2 py-0.5 text-12 text-primary">
            {workspace.name}
            {workspace.is_primary && <span className="ml-1 text-secondary">· {t("company.primary")}</span>}
          </span>
        ))}
      </div>
    </section>
  );
}
