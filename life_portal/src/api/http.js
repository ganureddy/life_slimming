// Frappe login returns tmp_id/verification at the envelope level.
// Data APIs generally return { message: ... }; retain both through this client.
export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}
export async function request(
  method,
  { args, csrfToken = "", signal, httpMethod } = {},
) {
  let response;
  try {
    response = await fetch("/api/method/" + method, {
      method: httpMethod || (args === undefined ? "GET" : "POST"),
      credentials: "same-origin",
      signal,
      headers: {
        Accept: "application/json",
        ...(args === undefined
          ? {}
          : {
              "Content-Type": "application/json",
              "X-Frappe-CSRF-Token": csrfToken,
            }),
      },
      body: args === undefined ? undefined : JSON.stringify(args),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(
      "Could not reach the server. Check your connection and try again.",
      0,
      "NetworkError",
    );
  }
  const body = await response.json().catch(() => ({}));
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
    else if (response.status === 403)
      message =
        "Your session expired or you do not have permission. Please sign in again.";
    else if (code === "CSRFTokenError")
      message = "Your session changed. Refresh the page and try again.";
    throw new ApiError(message, response.status, code);
  }
  return body;
}
