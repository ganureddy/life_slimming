import { request } from "./http";
import { session } from "../lib/session";

export async function getBranches(signal) {
  const { message } = await request("frappe.client.get_list", {
    args: {
      doctype: "Branch",
      fields: ["name"],
      limit_page_length: 0,
      order_by: "name asc",
    },
    csrfToken: session.csrf_token,
    signal,
  });
  return Array.isArray(message) ? message.map((row) => row.name).filter(Boolean) : [];
}

export async function getBranchCommandCenter(params, signal) {
  const body = await request("branch_command_center", {
    args: params,
    csrfToken: session.csrf_token,
    signal,
  });
  return body.message || {};
}

export async function getRosterEmployees(branch = "ALL", signal) {
  const body = await request("roster_employees", {
    args: { branch },
    csrfToken: session.csrf_token,
    signal,
  });
  return Array.isArray(body.message) ? body.message : [];
}
