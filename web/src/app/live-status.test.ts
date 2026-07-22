import { describe, expect, it } from "vitest";
import { UnsupportedVersionError } from "@/shared/api/errors";
import type { DoctorPayload } from "@/shared/api/types";
import { deriveLiveStatus, HEALTH_POLL_INTERVAL_MS } from "./live-status";

const doctor = (statuses: string[]): DoctorPayload => ({
  schema_version: "1",
  checks: statuses.map((status, i) => ({
    name: `check-${i}`,
    status,
    message: "",
    hint: null,
  })),
});

describe("deriveLiveStatus", () => {
  it("polls at the spec interval", () => {
    expect(HEALTH_POLL_INTERVAL_MS).toBe(15_000);
  });

  it("is connecting before the first probe lands", () => {
    expect(
      deriveLiveStatus({ status: "pending", error: null, data: undefined, dataUpdatedAt: 0 }),
    ).toEqual({ state: "connecting" });
  });

  it("is connected with the doctor verdict on success", () => {
    const status = deriveLiveStatus({
      status: "success",
      error: null,
      data: doctor(["ok", "warn"]),
      dataUpdatedAt: 1_000,
    });
    expect(status).toEqual({
      state: "connected",
      doctorOk: true,
      failingChecks: 0,
      lastUpdatedAt: 1_000,
    });
  });

  it("counts failing checks", () => {
    const status = deriveLiveStatus({
      status: "success",
      error: null,
      data: doctor(["ok", "fail", "fail"]),
      dataUpdatedAt: 1_000,
    });
    expect(status).toMatchObject({ state: "connected", doctorOk: false, failingChecks: 2 });
  });

  it("is disconnected on transport failure, keeping the last-good timestamp", () => {
    const status = deriveLiveStatus({
      status: "error",
      error: new Error("fetch failed"),
      data: doctor(["ok"]),
      dataUpdatedAt: 2_000,
    });
    expect(status).toEqual({ state: "disconnected", lastUpdatedAt: 2_000 });
  });

  it("is disconnected with no timestamp when the server was never reached", () => {
    const status = deriveLiveStatus({
      status: "error",
      error: new Error("fetch failed"),
      data: undefined,
      dataUpdatedAt: 0,
    });
    expect(status).toEqual({ state: "disconnected", lastUpdatedAt: null });
  });

  it("is a blocking refusal on schema_version mismatch — even with stale data", () => {
    const status = deriveLiveStatus({
      status: "error",
      error: new UnsupportedVersionError("999", "1"),
      data: doctor(["ok"]),
      dataUpdatedAt: 3_000,
    });
    expect(status).toEqual({ state: "unsupported", observed: "999", supported: "1" });
  });
});
