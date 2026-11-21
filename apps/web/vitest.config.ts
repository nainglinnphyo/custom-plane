/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { defineConfig } from "vitest/config";

// Deliberately separate from vite.config.ts: that one loads the React Router plugin, which is
// not needed (and not wanted) for unit tests of plain TypeScript modules.
export default defineConfig({
  test: {
    environment: "node",
    include: ["**/*.test.{ts,tsx}"],
    exclude: ["**/node_modules/**", "build/**", ".react-router/**"],
  },
});
