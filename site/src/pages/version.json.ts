import type { APIRoute } from "astro";
import { BUILD_COMMIT, BUILT_AT } from "../lib/provenance";
import {
  BENCHMARK_HARNESS_VERSION,
  BUILD_ENVIRONMENT,
  RELEASE_VERSION,
  SCHEMA_VERSION,
} from "../lib/release-provenance";

export const prerender = true;

export const GET: APIRoute = () => {
  if (!BUILD_COMMIT || !/^[0-9a-f]{40}$/.test(BUILD_COMMIT)) {
    throw new Error("irrevon-site: version manifest requires a full source commit");
  }
  return new Response(
    JSON.stringify(
      {
        release_version: RELEASE_VERSION,
        commit_sha: BUILD_COMMIT,
        built_at: BUILT_AT,
        benchmark_harness_version: BENCHMARK_HARNESS_VERSION,
        schema_version: SCHEMA_VERSION,
        environment: BUILD_ENVIRONMENT,
      },
      null,
      2,
    ) + "\n",
    {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "public, max-age=0, must-revalidate",
      },
    },
  );
};
