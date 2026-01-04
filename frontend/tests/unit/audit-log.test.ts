import { describe, expect, it } from "vitest";

import { buildAuditLogQuery } from "../../services/api/admin/audit-log";

describe("buildAuditLogQuery", () => {
  it("serializes provided filters", () => {
    const query = buildAuditLogQuery({
      entityType: "skill",
      adminId: "alice",
      startDate: "2025-01-01T00:00:00Z",
      endDate: "2025-01-02T00:00:00Z",
    });
    expect(query).toBe(
      "entityType=skill&adminId=alice&startDate=2025-01-01T00%3A00%3A00Z&endDate=2025-01-02T00%3A00%3A00Z"
    );
  });

  it("omits empty filters", () => {
    const query = buildAuditLogQuery({ entityType: "", adminId: undefined });
    expect(query).toBe("");
  });
});
