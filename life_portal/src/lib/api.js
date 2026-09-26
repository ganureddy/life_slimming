import { request } from "../api/http";

export async function call(method, args, { csrfToken, signal } = {}) {
  return (await request(method, { args, csrfToken, signal })).message;
}
