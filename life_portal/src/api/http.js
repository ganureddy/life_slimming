import { apiUrl, apiCredentials } from "./config";
import endpoints from "./endpoints.json";
// Frappe login returns tmp_id/verification at the envelope level.
// Data APIs generally return { message: ... }; retain both through this client.
export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}
export function serverMessage(body) {
  try {
    const messages = JSON.parse(body._server_messages || '[]');
    return messages.map(value => {
      const item = typeof value === 'string' ? JSON.parse(value) : value;
      return typeof item?.message === 'string' ? item.message.replace(/<[^>]*>/g, '') : '';
    }).filter(Boolean).join('\n');
  } catch { return ''; }
}
export async function request(
  method,
  { args, csrfToken = "", signal, httpMethod, formData, timeoutMs = 45000 } = {},
) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  let timedOut = false;
  if (signal?.aborted) abort();
  signal?.addEventListener('abort', abort, { once: true });
  const timeout = timeoutMs > 0 ? setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs) : null;
  try {
    let response;
    try {
      response = await fetch(apiUrl("/api/method/" + (endpoints[method] || method)), {
        method: httpMethod || (args === undefined && !formData ? "GET" : "POST"),
        credentials: apiCredentials(),
        signal: controller.signal,
        headers: {
          Accept: "application/json",
          ...(formData ? { "X-Frappe-CSRF-Token": csrfToken } : args === undefined
            ? {}
            : {
                "Content-Type": "application/json",
                "X-Frappe-CSRF-Token": csrfToken,
              }),
        },
        body: formData || (args === undefined ? undefined : JSON.stringify(args)),
      });
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw new ApiError(
        "Could not reach the server. Check your connection and try again.",
        0,
        "NetworkError",
      );
    }
    const body = await response.json().catch(error => {
      if (controller.signal.aborted) throw error;
      return {};
    });
    if (timedOut) throw new DOMException("Request timed out", "AbortError");
    if (!response.ok || body.exc_type) {
      const code = body.exc_type || "";
      let message = "The request could not be completed. Please try again.";
      if (response.status === 429 || code === "InvalidLoginAttempt")
        message = "Too many attempts. Please wait before trying again.";
      else if (code === "ExpiredLoginException")
        message = "This verification session has expired. Please sign in again.";
      else if (response.status === 401 || code === "AuthenticationError")
        message =
          "The credentials or verification code are incorrect. Please try again.";
      else if (code === "CSRFTokenError")
        message = "Your session changed. Refresh the page and try again.";
      else if (response.status === 403)
        message =
          "Your session expired or you do not have permission. Please sign in again.";
      if (['ValidationError', 'MandatoryError', 'PermissionError', 'DoesNotExistError'].includes(code))
        message = serverMessage(body) || message;
      throw new ApiError(message, response.status, code);
    }
    return body;
  } catch (error) {
    if (timedOut && !signal?.aborted && error.name === 'AbortError') throw new ApiError(
      "The server took too long to respond. Refresh this view to check the latest data.",
      0,
      "TimeoutError",
    );
    throw error;
  } finally {
    if (timeout !== null) clearTimeout(timeout);
    signal?.removeEventListener('abort', abort);
  }
}
