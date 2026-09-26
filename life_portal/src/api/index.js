import endpoints from "./endpoints.json";
import { request } from "./http";
import { session } from "../lib/session";
export { authApi } from "./auth";
export { endpoints };

// One entry point for every migrated business API. Import by catalogue ID.
export async function dataApi(id, params = {}, { signal } = {}) {
  if (!Object.hasOwn(endpoints, id))
    throw new Error("Unknown portal API: " + id);
  const body = await request(endpoints[id], {
    args: params,
    csrfToken: session.csrf_token,
    signal,
  });
  // Some legacy APIs use top-level data/status fields, not only message.
  return body;
}
