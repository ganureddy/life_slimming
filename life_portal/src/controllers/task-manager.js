// Business rules and dynamic report markup are preserved, with page-owned lifecycle.
export function mountTaskManager(page) {
  const { frappe, document, window, setTimeout, clearTimeout } = page;

  var root = page.root;

  if (!root) {
    void 0;
    return;
  }

  // Web Page version: Custom HTML Block Awesome Bar interception removed.

  // ============================================================
  // BASIC HELPERS
  // ============================================================

  function $(selector) {
    return root.querySelector(selector);
  }

  function $all(selector) {
    return Array.prototype.slice.call(root.querySelectorAll(selector));
  }

  function esc(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function stripHtml(value) {
    return String(value || "")
      .replace(/<!--[\s\S]*?-->/g, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
  
function htmlToReadableText(value) {
  value = String(value || "");

  // Remove hidden LIFE metadata
  value = value.replace(/<!--[\s\S]*?-->/g, "");

  // Convert rich text breaks into real line breaks
  value = value
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n")
    .replace(/<\/div>/gi, "\n")
    .replace(/<\/li>/gi, "\n")
    .replace(/<li[^>]*>/gi, "• ");

  // Remove remaining HTML tags
  value = value.replace(/<[^>]+>/g, "");

  // Decode common HTML entities
  value = value
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#039;/g, "'");

  // Clean spaces but preserve line breaks
  value = value
    .replace(/\r/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  // Put numbered points on new lines if older text was saved as one paragraph
  value = value.replace(/\s+(\d+\s+[A-Z])/g, "\n\n$1");

  return value;
}

  function wordCount(value) {
    value = String(value || "").trim();
    return value ? value.split(/\s+/).length : 0;
  }

  function todayDate() {
    return new Date().toISOString().split("T")[0];
  }

  function formatDate(value) {
    if (!value) return "—";
    value = String(value).split(" ")[0];
    var p = value.split("-");
    if (p.length !== 3) return value;
    return p[2] + "/" + p[1] + "/" + p[0];
  }
  
  function formatLifeDate(value) {
  if (!value) return "—";

  value = String(value).split(" ")[0];

  var p = value.split("-");
  if (p.length !== 3) return value;

  var months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
  ];

  var year = p[0].slice(-2);
  var monthIndex = Number(p[1]) - 1;
  var day = p[2];

  return day + "-" + months[monthIndex] + "-" + year;
}

function normalizeDateTimeValue(value) {
  value = String(value || "").trim();

  if (!value) return "";

  value = value.replace(" ", "T");

  if (value.length >= 16) {
    return value.substring(0, 16);
  }

  return value;
}

function getNowReadableDateTime() {
  var d = new Date();

  var yyyy = d.getFullYear();
  var mm = String(d.getMonth() + 1).padStart(2, "0");
  var dd = String(d.getDate()).padStart(2, "0");
  var hh = String(d.getHours()).padStart(2, "0");
  var mi = String(d.getMinutes()).padStart(2, "0");

  return yyyy + "-" + mm + "-" + dd + " " + hh + ":" + mi;
}

function getTaskStartDate(task, meta) {
  meta = meta || {};

  return (
    meta.start_date ||
    getDatePartFromDateTime(task.creation || "") ||
    ""
  );
}

function getTaskCompletedDateTime(task, meta) {
  meta = meta || {};

  if (meta.completed_on) {
    return meta.completed_on;
  }

  // Fallback for old completed tasks before completed_on was added
  if (getTaskStatus(task) === "Completed") {
    return task.modified || task.date || "";
  }

  return getNowLocalDateTime();
}

function calculateWorkedDaysLabel(task, meta) {
  meta = meta || {};

  var startDate = getTaskStartDate(task, meta);
  var endDateTime = getTaskCompletedDateTime(task, meta);
  var endDate = getDatePartFromDateTime(endDateTime);

  if (!startDate || !endDate) return "—";

  var start = new Date(startDate + "T00:00:00");
  var end = new Date(endDate + "T00:00:00");

  var diff = Math.round((end - start) / (1000 * 60 * 60 * 24));

  if (diff < 0) return "Invalid";

  if (diff === 0) return "Same day";

  return diff + " day" + (diff > 1 ? "s" : "");
}

  function formatFileSize(bytes) {
    bytes = Number(bytes || 0);
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
    return Math.round((bytes / (1024 * 1024)) * 10) / 10 + " MB";
  }
  
  function getTodayLocalDate() {
  var d = new Date();
  var yyyy = d.getFullYear();
  var mm = String(d.getMonth() + 1).padStart(2, "0");
  var dd = String(d.getDate()).padStart(2, "0");

  return yyyy + "-" + mm + "-" + dd;
}

function getNowLocalDateTime() {
  var d = new Date();
  var yyyy = d.getFullYear();
  var mm = String(d.getMonth() + 1).padStart(2, "0");
  var dd = String(d.getDate()).padStart(2, "0");
  var hh = String(d.getHours()).padStart(2, "0");
  var mi = String(d.getMinutes()).padStart(2, "0");

  return yyyy + "-" + mm + "-" + dd + "T" + hh + ":" + mi;
}

function getDatePartFromDateTime(value) {
  value = String(value || "");
  return value ? value.split("T")[0].split(" ")[0] : "";
}

function formatLifeDateTime(value) {
  if (!value) return "—";

  value = String(value);
  var datePart = value.split("T")[0].split(" ")[0];
  var timePart = "";

  if (value.indexOf("T") !== -1) {
    timePart = value.split("T")[1] || "";
  } else if (value.indexOf(" ") !== -1) {
    timePart = value.split(" ")[1] || "";
  }

  timePart = timePart ? timePart.substring(0, 5) : "";

  return formatLifeDate(datePart) + (timePart ? " " + timePart : "");
}

function calculateTaskDurationDays(startDate, deadlineDateTime) {
  var endDate = getDatePartFromDateTime(deadlineDateTime);

  if (!startDate || !endDate) return "";

  var start = new Date(startDate + "T00:00:00");
  var end = new Date(endDate + "T00:00:00");

  var diff = Math.round((end - start) / (1000 * 60 * 60 * 24));

  if (diff < 0) return "Invalid";

  if (diff === 0) return "Same day";

  return diff + " day" + (diff > 1 ? "s" : "");
}

function updateTaskDateRules() {
  var startEl = $("#task-startdate");
  var deadlineEl = $("#task-deadline");
  var durationEl = $("#task-duration-label");

  var today = getTodayLocalDate();
  var nowDateTime = getNowLocalDateTime();

  if (startEl) {
    startEl.setAttribute("min", today);
  }

  if (deadlineEl) {
    deadlineEl.setAttribute("min", nowDateTime);
  }

  var startDate = startEl ? startEl.value : "";
  var deadlineDateTime = deadlineEl ? deadlineEl.value : "";

  if (startDate && startDate < today) {
    startEl.value = today;
    startDate = today;
    showModal("⚠️", "Past Date Not Allowed", "Task Start Date cannot be a past date.");
  }

  if (deadlineDateTime && deadlineDateTime < nowDateTime) {
    deadlineEl.value = "";
    deadlineDateTime = "";
    showModal("⚠️", "Past Deadline Not Allowed", "Task Deadline cannot be a past date/time.");
  }

  if (startDate && deadlineDateTime) {
    var deadlineDate = getDatePartFromDateTime(deadlineDateTime);

    if (deadlineDate < startDate) {
      deadlineEl.value = "";
      if (durationEl) durationEl.textContent = "";
      showModal("⚠️", "Invalid Deadline", "Task Deadline cannot be before Task Start Date.");
      return;
    }

    if (durationEl) {
      durationEl.textContent = calculateTaskDurationDays(startDate, deadlineDateTime);
    }
  } else {
    if (durationEl) durationEl.textContent = "";
  }
}

function validateTaskDatesBeforeSubmit(startDate, deadlineDateTime) {
  var today = getTodayLocalDate();
  var nowDateTime = getNowLocalDateTime();

  if (!startDate || !deadlineDateTime) {
    return {
      ok: false,
      message: "Please select both Task Start Date and Task Deadline Date & Time."
    };
  }

  if (startDate < today) {
    return {
      ok: false,
      message: "Task Start Date cannot be a past date."
    };
  }

  if (deadlineDateTime < nowDateTime) {
    return {
      ok: false,
      message: "Task Deadline Date & Time cannot be in the past."
    };
  }

  if (getDatePartFromDateTime(deadlineDateTime) < startDate) {
    return {
      ok: false,
      message: "Task Deadline cannot be before Task Start Date."
    };
  }

  return {
    ok: true,
    message: ""
  };
}

  function setText(id, value) {
    var el = $("#" + id);
    if (el) el.textContent = value || "";
  }

  function setValue(id, value) {
    var el = $("#" + id);
    if (el) el.value = value || "";
  }

  function getValue(id) {
    var el = $("#" + id);
    return el ? String(el.value || "").trim() : "";
  }

  function showModal(icon, title, text) {
    setText("modal-icon", icon || "ℹ️");
    setText("modal-title", title || "");
    setText("modal-text", text || "");

    var modal = $("#modal");
    if (modal) modal.classList.add("show");
  }

  function closeModal() {
    var modal = $("#modal");
    if (modal) modal.classList.remove("show");
  }
  

function buildTicketDetailsHtml(t, meta) {
  meta = meta || {};

  var details = getTicketDetails(t);
  var status = getTicketStatus(t);
  var ccText = (meta.cc_to || []).map(userDisplayName).join(", ") || "—";

  return '' +
    '<div class="life-detail-modal-wrap">' +

      '<div class="life-detail-top-tags">' +
        '<div class="life-detail-tag">🎫 Status: ' + esc(status || "—") + '</div>' +
        '<div class="life-detail-tag">📌 Priority: ' + esc(t.priority || "—") + '</div>' +
        '<div class="life-detail-tag">🏢 Branch: ' + esc(meta.branch || "—") + '</div>' +
      '</div>' +

      '<div class="life-detail-section">' +
        '<div class="life-detail-section-title">Ticket Information</div>' +

        '<div class="life-detail-grid">' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Ticket ID</div>' +
            '<div class="life-detail-value">' + esc(t.name || "—") + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Raised By</div>' +
            '<div class="life-detail-value">' + esc(userDisplayName(t.raised_by || t.owner)) + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Raised On</div>' +
            '<div class="life-detail-value">' + esc(formatLifeDate(t.opening_date || t.creation)) + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Category</div>' +
            '<div class="life-detail-value">' + esc(meta.category || "—") + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Issue</div>' +
            '<div class="life-detail-value">' + esc(meta.issue || t.subject || "—") + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Tagged To</div>' +
            '<div class="life-detail-value">' + esc(userDisplayName(meta.tag_to || "")) + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">CC To</div>' +
            '<div class="life-detail-value">' + esc(ccText) + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Created By</div>' +
            '<div class="life-detail-value">' + esc(userDisplayName(t.owner || "")) + '</div>' +
          '</div>' +

        '</div>' +
      '</div>' +

      '<div class="life-detail-section">' +
        '<div class="life-detail-section-title">Issue Details</div>' +
        '<div class="life-detail-box">' + esc(details || "—") + '</div>' +
      '</div>' +

    '</div>';
}
  
  function showRichModal(icon, title, html) {
  setText("modal-icon", icon || "ℹ️");
  setText("modal-title", title || "");

  var textEl = $("#modal-text");
  if (textEl) {
    textEl.innerHTML = html || "";
  }

  var modal = $("#modal");
  if (modal) modal.classList.add("show");
}


function modalAttachmentHtml(doctype, docname) {
  var rows = (attachmentCache[doctype] && attachmentCache[doctype][docname]) || [];

  if (!rows.length) {
    return '' +
      '<div class="life-modal-attachments">' +
        '<div class="life-modal-section-title">Attachments</div>' +
        '<div class="life-modal-muted">No attachments uploaded.</div>' +
      '</div>';
  }

  return '' +
    '<div class="life-modal-attachments">' +
      '<div class="life-modal-section-title">Attachments</div>' +
      rows.map(function (f) {
        var fileName = f.file_name || f.file_url || "Open File";
        var fileUrl = f.file_url || "";

        return '' +
          '<div class="life-modal-file-row">' +
            '<div>📎 ' + esc(fileName) + '</div>' +
            (
              fileUrl
                ? '<a href="' + esc(fileUrl) + '" target="_blank" class="life-modal-file-link">Open</a>'
                : ''
            ) +
          '</div>';
      }).join("") +
    '</div>';
}

  function toast(message, ok) {
    if (window.frappe && frappe.show_alert) {
      frappe.show_alert({
        message: message,
        indicator: ok ? "green" : "red"
      });
    } else {
      showModal(ok ? "✅" : "⚠️", ok ? "Success" : "Error", message);
    }
  }

  function getErrorMessage(err) {
    if (!err) return "Something went wrong.";

    if (err._server_messages) {
      try {
        var msgs = JSON.parse(err._server_messages);
        return msgs.map(function (m) {
          try {
            return JSON.parse(m).message || m;
          } catch (e) {
            return m;
          }
        }).join("<br>");
      } catch (e2) {}
    }

    return err.message || err.exception || String(err);
  }
  



function shortPreviewText(text, limit) {
  text = String(text || "").replace(/\s+/g, " ").trim();
  limit = limit || 120;

  if (text.length <= limit) return text;

  return text.substring(0, limit).trim() + "...";
}

var detailHtmlRegistry = {};

function registerDetailHtml(title, html, afterHtml) {
  var id = "DETAIL-" + Date.now() + "-" + Math.floor(Math.random() * 100000);

  detailHtmlRegistry[id] = {
    title: title || "Details",
    html: html || "",
    afterHtml: afterHtml || ""
  };

  return id;
}

function renderDescriptionCell(previewText, title, doctype, docname, modalHtml, afterHtml) {
  previewText = String(previewText || "").trim();

  if (!previewText) {
    return '<span style="color:#8C8C8C">—</span>';
  }

  var id = registerDetailHtml(
    title || "Details",
    modalHtml || "",
    afterHtml || ""
  );

  return '' +
    '<div class="life-desc-cell">' +
      '<div class="life-desc-preview" title="' + esc(previewText) + '">' +
        esc(shortPreviewText(previewText, 130)) +
      '</div>' +
      '<button type="button" class="life-view-details-btn" ' +
        'data-detail-html-id="' + esc(id) + '" ' +
        'data-doctype="' + esc(doctype || "") + '" ' +
        'data-docname="' + esc(docname || "") + '">' +
        'View Details' +
      '</button>' +
    '</div>';
}


function bindDescriptionButtons(scope) {
  (scope || root).querySelectorAll(".life-view-details-btn").forEach(function (btn) {
    if (btn.dataset.boundDesc === "1") return;

    btn.dataset.boundDesc = "1";

    btn.addEventListener("click", function () {
      var id = btn.dataset.detailHtmlId || "";
      var row = detailHtmlRegistry[id] || {};

      var doctype = btn.dataset.doctype || "";
      var docname = btn.dataset.docname || "";

      var attachmentsHtml = modalAttachmentHtml(doctype, docname);

      var html =
        (row.html || "") +
        attachmentsHtml +
        (row.afterHtml || "");

      showRichModal("📄", row.title || "Details", html);
    });
  });
}


function buildTaskDelayHistoryHtml(history) {
  history = history || [];

  if (!history.length) {
    return '<div class="life-empty-history">No delay review history available.</div>';
  }

  return '' +
    '<div class="life-history-list">' +
      history.map(function (h, idx) {
        return '' +
          '<div class="life-history-card">' +
            '<div class="life-history-head">' +
              '<div class="life-history-title">Review #' + (idx + 1) + ' - ' + esc(h.reviewed_by_name || h.reviewed_by || "—") + '</div>' +
              '<div class="life-history-date">' + esc(h.reviewed_on || "—") + '</div>' +
            '</div>' +

            '<div class="life-history-grid">' +
              '<div>' +
                '<div class="life-detail-label">Old Deadline</div>' +
                '<div class="life-detail-value">' + esc(formatLifeDateTime(h.old_deadline || "")) + '</div>' +
              '</div>' +
              '<div>' +
                '<div class="life-detail-label">New Deadline</div>' +
                '<div class="life-detail-value">' + esc(formatLifeDateTime(h.new_deadline || "")) + '</div>' +
              '</div>' +
            '</div>' +

            '<div class="life-detail-label">Remarks</div>' +
            '<div class="life-history-remarks">' + esc(h.remarks || "—") + '</div>' +
          '</div>';
      }).join("") +
    '</div>';
}

function buildTaskDelayHistorySection(meta) {
  meta = meta || {};

  return '' +
    '<div class="life-detail-section">' +
      '<div class="life-detail-section-title">Delay Review History</div>' +
      buildTaskDelayHistoryHtml(meta.delay_reviews || []) +
    '</div>';
}


function buildTaskDetailsHtml(t, meta, details, updateTo) {
  meta = meta || {};
  details = details || "—";
  updateTo = updateTo || "—";

  var status = getTaskStatus(t);
  var durationText =
    meta.duration_label ||
    calculateTaskDurationDays(meta.start_date, meta.deadline_datetime || t.date) ||
    "—";
    var workedDays = meta.worked_days || calculateWorkedDaysLabel(t, meta);

  return '' +
    '<div class="life-detail-modal-wrap">' +

      '<div class="life-detail-top-tags">' +
        '<div class="life-detail-tag">📌 Priority: ' + esc(t.priority || "—") + '</div>' +
        '<div class="life-detail-tag">📍 Status: ' + esc(status || "—") + '</div>' +
        '<div class="life-detail-tag">⏱ Duration: ' + esc(durationText) + '</div>' +
        '<div class="life-detail-tag">🧮 Worked: ' + esc(workedDays) + '</div>' +
        '<div class="life-detail-tag">🗂 Category: ' + esc(meta.category || "—") + '</div>' +
      '</div>' +

      '<div class="life-detail-section">' +
        '<div class="life-detail-section-title">Task Information</div>' +
        '<div class="life-detail-grid">' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Assigned By</div>' +
            '<div class="life-detail-value">' + esc(userDisplayName(t.assigned_by || t.owner)) + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Assigned To</div>' +
            '<div class="life-detail-value">' + esc(userDisplayName(t.allocated_to)) + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Start Date</div>' +
            '<div class="life-detail-value">' + esc(formatLifeDate(meta.start_date || "")) + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Deadline</div>' +
            '<div class="life-detail-value">' + esc(formatLifeDateTime(meta.deadline_datetime || t.date)) + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Update To</div>' +
            '<div class="life-detail-value">' + esc(updateTo || "—") + '</div>' +
          '</div>' +

          '<div class="life-detail-item">' +
            '<div class="life-detail-label">Created By</div>' +
            '<div class="life-detail-value">' + esc(userDisplayName(t.owner || "")) + '</div>' +
          '</div>' +

        '</div>' +
      '</div>' +

      '<div class="life-detail-section">' +
        '<div class="life-detail-section-title">Task Details</div>' +
        '<div class="life-detail-box">' + esc(details || "—") + '</div>' +
      '</div>' +

    '</div>';
}


  function initials(name) {
    return String(name || "?")
      .split(/\s+/)
      .map(function (w) { return w.charAt(0); })
      .join("")
      .slice(0, 2)
      .toUpperCase();
  }

 function userLabel(email) {
  var value = String(email || "").trim();

  var u = users.find(function (x) {
    return x.name === value || x.full_name === value;
  });

  return u ? (u.full_name || u.name) : (value || "—");
}

function userDisplayName(value) {
  value = String(value || "").trim();

  if (!value) return "—";

  if (value === currentUser) {
    return currentUserFullName || value;
  }

  var u = users.find(function (x) {
    return (
      x.name === value ||
      x.full_name === value ||
      String(x.name || "").toLowerCase() === value.toLowerCase() ||
      String(x.full_name || "").toLowerCase() === value.toLowerCase()
    );
  });

  if (u) {
    return u.full_name || u.name;
  }

  // fallback for emails if User list did not return full_name
  if (value.indexOf("@") !== -1) {
    return value.split("@")[0];
  }

  return value;
}

function escapeRegex(value) {
  return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractLabelValue(text, label, nextLabels) {
  text = String(text || "").replace(/\s+/g, " ").trim();
  nextLabels = nextLabels || [];

  var endPattern = "$";

  if (nextLabels.length) {
    endPattern = "\\s+(?:" + nextLabels.map(escapeRegex).join("|") + ")\\s*:";
  }

  var re = new RegExp(
    escapeRegex(label) + "\\s*:\\s*([\\s\\S]*?)(?=" + endPattern + "|$)",
    "i"
  );

  var m = text.match(re);

  return m && m[1] ? String(m[1]).trim() : "";
}

function resolveUserValue(value) {
  value = String(value || "").trim();

  if (!value) return "";

  var u = users.find(function (x) {
    return (
      String(x.name || "").toLowerCase() === value.toLowerCase() ||
      String(x.full_name || "").toLowerCase() === value.toLowerCase()
    );
  });

  return u ? u.name : value;
}

function isCurrentUserValue(value) {
  value = String(value || "").trim();

  return (
    value === currentUser ||
    value === currentUserFullName ||
    userLabel(value) === currentUserFullName
  );
}

  function findUserByNameOrEmail(value) {
    value = String(value || "").toLowerCase();

    return users.find(function (u) {
      return (
        String(u.name || "").toLowerCase() === value ||
        String(u.full_name || "").toLowerCase() === value
      );
    });
  }

  function priorityPill(priority) {
    var cls = priority === "High" ? "p-r" : priority === "Medium" ? "p-o" : "p-g";
    return '<span class="pill ' + cls + '">' + esc(priority || "—") + "</span>";
  }

  function statusPill(status) {
    var cls = "p-gy";

    if (["Open", "Pending"].indexOf(status) !== -1) cls = "p-n";
    if (["In Progress"].indexOf(status) !== -1) cls = "p-o";
    if (["Closed", "Completed", "Resolved"].indexOf(status) !== -1) cls = "p-g";
    if (["Overdue", "Cancelled"].indexOf(status) !== -1) cls = "p-r";

    return '<span class="pill ' + cls + '">' + esc(status || "—") + "</span>";
  }

  // ============================================================
  // STATE
  // ============================================================

  var currentUser = "";
  var currentUserFullName = "";
  var isManager = false;
  var canViewAllReports = false;
  var currentUserRoles = [];

  var users = [];
  var employeeGenderByUser = {};
  var tasks = [];
  var tickets = [];

  var selectedTaskPriority = "";
  var selectedTicketPriority = "";

  var taskAssignTo = [];
  var taskUpdateTo = [];
  var ticketTagTo = [];
  var ticketCcTo = [];

  var taskFiles = [];
  var ticketFiles = [];
  var taskUpdateFiles = [];

  var attachmentCache = {
    ToDo: {},
    Issue: {}
  };
  
  var TABLE_PAGE_SIZE = 15;

var tablePageState = {
  taskReport: 1,
  myTaskTo: 1,
  myTaskBy: 1,
  ticketReport: 1,
  myTicketToMe: 1,
  myTicketByMe: 1
};

function resetTablePage(key) {
  tablePageState[key] = 1;
}

function getPaginatedRows(key, rows) {
  rows = rows || [];

  var total = rows.length;
  var totalPages = Math.max(1, Math.ceil(total / TABLE_PAGE_SIZE));

  var page = Number(tablePageState[key] || 1);

  if (page < 1) page = 1;
  if (page > totalPages) page = totalPages;

  tablePageState[key] = page;

  var start = (page - 1) * TABLE_PAGE_SIZE;
  var end = Math.min(start + TABLE_PAGE_SIZE, total);

  return {
    rows: rows.slice(start, end),
    total: total,
    page: page,
    totalPages: totalPages,
    start: total ? start + 1 : 0,
    end: end
  };
}

function getModifiedTime(row) {
  var value =
    row.modified ||
    row.creation ||
    row.opening_date ||
    row.date ||
    "";

  value = String(value || "").replace(" ", "T");

  var time = new Date(value).getTime();

  return isNaN(time) ? 0 : time;
}

function sortByModifiedLatest(rows) {
  return (rows || []).slice().sort(function (a, b) {
    return getModifiedTime(b) - getModifiedTime(a);
  });
}

function renderTablePagination(body, key, pageData, renderFn) {
  if (!body || !pageData) return;

  var wrap = body.closest(".tbl-wrap") || body.closest("table");
  if (!wrap || !wrap.parentNode) return;

  var pagerId = "life-pager-" + key;
  var pager = $("#" + pagerId);

  if (!pager) {
    pager = document.createElement("div");
    pager.id = pagerId;
    pager.className = "life-table-pager";
    wrap.parentNode.insertBefore(pager, wrap.nextSibling);
  }

  if (!pageData.total) {
    pager.innerHTML = "";
    return;
  }

  pager.innerHTML =
    '<span>Showing ' + pageData.start + ' - ' + pageData.end + ' of ' + pageData.total + '</span>' +
    '<button type="button" data-act="prev" ' + (pageData.page <= 1 ? "disabled" : "") + '>Previous</button>' +
    '<span>Page ' + pageData.page + ' / ' + pageData.totalPages + '</span>' +
    '<button type="button" data-act="next" ' + (pageData.page >= pageData.totalPages ? "disabled" : "") + '>Next</button>';

  pager.querySelectorAll("button[data-act]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var act = btn.dataset.act || "";

      if (act === "prev") {
        tablePageState[key] = Math.max(1, Number(tablePageState[key] || 1) - 1);
      }

      if (act === "next") {
        tablePageState[key] = Number(tablePageState[key] || 1) + 1;
      }

      renderFn();
    });
  });
}
  
  // ============================================================
// ATTACHMENT CACHE + TABLE ATTACHMENT CHIPS
// Required for All Tasks / All Tickets table rendering
// ============================================================

function loadAttachmentCache(doctype, docnames, done) {
  docnames = (docnames || []).filter(Boolean);

  if (!attachmentCache[doctype]) {
    attachmentCache[doctype] = {};
  }

  docnames.forEach(function (name) {
    attachmentCache[doctype][name] = [];
  });

  if (!docnames.length) {
    if (done) done();
    return;
  }

  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "File",
      fields: [
        "name",
        "file_name",
        "file_url",
        "attached_to_doctype",
        "attached_to_name",
        "is_private",
        "file_size"
      ],
      filters: [
        ["File", "attached_to_doctype", "=", doctype],
        ["File", "attached_to_name", "in", docnames]
      ],
      limit_page_length: 1000
    },
    callback: function (r) {
      var rows = r.message || [];

      rows.forEach(function (f) {
        var attachedName = f.attached_to_name || "";

        if (!attachmentCache[doctype][attachedName]) {
          attachmentCache[doctype][attachedName] = [];
        }

        attachmentCache[doctype][attachedName].push(f);
      });

      if (done) done();
    },
    error: function () {
      if (done) done();
    }
  });
}

function attachmentChip(doctype, docname) {
  var rows =
    attachmentCache[doctype] &&
    attachmentCache[doctype][docname]
      ? attachmentCache[doctype][docname]
      : [];

  if (!rows.length) {
    return '<span style="color:#8C8C8C;font-weight:700">—</span>';
  }

  return '' +
    '<span class="attach-chip-table" ' +
      'data-doctype="' + esc(doctype || "") + '" ' +
      'data-docname="' + esc(docname || "") + '">' +
      '📎 ' + rows.length +
    '</span>';
}

function bindAttachmentChips(scope) {
  (scope || root).querySelectorAll(".attach-chip-table").forEach(function (chip) {
    if (chip.dataset.boundAttachmentChip === "1") return;

    chip.dataset.boundAttachmentChip = "1";

    chip.addEventListener("click", function () {
      var doctype = chip.dataset.doctype || "";
      var docname = chip.dataset.docname || "";

      showRichModal(
        "📎",
        "Attachments",
        modalAttachmentHtml(doctype, docname)
      );
    });
  });
}

  var MANAGER_EMAILS = [
    "Administrator",
    "administrator",
    "narendhar@lifescc.com"
  ];

  var TASK_CATEGORIES = [
    "Sales",
    "Services",
    "Audit",
    "Marketing",
    "Machinery",
    "Accounts",
    "HR",
    "IT",
    "Operations",
    "Inventory / Stock"
  ];
  
  var TASK_STATUS_FILTERS = [
  "Open",
  "Reopened",
  "Completed",
  "Overdue",
  "Closed",
  "Cancelled"
];

var TICKET_STATUS_FILTERS = [
  "Open",
  "Reopened",
  "Resolved",
  "Closed"
];

  var BRANCHES = [
    "Head Office",
    "Chandanagar",
    "S R Nagar",
    "Madhapur",
    "Banjara Hills",
    "Himayathnagar",
    "Dilsukhnagar",
    "Gachibowli",
    "Vijayawada",
    "Vizag",
    "Nellore",
    "Kukatpally"
  ];

  var TICKET_CATEGORY_MAP = {
    "Electrical / Equipment": [
      "AC Not Working",
      "TV Not Working",
      "Lighting Issue / Bulb Fused",
      "Plumbing Issue",
      "Water Cooler / RO Not Working",
      "Generator / Power Backup Failure",
      "Fire Extinguisher Expired",
      "Other"
    ],
    "Clinical Machinery": [
      "Slimming Machine Not Working",
      "Laser Machine Malfunction",
      "Cavitation / RF Machine Issue",
      "Cryo / Fat Freezing Unit Issue",
      "Hydra Facial Machine Issue",
      "Machine Calibration Required",
      "Machine Annual Maintenance Due",
      "Spare Part Required",
      "Other"
    ],
    "IT / ERP / Software": [
      "Billing Software Issue",
      "ERP Login Issue",
      "Client Data Not Loading",
      "Network / WiFi Issue",
      "Printer Not Working",
      "Biometric / Attendance Device Issue",
      "CCTV Not Working",
      "Email Not Working",
      "Other"
    ],
    "Human Resources": [
      "Need HR Assistance",
      "Payroll / Salary Query",
      "Leave / Attendance Issue",
      "Policy Clarification",
      "Appointment Letter / Documents Request",
      "PF / ESI Query",
      "Training Request",
      "Other"
    ],
    "Asset / Missing Item": [
      "Missing Asset",
      "Lost Phone",
      "Lost Laptop",
      "Damaged Equipment",
      "Furniture Damaged",
      "Uniform Not Issued",
      "Stationery Shortage",
      "Other"
    ],
    "Employee Conduct": [
      "Facing Issue With Another Employee",
      "Harassment Complaint",
      "Behavioural Concern",
      "Discrimination Complaint",
      "Unprofessional Conduct by Staff",
      "Other"
    ],
    "Operations": [
      "Branch Maintenance Issue",
      "Staffing Shortage",
      "Process / Workflow Issue",
      "Appointment Scheduling Conflict",
      "Branch Cleanliness Issue",
      "Housekeeping Request",
      "Other"
    ],
    "Accounts / Billing": [
      "Payment Discrepancy",
      "Invoice Issue",
      "Reimbursement Query",
      "Refund Processing Delay",
      "GST / Tax Query",
      "Petty Cash Shortage",
      "Bank Deposit Issue",
      "Other"
    ],
    "Marketing": [
      "Campaign Material Request",
      "Marketing Collateral Damaged",
      "Social Media Query Escalation",
      "Lead / Enquiry Not Assigned",
      "Signage / Branding Issue",
      "Other"
    ],
    "Inventory / Stock": [
      "Consumable Stock Shortage",
      "Cosmetic Product Stock Shortage",
      "Stock Damage / Expiry",
      "Reorder Request",
      "Stock Mismatch",
      "Other"
    ],
    "Security": [
      "Theft",
      "Unauthorized Access",
      "Suspicious Activity",
      "CCTV Footage Request",
      "Visitor / Vendor Access Issue",
      "Other"
    ],
    "Client / Treatment Related": [
      "Client Allergic Reaction",
      "Client Dissatisfaction — Need Doctor Review",
      "Consent Form Missing",
      "Treatment Protocol Clarification Needed",
      "Client Photo / Before-After Missing",
      "Other"
    ],
    "Front Office / Reception": [
      "Appointment Double-Booked",
      "Walk-in Client Waiting Too Long",
      "Reception Handover Issue",
      "Client Call Not Returned",
      "Other"
    ],
    "Facility / Housekeeping": [
      "Washroom Maintenance",
      "Pest Control Required",
      "Linen / Towel Shortage",
      "Parking Issue",
      "Other"
    ]
  };

  var EMPLOYEE_INVOLVED_ISSUES = [
    "Facing Issue With Another Employee",
    "Harassment Complaint",
    "Discrimination Complaint",
    "Behavioural Concern"
  ];

  var CATEGORY_TAG_TO_SUGGEST = {
    "IT / ERP / Software": "narendhar",
    "Human Resources": "viveka",
    "Accounts / Billing": "satya",
    "Marketing": "sridevi",
    "Inventory / Stock": "valli",
    "Operations": "surya",
    "Clinical Machinery": "anand"
  };

  // ============================================================
  // META STORAGE IN DESCRIPTION
  // ============================================================

  function makeMetaBlock(type, meta) {
    return "<!--LIFE_" + type + "_META:" + JSON.stringify(meta || {}) + "-->";
  }

  function parseMeta(description, type) {
    var re = new RegExp("<!--LIFE_" + type + "_META:([\\s\\S]*?)-->");
    var m = String(description || "").match(re);

    if (!m || !m[1]) return {};

    try {
      return JSON.parse(m[1]);
    } catch (e) {
      return {};
    }
  }

  function removeMeta(description) {
    return String(description || "").replace(/<!--LIFE_[A-Z]+_META:[\s\S]*?-->/g, "").trim();
  }

  function buildTaskDescription(details, meta) {
    return makeMetaBlock("TASK", meta) + "\n" + esc(details).replace(/\n/g, "<br>");
  }

  function buildTicketDescription(details, meta) {
    var parts = [];

    parts.push(makeMetaBlock("TICKET", meta));
    parts.push("<b>Branch:</b> " + esc(meta.branch || ""));
    parts.push("<b>Category:</b> " + esc(meta.category || ""));
    parts.push("<b>Issue:</b> " + esc(meta.issue || ""));

    if (meta.other_text) {
      parts.push("<b>Other Issue:</b> " + esc(meta.other_text));
    }

    if (meta.employee_involved) {
      parts.push("<b>Employee Involved:</b> " + esc(meta.employee_involved));
    }

    parts.push("<b>Tagged To:</b> " + esc(userLabel(meta.tag_to || "")));

    if (meta.cc_to && meta.cc_to.length) {
      parts.push("<b>CC To:</b> " + esc(meta.cc_to.map(userLabel).join(", ")));
    }

    parts.push("<br><b>Details:</b><br>" + esc(details).replace(/\n/g, "<br>"));

    return parts.join("<br>");
  }
  
  function bindRefreshButton() {
  var btn = $("#life-refresh-btn");

  if (!btn) return;

  btn.addEventListener("click", function () {
    refreshTaskTicketBlock();
  });
}

function refreshTaskTicketBlock() {
  var btn = $("#life-refresh-btn");
  var note = $("#life-refresh-note");

  if (btn) {
    btn.disabled = true;
    btn.textContent = "Refreshing...";
  }

  if (note) {
    note.textContent = "Please wait";
  }

  // Clear old table rows while refreshing
  var taskBody = $("#task-report-body");
  var ticketBody = $("#ticket-report-body");
  var myTaskToBody = $("#mytask-to-body");
  var myTaskByBody = $("#mytask-by-body");
  var myTicketToMeBody = $("#myticket-tome-body");
  var myTicketByMeBody = $("#myticket-byme-body");

  if (taskBody) taskBody.innerHTML = "";
  if (ticketBody) ticketBody.innerHTML = "";
  if (myTaskToBody) myTaskToBody.innerHTML = "";
  if (myTaskByBody) myTaskByBody.innerHTML = "";
  if (myTicketToMeBody) myTicketToMeBody.innerHTML = "";
  if (myTicketByMeBody) myTicketByMeBody.innerHTML = "";

  attachmentCache = {
    ToDo: {},
    Issue: {}
  };

  loadCurrentUser();
  loadTasks(); loadTickets();
  loadUsers(function () {
    page.setUsers(users);
    renderTaskReport(); renderMyTasks(); renderTicketReport(); renderMyTickets(); renderCounts();
  });
  page.whenIdle().then(function (result) {
    if (!page.isActive()) return;
    if (btn) { btn.disabled = false; btn.textContent = '↻ Refresh'; }
    if (!result.ok) {
      if (note) note.textContent = 'Refresh failed. Please retry.';
      return;
    }
    if (note) {
      note.textContent = 'Updated just now';
      setTimeout(function () { note.textContent = ''; }, 2500);
    }
    toast('Task Manager refreshed successfully.', true);
  });
}

function updateActiveTabNote(type, idx) {
  var note = $("#life-tab-note");

  if (!note) return;

  var notes = {
    task: {
      0: "Assign New Task: Create a new internal task, set priority, deadline, assignee, update recipients, and optional attachments.",
      1: "All Tasks Report: View and filter all task records by category, priority, and status.",
      2: "My Tasks: Track tasks assigned to you and tasks created by you."
    },
    ticket: {
      0: "Raise New Ticket: Submit a new branch/helpdesk issue with category, resolver, CC users, priority, details, and attachments.",
      1: "All Tickets Report: View and filter all tickets raised across permitted records.",
      2: "My Tickets: Track tickets tagged to you, CC’d to you, and tickets raised by you."
    }
  };

  note.textContent =
    notes[type] && notes[type][idx]
      ? notes[type][idx]
      : "Select a tab to view its purpose.";
}

function normalizeEmployeeGender(value) {
  value = String(value || "").trim().toLowerCase();

  if (!value) return "neutral";

  // Check female first because "female" contains "male"
  if (value.indexOf("female") !== -1 || value === "f") return "female";
  if (value.indexOf("male") !== -1 || value === "m") return "male";

  return "neutral";
}

function getAssigneeGender(assignee) {
  assignee = String(assignee || "").trim();

  if (!assignee || assignee === "Unassigned") {
    return "neutral";
  }

  var displayName = userDisplayName(assignee);
  var userName = userLabel(assignee);

  return normalizeEmployeeGender(
    employeeGenderByUser[assignee] ||
    employeeGenderByUser[assignee.toLowerCase()] ||
    employeeGenderByUser[displayName] ||
    employeeGenderByUser[String(displayName || "").toLowerCase()] ||
    employeeGenderByUser[userName] ||
    employeeGenderByUser[String(userName || "").toLowerCase()] ||
    ""
  );
}


function buildAssigneeGenderIconHtml(assignee) {
  var gender = getAssigneeGender(assignee);

  var symbol = "•";
  if (gender === "male") symbol = "♂";
  if (gender === "female") symbol = "♀";

  return '' +
    '<span class="life-assignee-person-icon life-gender-' + esc(gender) + '" ' +
      'title="' + esc(gender === "neutral" ? "Gender not set" : gender) + '" ' +
      'aria-hidden="true">' +
      esc(symbol) +
    '</span>';
}

function loadEmployeeGenderMap(done) {
  employeeGenderByUser = {};

  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "Employee",
      fields: ["name", "employee_name", "user_id", "gender", "status"],
      filters: {
        status: "Active"
      },
      limit_page_length: 1000
    },
    callback: function (r) {
      var rows = r.message || [];

      rows.forEach(function (emp) {
        var gender = emp.gender || "";

        if (emp.user_id) {
          employeeGenderByUser[String(emp.user_id).trim()] = gender;
          employeeGenderByUser[String(emp.user_id).trim().toLowerCase()] = gender;
        }

        if (emp.employee_name) {
          employeeGenderByUser[String(emp.employee_name).trim()] = gender;
          employeeGenderByUser[String(emp.employee_name).trim().toLowerCase()] = gender;
        }

        if (emp.name) {
          employeeGenderByUser[String(emp.name).trim()] = gender;
          employeeGenderByUser[String(emp.name).trim().toLowerCase()] = gender;
        }
      });

      if (done) done();
    },
    error: function () {
      if (done) done();
    }
  });
}

function setDefaultTaskStartDate() {
  var startEl = $("#task-startdate");
  if (startEl && !startEl.value) {
    var today = getTodayLocalDate();
    startEl.value = today;
  }
}


function forceDefaultTaskStartDate() {
  var startEl = $("#task-startdate");
  if (startEl) {
    var today = getTodayLocalDate();
    startEl.value = today;
  }
}


  // ============================================================
  // INIT
  // ============================================================

  function init() {
    bindModuleTabs();
    bindSubTabs();
    bindPriorityButtons();
    bindWordCounts();
    updateWordCount($("#task-details"), $("#task-wordcount"), 100);
updateWordCount($("#ticket-other-text"), $("#ticket-other-wordcount"), 100);
    bindTicketCategoryEvents();
    bindPickers();
    bindAttachments();
    bindButtons();
    bindModal();
    bindTaskDateRules();
    bindRefreshButton();

    populateStaticDropdowns();
    updateActiveTabNote("task", 0);
    loadCurrentUser(function () {
      applyReportTabVisibility();

      loadTasks();
      loadTickets();
      loadUsers(function () {
        page.setUsers(users);
        renderTaskReport(); renderMyTasks();
        renderTicketReport(); renderMyTickets(); renderCounts();
      });
    });
    
    forceDefaultTaskStartDate();
  }

  // ============================================================
  // BINDINGS
  // ============================================================

  function bindModuleTabs() {
    var taskBtn = $("#toggle-task");
    var ticketBtn = $("#toggle-ticket");

    if (taskBtn) {
      taskBtn.addEventListener("click", function () {
        selectModule("task");
      });
    }

    if (ticketBtn) {
      ticketBtn.addEventListener("click", function () {
        selectModule("ticket");
      });
    }
  }

function selectModule(moduleName) {
  $("#toggle-task").classList.toggle("sel", moduleName === "task");
  $("#toggle-ticket").classList.toggle("sel", moduleName === "ticket");

  $("#module-task").classList.toggle("on", moduleName === "task");
  $("#module-ticket").classList.toggle("on", moduleName === "ticket");

  var activeSub = $("#module-" + moduleName + " .snav.on");
  var idx = 0;

  if (activeSub) {
    idx = Number(activeSub.dataset.taskSub || activeSub.dataset.ticketSub || 0);
  }

  updateActiveTabNote(moduleName, idx);
}


  function bindSubTabs() {
    $all("[data-task-sub]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        showSub("task", Number(tab.dataset.taskSub || 0), tab);
      });
    });

    $all("[data-ticket-sub]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        showSub("ticket", Number(tab.dataset.ticketSub || 0), tab);
      });
    });
  }

function showSub(type, idx, activeTab) {
  if (
    idx === 1 &&
    (type === "task" || type === "ticket") &&
    !canCurrentUserViewAllReports()
  ) {
    showModal(
      "⚠️",
      "Access Restricted",
      "You do not have permission to view all reports."
    );
    return;
  }

  $all("#module-" + type + " .snav").forEach(function (x) {
    x.classList.remove("on");
  });

  activeTab.classList.add("on");

  $all("#module-" + type + " .subpage").forEach(function (page, i) {
    page.classList.toggle("on", i === idx);
  });

  updateActiveTabNote(type, idx);

  if (type === "task" && idx === 1) renderTaskReport();
  if (type === "task" && idx === 2) renderMyTasks();

  if (type === "ticket" && idx === 1) renderTicketReport();
  if (type === "ticket" && idx === 2) renderMyTickets();
}

  function bindPriorityButtons() {
    $all("#task-priority-grp .priority-chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        $all("#task-priority-grp .priority-chip").forEach(function (x) {
          x.classList.remove("sel");
        });
        chip.classList.add("sel");
        selectedTaskPriority = chip.dataset.p || "";
      });
    });

    $all("#ticket-priority-grp .priority-chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        $all("#ticket-priority-grp .priority-chip").forEach(function (x) {
          x.classList.remove("sel");
        });
        chip.classList.add("sel");
        selectedTicketPriority = chip.dataset.p || "";
      });
    });
  }
  
function getWordArray(text) {
  text = String(text || "").trim();
  return text ? text.split(/\s+/) : [];
}

function firstNWords(text, count) {
  return getWordArray(text).slice(0, count).join(" ");
}

function getTextWithoutSelection(input) {
  var value = String(input.value || "");
  var start = input.selectionStart || 0;
  var end = input.selectionEnd || 0;

  return value.slice(0, start) + value.slice(end);
}

function getTextAfterInsert(input, insertText) {
  var value = String(input.value || "");
  var start = input.selectionStart || 0;
  var end = input.selectionEnd || 0;

  return value.slice(0, start) + String(insertText || "") + value.slice(end);
}

function insertTextAtCursor(input, text) {
  var start = input.selectionStart || 0;
  var end = input.selectionEnd || 0;

  input.setRangeText(text, start, end, "end");

  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function updateWordCount(input, label, maxWords) {
  if (!input || !label) return;

  var count = wordCount(input.value || "");

  label.textContent = count + " / " + maxWords + " words";
  label.classList.toggle("over", count > maxWords);
}

function bindWordLimit(input, label, maxWords) {
  if (!input) return;

  input.addEventListener("beforeinput", function (e) {
    var inputType = e.inputType || "";

    if (
      inputType.indexOf("delete") === 0 ||
      inputType === "historyUndo" ||
      inputType === "historyRedo" ||
      inputType === "insertFromPaste"
    ) {
      return;
    }

    var insertText = e.data || "";

    if (inputType === "insertParagraph" || inputType === "insertLineBreak") {
      insertText = "\n";
    }

    if (!insertText) return;

    var nextText = getTextAfterInsert(input, insertText);

    if (wordCount(nextText) > maxWords) {
      e.preventDefault();
      updateWordCount(input, label, maxWords);
    }
  });

  input.addEventListener("paste", function (e) {
    e.preventDefault();

    var clipboard = e.clipboardData || window.clipboardData;
    var pasteText = clipboard ? clipboard.getData("text") : "";

    if (!pasteText) return;

    var currentWithoutSelection = getTextWithoutSelection(input);
    var availableWords = maxWords - wordCount(currentWithoutSelection);

    if (availableWords <= 0) {
      updateWordCount(input, label, maxWords);
      return;
    }

    var allowedPasteText = firstNWords(pasteText, availableWords);

    if (allowedPasteText) {
      insertTextAtCursor(input, allowedPasteText);
    }

    updateWordCount(input, label, maxWords);
  });

  input.addEventListener("input", function () {
    updateWordCount(input, label, maxWords);
  });

  updateWordCount(input, label, maxWords);
}

function bindWordCounts() {
  bindWordLimit($("#task-details"), $("#task-wordcount"), 100);
  bindWordLimit($("#ticket-other-text"), $("#ticket-other-wordcount"), 100);
}


  function bindTicketCategoryEvents() {
    var category = $("#ticket-category");
    var issue = $("#ticket-issue");

    if (category) {
      category.addEventListener("change", function () {
        var cat = category.value || "";
        var issues = TICKET_CATEGORY_MAP[cat] || [];

        if (issue) {
          issue.innerHTML =
            '<option value="">Select Issue</option>' +
            issues.map(function (x) {
              return '<option value="' + esc(x) + '">' + esc(x) + "</option>";
            }).join("");
        }

        var otherBlock = $("#ticket-other-block");
        var empBlock = $("#ticket-employee-involved-block");

        if (otherBlock) otherBlock.style.display = "none";
        if (empBlock) empBlock.style.display = "none";

        applyTicketCategorySuggestion(cat);
      });
    }

    if (issue) {
      issue.addEventListener("change", function () {
        var val = issue.value || "";

        var otherBlock = $("#ticket-other-block");
        var empBlock = $("#ticket-employee-involved-block");

        if (otherBlock) otherBlock.style.display = val === "Other" ? "block" : "none";

        if (empBlock) {
          empBlock.style.display =
            EMPLOYEE_INVOLVED_ISSUES.indexOf(val) !== -1 ? "block" : "none";
        }
      });
    }
  }

  function bindPickers() {
    bindPickerInput("task-assignto-search", "task-assignto-results", "taskAssignTo", false, true);
    bindPickerInput("task-updateto-search", "task-updateto-results", "taskUpdateTo", true, false);
    bindPickerInput("ticket-tagto-search", "ticket-tagto-results", "ticketTagTo", false, false);
    bindPickerInput("ticket-ccto-search", "ticket-ccto-results", "ticketCcTo", true, false);

    document.addEventListener("click", function (e) {
      if (!e.target.closest(".picker-wrap")) {
        $all(".picker-results").forEach(function (box) {
          box.classList.remove("show");
        });
      }
    });
  }

  function bindPickerInput(inputId, resultId, key, multi, excludeSelf) {
    var input = $("#" + inputId);
    var resultBox = $("#" + resultId);

    if (!input || !resultBox) return;

    input.addEventListener("input", function () {
      renderPickerResults(input, resultBox, key, multi, excludeSelf);
    });
  }

function bindAttachments() {
  var taskZone = $("#task-attach-zone");
  var taskInput = $("#task-file-input");

  if (taskZone && taskInput) {
    taskInput.setAttribute("accept", ALLOWED_ATTACHMENT_ACCEPT);

    taskZone.addEventListener("click", function () {
      taskInput.click();
    });

    taskInput.addEventListener("change", function () {
      addSelectedFiles("task", taskInput.files || []);
      taskInput.value = "";
    });
  }

  var ticketZone = $("#ticket-attach-zone");
  var ticketInput = $("#ticket-file-input");

  if (ticketZone && ticketInput) {
    ticketInput.setAttribute("accept", ALLOWED_ATTACHMENT_ACCEPT);

    ticketZone.addEventListener("click", function () {
      ticketInput.click();
    });

    ticketInput.addEventListener("change", function () {
      addSelectedFiles("ticket", ticketInput.files || []);
      ticketInput.value = "";
    });
  }
}

  function bindButtons() {
    var taskSubmit = $("#task-submit-btn");
    if (taskSubmit) {
      taskSubmit.addEventListener("click", submitTask);
    }

    var ticketSubmit = $("#ticket-submit-btn");
    if (ticketSubmit) {
      ticketSubmit.addEventListener("click", submitTicket);
    }

    var taskApply = $("#task-report-apply");
    if (taskApply) {
      taskApply.addEventListener("click", function () {
          resetTablePage("taskReport");
          renderTaskReport();
        });
    }

    ["tr-category", "tr-priority", "tr-status"].forEach(function (id) {
      var el = $("#" + id);
      if (el) {
          el.addEventListener("change", function () {
            resetTablePage("taskReport");
            renderTaskReport();
          });
        }
    });

    var ticketApply = $("#ticket-report-apply");
    if (ticketApply) {
      ticketApply.addEventListener("click", function () {
          resetTablePage("ticketReport");
          renderTicketReport();
        });
    }

    ["ticr-category", "ticr-priority", "ticr-status"].forEach(function (id) {
      var el = $("#" + id);
      if (el) {
          el.addEventListener("change", function () {
            resetTablePage("ticketReport");
            renderTicketReport();
          });
        }
    });
  }

  function bindModal() {
    var okBtn = $("#modal-ok-btn");
    if (okBtn) okBtn.addEventListener("click", closeModal);

    var modal = $("#modal");
    if (modal) {
      modal.addEventListener("click", function (e) {
        if (e.target === modal) closeModal();
      });
    }
  }
  
  function bindTaskDateRules() {
  var startEl = $("#task-startdate");
  var deadlineEl = $("#task-deadline");

  if (startEl) {
    startEl.addEventListener("change", updateTaskDateRules);
    startEl.addEventListener("input", updateTaskDateRules);
  }

  if (deadlineEl) {
    deadlineEl.addEventListener("change", updateTaskDateRules);
    deadlineEl.addEventListener("input", updateTaskDateRules);
  }

  updateTaskDateRules();
}

  // ============================================================
  // DROPDOWNS / USER LOAD
  // ============================================================

function populateStaticDropdowns() {
  fillSelect("#task-category", TASK_CATEGORIES, "Select");
  fillSelect("#tr-category", TASK_CATEGORIES, "All");
  fillSelect("#tr-status", TASK_STATUS_FILTERS, "All");

  fillSelect("#ticket-branch", BRANCHES, "");
  fillSelect("#ticket-category", Object.keys(TICKET_CATEGORY_MAP), "Select Category");
  fillSelect("#ticr-category", Object.keys(TICKET_CATEGORY_MAP), "All");
  fillSelect("#ticr-status", TICKET_STATUS_FILTERS, "All");
}


  function fillSelect(selector, rows, firstLabel) {
    var el = $(selector);
    if (!el) return;

    var html = "";

    if (firstLabel !== "") {
      html += '<option value="">' + esc(firstLabel) + "</option>";
    }

    html += rows.map(function (x) {
      return '<option value="' + esc(x) + '">' + esc(x) + "</option>";
    }).join("");

    el.innerHTML = html;
  }
  
  function normalizeRoleName(value) {
    return String(value || "").trim();
  }

  function addCurrentUserRole(value) {
    var role = "";

    if (typeof value === "string") {
      role = normalizeRoleName(value);
    } else if (value && typeof value === "object") {
      role = normalizeRoleName(
        value.role ||
        value.name ||
        value.role_name ||
        ""
      );
    }

    if (!role) return;

    if (currentUserRoles.indexOf(role) === -1) {
      currentUserRoles.push(role);
    }
  }

  function collectRolesFromClientGlobals() {
    currentUserRoles = [];

    var sources = [];

    if (
      typeof frappe !== "undefined" &&
      frappe &&
      Array.isArray(frappe.user_roles)
    ) {
      sources = sources.concat(frappe.user_roles);
    }

    if (
      typeof frappe !== "undefined" &&
      frappe &&
      frappe.boot &&
      frappe.boot.user &&
      Array.isArray(frappe.boot.user.roles)
    ) {
      sources = sources.concat(frappe.boot.user.roles);
    }

    sources.forEach(addCurrentUserRole);
  }

  function collectRolesFromUserDoc(userDoc) {
    var roles = userDoc && Array.isArray(userDoc.roles)
      ? userDoc.roles
      : [];

    roles.forEach(addCurrentUserRole);
  }

  function userHasRole(roleName) {
    roleName = normalizeRoleName(roleName);

    if (!roleName) return false;

    if (currentUserRoles.indexOf(roleName) !== -1) {
      return true;
    }

    try {
      if (
        frappe.user &&
        typeof frappe.user.has_role === "function" &&
        frappe.user.has_role(roleName)
      ) {
        return true;
      }
    } catch (e) {
      // Continue with collected role list.
    }

    return false;
  }

  function isSpecialReportEmail(user) {
    user = String(user || "").trim().toLowerCase();

    return MANAGER_EMAILS.some(function (email) {
      return String(email || "").trim().toLowerCase() === user;
    });
  }

  function refreshCurrentUserReportPermission() {
    isManager =
      isSpecialReportEmail(currentUser) ||
      userHasRole("System Manager");

    canViewAllReports =
      isManager ||
      userHasRole("Sales Manager");

    applyReportTabVisibility();

    void 0;
  }

  function canCurrentUserViewAllReports() {
    return !!canViewAllReports;
  }

  function applyReportTabVisibility() {
    var allowed = canCurrentUserViewAllReports();

    var taskReportTab = root.querySelector('[data-task-sub="1"]');
    var ticketReportTab = root.querySelector('[data-ticket-sub="1"]');

    if (taskReportTab) {
      taskReportTab.style.display = allowed ? "" : "none";
    }

    if (ticketReportTab) {
      ticketReportTab.style.display = allowed ? "" : "none";
    }

    /* If hidden report tab was active, move user back to safe tab */
    if (!allowed) {
      var activeTaskReport =
        taskReportTab &&
        taskReportTab.classList.contains("on");

      var activeTicketReport =
        ticketReportTab &&
        ticketReportTab.classList.contains("on");

      if (activeTaskReport) {
        var taskDefaultTab =
          root.querySelector('[data-task-sub="0"]');

        if (taskDefaultTab) {
          showSub("task", 0, taskDefaultTab);
        }
      }

      if (activeTicketReport) {
        var ticketDefaultTab =
          root.querySelector('[data-ticket-sub="0"]');

        if (ticketDefaultTab) {
          showSub("ticket", 0, ticketDefaultTab);
        }
      }
    }
  }


  function loadCurrentUser(done) {
    currentUser = page.session.user;
    currentUserFullName = page.session.full_name || currentUser;
    collectRolesFromClientGlobals();
    refreshCurrentUserReportPermission();
    setText('logged-in-user-name', currentUserFullName);
    setText('logged-in-user-role', currentUser);
    setValue('task-assignedby', currentUserFullName);
    setValue('ticket-raisedby', currentUserFullName);
    if (done) done();
  }

  function isTaskVisibleToCurrentUser(t) {
    if (canCurrentUserViewAllReports()) {
      return true;
    }

    t = t || {};

    return (
      isCurrentUserValue(t.allocated_to) ||
      isCurrentUserValue(t.assigned_by) ||
      isCurrentUserValue(t.owner)
    );
  }

  function isTicketVisibleToCurrentUser(t) {
    if (canCurrentUserViewAllReports()) {
      return true;
    }

    t = t || {};

    var meta = getTicketMeta(t);

    return (
      isCurrentUserValue(t.owner) ||
      isCurrentUserValue(t.raised_by) ||
      isCurrentUserValue(meta.tag_to) ||
      (meta.cc_to || []).some(isCurrentUserValue)
    );
  }

function loadUsers(done) {
  var allUsers = [];
  var pageLength = 500;

  function fetchPage(start) {
    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "User",
        fields: ["name", "full_name", "enabled"],
        filters: {
          enabled: 1
        },
        order_by: "full_name asc",
        limit_start: start,
        limit_page_length: pageLength
      },
      callback: function (r) {
        var rows = r.message || [];

        allUsers = allUsers.concat(rows);

        if (rows.length === pageLength) {
          fetchPage(start + pageLength);
          return;
        }

        users = allUsers.filter(function (u) {
          return u.name !== "Administrator" && u.full_name;
        });

        fillSelect(
          "#ticket-employee-involved",
          users.map(function (u) { return u.full_name; }),
          "Select Employee"
        );

          if (done) done();
        
      },
      error: function () {
        users = allUsers.filter(function (u) {
          return u.name !== "Administrator" && u.full_name;
        });

        
          if (done) done();
        
      }
    });
  }

  fetchPage(0);
}

  // ============================================================
  // PICKER
  // ============================================================

  function getPickerSelected(key) {
    if (key === "taskAssignTo") return taskAssignTo;
    if (key === "taskUpdateTo") return taskUpdateTo;
    if (key === "ticketTagTo") return ticketTagTo;
    if (key === "ticketCcTo") return ticketCcTo;
    return [];
  }

  function setPickerSelected(key, value) {
    if (key === "taskAssignTo") taskAssignTo = value;
    if (key === "taskUpdateTo") taskUpdateTo = value;
    if (key === "ticketTagTo") ticketTagTo = value;
    if (key === "ticketCcTo") ticketCcTo = value;
  }

  function getPickerChipId(key) {
    return {
      taskAssignTo: "task-assignto-chip",
      taskUpdateTo: "task-updateto-chip",
      ticketTagTo: "ticket-tagto-chip",
      ticketCcTo: "ticket-ccto-chip"
    }[key];
  }

  function renderPickerResults(input, resultBox, key, multi, excludeSelf) {
    var q = String(input.value || "").trim().toLowerCase();

    if (!q) {
      resultBox.innerHTML = "";
      resultBox.classList.remove("show");
      return;
    }

    var selected = getPickerSelected(key);

    var matches = users.filter(function (u) {
      var txt = (u.full_name + " " + u.name).toLowerCase();
      if (excludeSelf && u.name === currentUser) return false;
      if (selected.indexOf(u.name) !== -1) return false;
      return txt.indexOf(q) !== -1;
    }).slice(0, 10);

    if (!matches.length) {
      resultBox.innerHTML =
        '<div class="picker-item" style="cursor:default;color:#8C8C8C">No matching employee found.</div>';
      resultBox.classList.add("show");
      return;
    }

    resultBox.innerHTML = matches.map(function (u) {
      return '' +
        '<div class="picker-item" data-email="' + esc(u.name) + '">' +
          '<div class="picker-avatar">' + esc(initials(u.full_name || u.name)) + '</div>' +
          '<div>' +
            '<div class="picker-name">' + esc(u.full_name || u.name) + '</div>' +
            '<div class="picker-role">' + esc(u.name) + '</div>' +
          '</div>' +
        '</div>';
    }).join("");

    resultBox.classList.add("show");

    resultBox.querySelectorAll(".picker-item[data-email]").forEach(function (item) {
      item.addEventListener("click", function () {
        var email = item.dataset.email || "";
        var selectedNow = getPickerSelected(key).slice();

        if (multi) {
          if (selectedNow.indexOf(email) === -1) selectedNow.push(email);
        } else {
          selectedNow = [email];
        }

        setPickerSelected(key, selectedNow);

        input.value = "";
        resultBox.innerHTML = "";
        resultBox.classList.remove("show");

        renderPickerChips(key);
      });
    });
  }

  function renderPickerChips(key) {
    var row = $("#" + getPickerChipId(key));
    if (!row) return;

    var selected = getPickerSelected(key);

    var html = selected.map(function (email) {
      return '' +
        '<div class="selected-chip">' +
          esc(userLabel(email)) +
          '<span class="x" data-key="' + esc(key) + '" data-email="' + esc(email) + '">×</span>' +
        '</div>';
    }).join("");

    if (key === "taskUpdateTo") {
      html += '<div class="selected-chip locked">' + esc(currentUserFullName || currentUser) + ' (you — always included)</div>';
    }

    row.innerHTML = html;

    row.querySelectorAll(".selected-chip .x").forEach(function (x) {
      x.addEventListener("click", function () {
        var email = x.dataset.email || "";
        var arr = getPickerSelected(key).filter(function (v) {
          return v !== email;
        });

        setPickerSelected(key, arr);
        renderPickerChips(key);
      });
    });
  }

  function applyTicketCategorySuggestion(category) {
    var searchText = CATEGORY_TAG_TO_SUGGEST[category];

    if (!searchText || !users.length) return;

    var match = users.find(function (u) {
      return (
        String(u.full_name || "").toLowerCase().indexOf(searchText.toLowerCase()) !== -1 ||
        String(u.name || "").toLowerCase().indexOf(searchText.toLowerCase()) !== -1
      );
    });

    if (match) {
      ticketTagTo = [match.name];
      renderPickerChips("ticketTagTo");
    }
  }

  // ============================================================
// ATTACHMENTS - VALIDATION + UPLOAD
// Documents, images, and HTML files - max 5 MB
// ============================================================

// var MAX_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

// var ALLOWED_ATTACHMENT_EXTENSIONS = [
//   // Images
//   "jpg", "jpeg", "png", "gif", "webp", "bmp", "heic", "heif",
  
//   // Documents
//   "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
//   "txt", "csv", "rtf", "odt", "ods", "odp",
  
//   // Web files - HTML SUPPORT ADDED
//   "html", "htm", "xhtml"
// ];

// var ALLOWED_ATTACHMENT_ACCEPT =
//   ".jpg,.jpeg,.png,.gif,.webp,.bmp,.heic,.heif," +
//   ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.rtf,.odt,.ods,.odp," +
//   ".html,.htm,.xhtml," + // HTML files added
//   "image/*,application/pdf,text/html"; // Added text/html MIME type

// function getFileExtension(fileName) {
//   fileName = String(fileName || "").toLowerCase().trim();

//   if (fileName.indexOf(".") === -1) return "";

//   return fileName.split(".").pop();
// }

// function isAllowedAttachmentType(file) {
//   var fileName = file && file.name ? file.name : "";
//   var mimeType = file && file.type ? String(file.type).toLowerCase() : "";
//   var ext = getFileExtension(fileName);

//   // Allow HTML files by MIME type
//   if (mimeType === "text/html" || mimeType === "application/xhtml+xml") {
//     return true;
//   }

//   // Allow all normal browser-recognized image files
//   if (mimeType.indexOf("image/") === 0) {
//     return ALLOWED_ATTACHMENT_EXTENSIONS.indexOf(ext) !== -1;
//   }

//   // Allow by extension also, because some systems/browsers do not send MIME type
//   return ALLOWED_ATTACHMENT_EXTENSIONS.indexOf(ext) !== -1;
// }

// function getFileIcon(file) {
//   var mimeType = String(file.type || "").toLowerCase();
//   var ext = getFileExtension(file.name || "");
  
//   if (mimeType.indexOf("image/") === 0) return "🖼️";
//   if (mimeType === "text/html" || ext === "html" || ext === "htm" || ext === "xhtml") {
//     return "🌐";
//   }
//   return "📄";
// }

// function validateAttachmentFile(file) {
//   if (!file) {
//     return {
//       ok: false,
//       message: "Invalid file."
//     };
//   }

//   if (!isAllowedAttachmentType(file)) {
//     return {
//       ok: false,
//       message: "Only documents, images, and HTML files are allowed."
//     };
//   }

//   if (Number(file.size || 0) > MAX_ATTACHMENT_SIZE_BYTES) {
//     return {
//       ok: false,
//       message: "File size must be 5 MB or below."
//     };
//   }

//   return {
//     ok: true,
//     message: ""
//   };
// }

// ============================================================
// ATTACHMENTS - VALIDATION + UPLOAD
// Documents, images, and HTML files - max 5 MB
// ============================================================

// var MAX_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

// var ALLOWED_ATTACHMENT_EXTENSIONS = [
//   // Images
//   "jpg", "jpeg", "png", "gif", "webp", "bmp", "heic", "heif",
  
//   // Documents
//   "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
//   "txt", "csv", "rtf", "odt", "ods", "odp",
  
//   // Web files - HTML SUPPORT ADDED
//   "html", "htm", "xhtml"
// ];

// var ALLOWED_ATTACHMENT_ACCEPT =
//   ".jpg,.jpeg,.png,.gif,.webp,.bmp,.heic,.heif," +
//   ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.rtf,.odt,.ods,.odp," +
//   ".html,.htm,.xhtml," + // HTML files added
//   "image/*,application/pdf,text/html"; // Added text/html MIME type

// function getFileExtension(fileName) {
//   fileName = String(fileName || "").toLowerCase().trim();

//   if (fileName.indexOf(".") === -1) return "";

//   return fileName.split(".").pop();
// }

// function isAllowedAttachmentType(file) {
//   var fileName = file && file.name ? file.name : "";
//   var mimeType = file && file.type ? String(file.type).toLowerCase() : "";
//   var ext = getFileExtension(fileName);

//   // CRITICAL FIX: Allow HTML files by MIME type FIRST
//   if (mimeType === "text/html" || 
//       mimeType === "application/xhtml+xml" ||
//       ext === "html" || 
//       ext === "htm" || 
//       ext === "xhtml") {
//     return true;
//   }

//   // Allow all normal browser-recognized image files
//   if (mimeType.indexOf("image/") === 0) {
//     return ALLOWED_ATTACHMENT_EXTENSIONS.indexOf(ext) !== -1;
//   }

//   // Allow by extension also, because some systems/browsers do not send MIME type
//   return ALLOWED_ATTACHMENT_EXTENSIONS.indexOf(ext) !== -1;
// }

// function getFileIcon(file) {
//   var mimeType = String(file.type || "").toLowerCase();
//   var ext = getFileExtension(file.name || "");
  
//   if (mimeType.indexOf("image/") === 0) return "🖼️";
//   if (mimeType === "text/html" || 
//       ext === "html" || 
//       ext === "htm" || 
//       ext === "xhtml") {
//     return "🌐";
//   }
//   return "📄";
// }

// function validateAttachmentFile(file) {
//   if (!file) {
//     return {
//       ok: false,
//       message: "Invalid file."
//     };
//   }

//   if (!isAllowedAttachmentType(file)) {
//     return {
//       ok: false,
//       message: "Only documents, images, and HTML files are allowed."
//     };
//   }

//   if (Number(file.size || 0) > MAX_ATTACHMENT_SIZE_BYTES) {
//     return {
//       ok: false,
//       message: "File size must be 5 MB or below."
//     };
//   }

//   return {
//     ok: true,
//     message: ""
//   };
// }

// function validateAttachmentList(files) {
//   files = files || [];

//   var errors = [];

//   Array.prototype.slice.call(files).forEach(function (file) {
//     var validation = validateAttachmentFile(file);

//     if (!validation.ok) {
//       errors.push((file.name || "File") + " - " + validation.message);
//     }
//   });

//   if (errors.length) {
//     return {
//       ok: false,
//       message: errors.join("\n")
//     };
//   }

//   return {
//     ok: true,
//     message: ""
//   };
// }

// function addSelectedFiles(type, files) {
//   var arr = type === "task" ? taskFiles : ticketFiles;
//   var rejected = [];

//   Array.prototype.slice.call(files || []).forEach(function (file) {
//     var validation = validateAttachmentFile(file);

//     if (!validation.ok) {
//       rejected.push("• " + (file.name || "File") + " - " + validation.message);
//       return;
//     }

//     // Prevent same file from being added again
//     var alreadyAdded = arr.some(function (existingFile) {
//       return (
//         existingFile.name === file.name &&
//         existingFile.size === file.size &&
//         existingFile.lastModified === file.lastModified
//       );
//     });

//     if (!alreadyAdded) {
//       arr.push(file);
//     }
//   });

//   if (type === "task") taskFiles = arr;
//   if (type === "ticket") ticketFiles = arr;

//   renderSelectedFiles(type);

//   if (rejected.length) {
//     showModal(
//       "⚠️",
//       "Invalid Attachment",
//       "Only documents, images, and HTML files up to 5 MB are allowed.\n\n" + rejected.join("\n")
//     );
//   }
// }

// function renderSelectedFiles(type) {
//   var list = $("#" + type + "-attach-list");
//   var arr = type === "task" ? taskFiles : ticketFiles;

//   if (!list) return;

//   if (!arr.length) {
//     list.innerHTML = "";
//     return;
//   }

//   list.innerHTML = arr.map(function (file, idx) {
//     var icon = getFileIcon(file);

//     return '' +
//       '<div class="attach-item">' +
//         '<span class="an">' + icon + ' ' + esc(file.name || "File") + '</span>' +
//         '<span class="asize">' + esc(formatFileSize(file.size || 0)) + '</span>' +
//         '<span class="x" data-type="' + esc(type) + '" data-idx="' + idx + '">×</span>' +
//       '</div>';
//   }).join("");

//   list.querySelectorAll(".attach-item .x").forEach(function (x) {
//     x.addEventListener("click", function () {
//       var idx = Number(x.dataset.idx || 0);

//       if (type === "task") taskFiles.splice(idx, 1);
//       if (type === "ticket") ticketFiles.splice(idx, 1);

//       renderSelectedFiles(type);
//     });
//   });
// }

// function uploadFiles(doctype, docname, files) {
//   files = files || [];

//   if (!files.length) return Promise.resolve([]);

//   var validation = validateAttachmentList(files);

//   if (!validation.ok) {
//     return Promise.reject(validation.message);
//   }

//   return Promise.all(files.map(function (file) {
//     return uploadOneFile(doctype, docname, file);
//   }));
// }

// function uploadOneFile(doctype, docname, file) {
//   return new Promise(function (resolve, reject) {
//     var validation = validateAttachmentFile(file);

//     if (!validation.ok) {
//       reject((file.name || "File") + " - " + validation.message);
//       return;
//     }

//     var formData = new FormData();

//     formData.append("file", file, file.name);
//     formData.append("is_private", "1");
//     formData.append("folder", "Home/Attachments");
//     formData.append("doctype", doctype);
//     formData.append("docname", docname);

//     page.upload(formData).then(resolve, reject);
//   });
// }



// ============================================================
// ATTACHMENTS - VALIDATION + UPLOAD
// Documents, images, and HTML files - max 5 MB
// ============================================================

var MAX_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
var MAX_ATTACHMENT_COUNT = 5; // Maximum 5 files

var ALLOWED_ATTACHMENT_EXTENSIONS = [
  // Images
  "jpg", "jpeg", "png", "gif", "webp", "bmp", "heic", "heif",
  
  // Documents
  "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
  "txt", "csv", "rtf", "odt", "ods", "odp",
  
  // Web files - HTML SUPPORT ADDED
  "html", "htm", "xhtml"
];

// UPDATED: Include all HTML-related MIME types and extensions
var ALLOWED_ATTACHMENT_MIME_TYPES = [
  "text/html",
  "application/xhtml+xml",
  "application/xml",
  "text/xml"
];

var ALLOWED_ATTACHMENT_ACCEPT =
  ".jpg,.jpeg,.png,.gif,.webp,.bmp,.heic,.heif," +
  ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.rtf,.odt,.ods,.odp," +
  ".html,.htm,.xhtml," +
  "image/*,application/pdf,text/html,application/xhtml+xml";

function getFileExtension(fileName) {
  fileName = String(fileName || "").toLowerCase().trim();

  if (fileName.indexOf(".") === -1) return "";

  var parts = fileName.split(".");
  return parts[parts.length - 1];
}

function isAllowedAttachmentType(file) {
  var fileName = file && file.name ? file.name : "";
  var mimeType = file && file.type ? String(file.type).toLowerCase() : "";
  var ext = getFileExtension(fileName);

  // DEBUG: Log what we're checking
  void 0;
  void 0;
  void 0;

  // ============================================================
  // CRITICAL FIX: Explicitly allow HTML files
  // Check BOTH extension and MIME type
  // ============================================================
  
  // 1. Check if it's an HTML file by extension
  if (ext === "html" || ext === "htm" || ext === "xhtml") {
    void 0;
    return true;
  }

  // 2. Check if it's an HTML file by MIME type
  if (mimeType === "text/html" || 
      mimeType === "application/xhtml+xml" ||
      mimeType === "application/xml" ||
      mimeType === "text/xml") {
    void 0;
    return true;
  }

  // Allow all normal browser-recognized image files
  if (mimeType.indexOf("image/") === 0) {
    var isAllowed = ALLOWED_ATTACHMENT_EXTENSIONS.indexOf(ext) !== -1;
    void 0;
    return isAllowed;
  }

  // Allow by extension for other document types
  var isAllowedByExt = ALLOWED_ATTACHMENT_EXTENSIONS.indexOf(ext) !== -1;
  void 0;
  return isAllowedByExt;
}

function getFileIcon(file) {
  var mimeType = String(file.type || "").toLowerCase();
  var ext = getFileExtension(file.name || "");
  
  if (mimeType.indexOf("image/") === 0) return "🖼️";
  if (ext === "html" || ext === "htm" || ext === "xhtml") {
    return "🌐";
  }
  if (mimeType === "text/html" || mimeType === "application/xhtml+xml") {
    return "🌐";
  }
  return "📄";
}

function validateAttachmentFile(file) {
  if (!file) {
    return {
      ok: false,
      message: "Invalid file."
    };
  }

  // Get file info for debugging
  var fileName = file.name || "Unknown";
  var ext = getFileExtension(fileName);
  var mimeType = file.type || "";

  void 0;

  // Explicit HTML check FIRST
  if (ext === "html" || ext === "htm" || ext === "xhtml") {
    void 0;
    // Size check still applies
    if (Number(file.size || 0) > MAX_ATTACHMENT_SIZE_BYTES) {
      return {
        ok: false,
        message: "HTML file size must be 5 MB or below."
      };
    }
    return {
      ok: true,
      message: ""
    };
  }

  if (mimeType === "text/html" || mimeType === "application/xhtml+xml") {
    void 0;
    if (Number(file.size || 0) > MAX_ATTACHMENT_SIZE_BYTES) {
      return {
        ok: false,
        message: "HTML file size must be 5 MB or below."
      };
    }
    return {
      ok: true,
      message: ""
    };
  }

  // Normal validation for other file types
  if (!isAllowedAttachmentType(file)) {
    return {
      ok: false,
      message: "Only documents, images, and HTML files are allowed."
    };
  }

  if (Number(file.size || 0) > MAX_ATTACHMENT_SIZE_BYTES) {
    return {
      ok: false,
      message: "File size must be 5 MB or below."
    };
  }

  return {
    ok: true,
    message: ""
  };
}

function validateAttachmentList(files) {
  files = Array.prototype.slice.call(files || []);

  var errors = [];

  if (files.length > MAX_ATTACHMENT_COUNT) {
    return {
      ok: false,
      message: "You can upload maximum " + MAX_ATTACHMENT_COUNT + " files only."
    };
  }

  files.forEach(function (file) {
    var validation = validateAttachmentFile(file);

    if (!validation.ok) {
      errors.push((file.name || "File") + " - " + validation.message);
    }
  });

  if (errors.length) {
    return {
      ok: false,
      message: errors.join("\n")
    };
  }

  return {
    ok: true,
    message: ""
  };
}

function addSelectedFiles(type, files) {
  var arr = type === "task" ? taskFiles : ticketFiles;
  var rejected = [];
  var validNewFiles = [];

  Array.prototype.slice.call(files || []).forEach(function (file) {
    var validation = validateAttachmentFile(file);

    if (!validation.ok) {
      rejected.push("• " + (file.name || "File") + " - " + validation.message);
      return;
    }

    var alreadyAdded = arr.some(function (existingFile) {
      return (
        existingFile.name === file.name &&
        existingFile.size === file.size &&
        existingFile.lastModified === file.lastModified
      );
    });

    var alreadyInNew = validNewFiles.some(function (existingFile) {
      return (
        existingFile.name === file.name &&
        existingFile.size === file.size &&
        existingFile.lastModified === file.lastModified
      );
    });

    if (!alreadyAdded && !alreadyInNew) {
      validNewFiles.push(file);
    }
  });

  if (arr.length + validNewFiles.length > MAX_ATTACHMENT_COUNT) {
    showModal(
      "⚠️",
      "Maximum Files Limit",
      "You can upload maximum " + MAX_ATTACHMENT_COUNT + " files only.\n\nCurrently selected: " +
        arr.length +
        "\nTrying to add: " +
        validNewFiles.length +
        "\n\nPlease remove some files and try again."
    );
    return;
  }

  validNewFiles.forEach(function (file) {
    arr.push(file);
  });

  if (type === "task") taskFiles = arr;
  if (type === "ticket") ticketFiles = arr;

  renderSelectedFiles(type);

  if (rejected.length) {
    showModal(
      "⚠️",
      "Invalid Attachment",
      "Only documents, images, and HTML files up to 5 MB are allowed.\n\n" + rejected.join("\n")
    );
  }
}


function renderSelectedFiles(type) {
  var list = $("#" + type + "-attach-list");
  var arr = type === "task" ? taskFiles : ticketFiles;

  if (!list) return;

  if (!arr.length) {
    list.innerHTML = "";
    return;
  }

  list.innerHTML = arr.map(function (file, idx) {
    var icon = getFileIcon(file);

    return '' +
      '<div class="attach-item">' +
        '<span class="an">' + icon + ' ' + esc(file.name || "File") + '</span>' +
        '<span class="asize">' + esc(formatFileSize(file.size || 0)) + '</span>' +
        '<span class="x" data-type="' + esc(type) + '" data-idx="' + idx + '">×</span>' +
      '</div>';
  }).join("");

  list.querySelectorAll(".attach-item .x").forEach(function (x) {
    x.addEventListener("click", function () {
      var idx = Number(x.dataset.idx || 0);

      if (type === "task") taskFiles.splice(idx, 1);
      if (type === "ticket") ticketFiles.splice(idx, 1);

      renderSelectedFiles(type);
    });
  });
}

function uploadFiles(doctype, docname, files) {
  files = files || [];

  if (!files.length) return Promise.resolve([]);

  var validation = validateAttachmentList(files);

  if (!validation.ok) {
    return Promise.reject(validation.message);
  }

  return Promise.all(files.map(function (file) {
    return uploadOneFile(doctype, docname, file);
  }));
}

function normalizeTaskUpdateFiles(uploadedRows, originalFiles) {
  uploadedRows = uploadedRows || [];
  originalFiles = originalFiles || [];

  return uploadedRows.map(function (f, idx) {
    var original = originalFiles[idx] || {};

    return {
      file_name: f.file_name || original.name || f.name || "Open File",
      file_url: f.file_url || "",
      file_id: f.name || "",
      size: original.size || f.file_size || 0,
      uploaded_on: getNowLocalDateTime()
    };
  });
}

function renderTaskUpdateFileRows(files) {
  files = files || [];

  if (!files.length) {
    return '<div class="life-update-no-files">No files added in this update.</div>';
  }

  return '' +
    '<div class="life-update-file-list">' +
      files.map(function (f) {
        var fileName = f.file_name || f.file_url || "Open File";
        var fileUrl = f.file_url || "";

        return '' +
          '<div class="life-update-file-row">' +
            '<div class="life-update-file-name">📎 ' + esc(fileName) + '</div>' +
            (
              fileUrl
                ? '<a href="' + esc(fileUrl) + '" target="_blank" class="life-update-file-open">Open</a>'
                : ''
            ) +
          '</div>';
      }).join("") +
    '</div>';
}

// function uploadOneFile(doctype, docname, file) {
//   return new Promise(function (resolve, reject) {
//     var validation = validateAttachmentFile(file);

//     if (!validation.ok) {
//       reject((file.name || "File") + " - " + validation.message);
//       return;
//     }

//     var formData = new FormData();

//     formData.append("file", file, file.name);
//     formData.append("is_private", "1");
//     formData.append("folder", "Home/Attachments");
//     formData.append("doctype", doctype);
//     formData.append("docname", docname);

//     var xhr = new XMLHttpRequest();
//     xhr.open("POST", "/api/method/upload_file", true);

//     var csrfToken =
//       (window.frappe && frappe.csrf_token) ||
//       window.csrf_token ||
//       "";

//     if (csrfToken) {
//       xhr.setRequestHeader("X-Frappe-CSRF-Token", csrfToken);
//     }

//     xhr.onreadystatechange = function () {
//       if (xhr.readyState !== 4) return;

//       var response = {};

//       try {
//         response = JSON.parse(xhr.responseText || "{}");
//       } catch (e) {
//         reject("Unable to read upload response.");
//         return;
//       }

//       if (xhr.status >= 200 && xhr.status < 300 && response.message) {
//         resolve(response.message);
//       } else {
//         reject(response.exception || response.message || "File upload failed.");
//       }
//     };

//     xhr.onerror = function () {
//       reject("Network error while uploading file.");
//     };

//     xhr.send(formData);
//   });
// }


function uploadOneFile(doctype, docname, file) {
  return new Promise(function (resolve, reject) {
    var validation = validateAttachmentFile(file);

    if (!validation.ok) {
      reject((file.name || "File") + " - " + validation.message);
      return;
    }

    var formData = new FormData();
    var fileName = file.name || "";
    var ext = getFileExtension(fileName);
    var mimeType = String(file.type || "").toLowerCase();

    // Determine if this is an HTML file
    var isHtmlFile = (
      ext === "html" || 
      ext === "htm" || 
      ext === "xhtml" ||
      mimeType === "text/html" ||
      mimeType === "application/xhtml+xml"
    );

    formData.append("file", file, file.name);
    
    // Use Home folder for all files
    formData.append("folder", "Home");
    
    // Make HTML files public, others private
    if (isHtmlFile) {
      formData.append("is_private", "0");
      void 0;
    } else {
      formData.append("is_private", "1");
      void 0;
    }
    
    formData.append("doctype", doctype);
    formData.append("docname", docname);

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/method/upload_file", true);

    var csrfToken =
      (window.frappe && frappe.csrf_token) ||
      window.csrf_token ||
      "";

    if (csrfToken) {
      xhr.setRequestHeader("X-Frappe-CSRF-Token", csrfToken);
    }

    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) return;

      var response = {};
      try {
        response = JSON.parse(xhr.responseText || "{}");
      } catch (e) {
        reject("Unable to read upload response.");
        return;
      }

      if (xhr.status >= 200 && xhr.status < 300 && response.message) {
        void 0;
        if (response.message.file_url) {
          void 0;
        }
        resolve(response.message);
      } else {
        reject(response.exception || response.message || "File upload failed.");
      }
    };

    xhr.onerror = function () {
      reject("Network error while uploading file.");
    };

    xhr.send(formData);
  });
}
  // ============================================================
  // TASKS
  // ============================================================

  function submitTask() {
    var assignTo = taskAssignTo[0] || "";
    var category = getValue("task-category");
    var startDate = getValue("task-startdate");
    var deadlineDateTime = getValue("task-deadline");
    var deadline = getDatePartFromDateTime(deadlineDateTime);
    var details = getValue("task-details");

    if (!assignTo) {
      showModal("⚠️", "Select Assignee", "Please search and select who this task is being assigned to.");
      return;
    }

    if (!category) {
      showModal("⚠️", "Category Required", "Please select a task category.");
      return;
    }

    var dateValidation = validateTaskDatesBeforeSubmit(startDate, deadlineDateTime);

    if (!dateValidation.ok) {
      showModal("⚠️", "Invalid Task Dates", dateValidation.message);
      return;
    }

    if (!details) {
      showModal("⚠️", "Details Required", "Please enter task details.");
      return;
    }

    if (wordCount(details) > 100) {
      showModal("⚠️", "Too Many Words", "Task details cannot exceed 100 words.");
      return;
    }

    if (!selectedTaskPriority) {
      showModal("⚠️", "Priority Required", "Please select task priority.");
      return;
    }

    var updateTo = taskUpdateTo.slice();

    if (updateTo.indexOf(currentUser) === -1) {
      updateTo.push(currentUser);
    }

    var meta = {
      category: category,
      start_date: startDate,
      deadline_datetime: deadlineDateTime,
      duration_label: calculateTaskDurationDays(startDate, deadlineDateTime),
      update_to: updateTo
    };

    var doc = {
      doctype: "ToDo",
      description: buildTaskDescription(details, meta),
      allocated_to: assignTo,
      assigned_by: currentUser,
      priority: selectedTaskPriority,
      status: "Open",
      date: deadline
    };
    
    var taskFileValidation = validateAttachmentList(taskFiles);

    if (!taskFileValidation.ok) {
      showModal(
        "⚠️",
        "Invalid Attachment",
        "Please remove invalid task attachment(s):\n\n" + taskFileValidation.message
      );
      return;
    }

    var btn = $("#task-submit-btn");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Assigning...";
    }

    frappe.call({
      method: "frappe.client.insert",
      args: {
        doc: doc
      },
      callback: function (r) {
        var saved = r.message || {};

        uploadFiles("ToDo", saved.name, taskFiles)
          .then(function () {
            showModal("✅", "Task Assigned", "Task " + saved.name + " assigned to " + userLabel(assignTo) + ".");
            resetTaskForm();
            loadTasks();

            if (btn) {
              btn.disabled = false;
              btn.textContent = "✓ Assign Task";
            }
          })
          .catch(function (err) {
            showModal("⚠️", "Task Saved, Attachment Failed", getErrorMessage(err));
            resetTaskForm();
            loadTasks();

            if (btn) {
              btn.disabled = false;
              btn.textContent = "✓ Assign Task";
            }
          });
      },
      error: function (err) {
        showModal("⚠️", "Task Save Failed", getErrorMessage(err));

        if (btn) {
          btn.disabled = false;
          btn.textContent = "✓ Assign Task";
        }
      }
    });
  }

  function resetTaskForm() {
    setValue("task-category", "");
    forceDefaultTaskStartDate();
    setValue("task-deadline", "");
    setText("task-duration-label", "");
    updateTaskDateRules();
    setValue("task-details", "");

    updateWordCount($("#task-details"), $("#task-wordcount"), 100);

    selectedTaskPriority = "";
    $all("#task-priority-grp .priority-chip").forEach(function (x) {
      x.classList.remove("sel");
    });

    taskAssignTo = [];
    taskUpdateTo = [];
    renderPickerChips("taskAssignTo");
    renderPickerChips("taskUpdateTo");

    taskFiles = [];
    renderSelectedFiles("task");
  }

function loadTasks() {
  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "ToDo",
      fields: [
        "name",
        "description",
        "allocated_to",
        "assigned_by",
        "priority",
        "status",
        "date",
        "creation",
        "modified",
        "owner"
      ],
      order_by: "modified desc",
      limit_page_length: 500
    },
    callback: function (r) {
      tasks = (r.message || []).filter(isTaskVisibleToCurrentUser);

      loadAttachmentCache(
        "ToDo",
        tasks.map(function (t) { return t.name; }),
        function () {
          renderTaskReport();
          renderMyTasks();
          renderCounts();
        }
      );
    },
    error: function () {
      tasks = [];
      renderTaskReport();
      renderMyTasks();
      renderCounts();
    }
  });
}


  function getTaskMeta(task) {
    return parseMeta(task.description, "TASK");
  }

function getTaskDetails(task) {
  return htmlToReadableText(removeMeta(task.description || ""));
}

function getTaskStatus(task) {
  var meta = getTaskMeta(task);

  if (task.status === "Cancelled") {
    return "Cancelled";
  }

  if (task.status === "Closed") {
    return "Closed";
  }

  if (meta.workflow_state === "Completed") {
    return "Completed";
  }

  var deadlineDateTime = meta.deadline_datetime || "";

  if (!deadlineDateTime && task.date) {
    deadlineDateTime = task.date + "T23:59";
  }

  deadlineDateTime = normalizeDateTimeValue(deadlineDateTime);

  var activeForOverdue =
    task.status === "Open" &&
    (
      !meta.workflow_state ||
      meta.workflow_state === "Open" ||
      meta.workflow_state === "Reopened"
    );

  if (
    activeForOverdue &&
    deadlineDateTime &&
    deadlineDateTime < getNowLocalDateTime()
  ) {
    return "Overdue";
  }

  if (meta.workflow_state === "Reopened") {
    return "Reopened";
  }

  return task.status || "Open";
}


function renderTaskReport() {
  var body = $("#task-report-body");
  if (!body) return;

  var catF = getValue("tr-category");
  var priF = getValue("tr-priority");
  var statF = getValue("tr-status");

  var filtered = tasks.filter(function (t) {
    var meta = getTaskMeta(t);
    var status = getTaskStatus(t);

    return (
      (!catF || meta.category === catF) &&
      (!priF || t.priority === priF) &&
      (!statF || status === statF) && taskMatchesAssigneeSearch(t)
    );
  });
  filtered = sortByModifiedLatest(filtered);

  renderTaskTiles();

  setText("task-report-count", String(filtered.length));
  var pageData = getPaginatedRows("taskReport", filtered);

  if (!filtered.length) {
    body.innerHTML =
      '<tr><td colspan="9" style="text-align:center;color:#8C8C8C;padding:18px">No tasks found.</td></tr>';
    return;
  }

  body.innerHTML = pageData.rows.map(function (t) {
    var meta = getTaskMeta(t);
    var status = getTaskStatus(t);
    var details = getTaskDetails(t);
    var updateTo = (meta.update_to || []).map(userDisplayName).join(", ") || "—";
    var workedDays = calculateWorkedDaysLabel(t, meta);

    var detailId = registerDetailHtml(
      "Task Details - " + t.name,
      buildTaskDetailsHtml(t, meta, details, updateTo),
      buildTaskExtraHistorySection(meta)
    );

    return '' +
      '<tr class="life-clickable-row" ' +
        'data-detail-html-id="' + esc(detailId) + '" ' +
        'data-doctype="ToDo" ' +
        'data-docname="' + esc(t.name) + '">' +

        // Assigned By + Start Date
        '<td>' +
          '<div class="life-user-date-cell">' +
            '<div class="life-user-name">' +
              esc(userDisplayName(t.assigned_by || t.owner)) +
            '</div>' +
            '<div class="life-user-date">Start: ' +
              esc(formatLifeDate(meta.start_date || t.creation)) +
            '</div>' +
          '</div>' +
        '</td>' +

        // Assigned To + Deadline
        '<td>' +
          '<div class="life-user-date-cell">' +
            '<div class="life-user-name">' +
              esc(userDisplayName(t.allocated_to)) +
            '</div>' +
            '<div class="life-user-date">Due: ' +
              esc(formatLifeDateTime(meta.deadline_datetime || t.date)) +
            '</div>' +
            '<div class="life-user-date">Worked: ' +
              esc(workedDays) +
            '</div>' +
          '</div>' +
        '</td>' +

        // Category
        '<td>' +
          '<div class="life-row-main-text">' +
            esc(meta.category || "—") +
          '</div>' +
        '</td>' +

        // Details preview, row click opens full details
        '<td style="max-width:280px;white-space:normal">' +
          '<div class="life-row-main-text">' +
            esc(shortPreviewText(details || "—", 110)) +
          '</div>' +
        '</td>' +

        // Priority
        '<td>' + priorityPill(t.priority) + '</td>' +

        // Update To
        '<td style="max-width:180px;white-space:normal">' +
          esc(updateTo) +
        '</td>' +

        // Attachments
        '<td>' + attachmentChip("ToDo", t.name) + '</td>' +

        // Status
        '<td>' + statusPill(status) + '</td>' +

        // Action
        '<td>' + renderTaskActionButtons(t) + '</td>' +

      '</tr>';
  }).join("");

  bindTaskActionButtons(body);
  bindAttachmentChips(body);
  bindClickableTaskRows(body);
  renderTablePagination(body, "taskReport", pageData, renderTaskReport);
}

function renderTaskTiles() {
  var box = $("#task-tiles");
  if (!box) return;

  var total = tasks.length;

  var inProgress = tasks.filter(function (t) {
    var status = getTaskStatus(t);
    return status === "Open" || status === "Reopened";
  }).length;

  var reviewPending = tasks.filter(function (t) {
    return getTaskStatus(t) === "Completed";
  }).length;

  var overdue = tasks.filter(function (t) {
    return getTaskStatus(t) === "Overdue";
  }).length;

  box.innerHTML = [
    { l: "Total Tasks", v: total, c: "t-pn" },
    { l: "In Progress", v: inProgress, c: "t-po" },
    { l: "Review Pending", v: reviewPending, c: "t-pgr" },
    { l: "Overdue", v: overdue, c: "t-pr" }
  ].map(function (x) {
    return '<div class="tile ' + x.c + '"><div class="tl">' + esc(x.l) + '</div><div class="tv">' + esc(x.v) + '</div></div>';
  }).join("");
}


function renderMyTasks() {
  var toBody = $("#mytask-to-body");
  var byBody = $("#mytask-by-body");

  if (!toBody || !byBody) return;

  var toMe = tasks.filter(function (t) {
    return isCurrentUserValue(t.allocated_to);
  });

  var byMe = tasks.filter(function (t) {
    return (
      t.owner === currentUser ||
      t.assigned_by === currentUser ||
      userDisplayName(t.owner) === currentUserFullName ||
      userDisplayName(t.assigned_by) === currentUserFullName
    );
  });

  setText("mytask-to-count", String(toMe.length));
  setText("mytask-by-count", String(byMe.length));
  
  toMe = sortByModifiedLatest(toMe);
    byMe = sortByModifiedLatest(byMe);
  var toPageData = getPaginatedRows("myTaskTo", toMe);
  var byPageData = getPaginatedRows("myTaskBy", byMe);

  // ============================================================
  // Assigned To Me
  // New columns:
  // From | Category | Deadline | Priority | Status | Action
  // Row click opens task details
  // ============================================================

  toBody.innerHTML = toMe.length
    ? toPageData.rows.map(function (t) {
        var meta = getTaskMeta(t);
        var status = getTaskStatus(t);
        var details = getTaskDetails(t);
        var updateTo = (meta.update_to || []).map(userDisplayName).join(", ") || "—";

        var detailId = registerDetailHtml(
          "Task Details - " + t.name,
          buildTaskDetailsHtml(t, meta, details, updateTo),
          buildTaskExtraHistorySection(meta)
        );

        return '' +
          '<tr class="life-clickable-row" ' +
            'data-detail-html-id="' + esc(detailId) + '" ' +
            'data-doctype="ToDo" ' +
            'data-docname="' + esc(t.name) + '">' +

            '<td>' +
              '<div class="life-user-date-cell">' +
                '<div class="life-user-name">' +
                  esc(userDisplayName(t.assigned_by || t.owner)) +
                '</div>' +
                '<div class="life-user-date">Start: ' +
                  esc(formatLifeDate(meta.start_date || t.creation)) +
                '</div>' +
              '</div>' +
            '</td>' +

            '<td>' +
              '<div class="life-row-main-text">' +
                esc(meta.category || "—") +
              '</div>' +
            '</td>' +

            '<td>' +
              esc(formatLifeDateTime(meta.deadline_datetime || t.date)) +
            '</td>' +

            '<td>' + priorityPill(t.priority) + '</td>' +

            '<td>' + statusPill(status) + '</td>' +

            '<td>' + renderTaskActionButtons(t) + '</td>' +

          '</tr>';
      }).join("")
    : '<tr><td colspan="6" style="text-align:center;color:#8C8C8C;padding:14px">No tasks assigned to you.</td></tr>';

  // ============================================================
  // Assigned By Me
  // New columns:
  // To | Category | Deadline | Priority | Status
  // Row click opens task details
  // ============================================================

  byBody.innerHTML = byMe.length
    ? byPageData.rows.map(function (t) {
        var meta = getTaskMeta(t);
        var status = getTaskStatus(t);
        var details = getTaskDetails(t);
        var updateTo = (meta.update_to || []).map(userDisplayName).join(", ") || "—";

        var detailId = registerDetailHtml(
          "Task Details - " + t.name,
          buildTaskDetailsHtml(t, meta, details, updateTo),
          buildTaskExtraHistorySection(meta)
        );

        return '' +
          '<tr class="life-clickable-row" ' +
            'data-detail-html-id="' + esc(detailId) + '" ' +
            'data-doctype="ToDo" ' +
            'data-docname="' + esc(t.name) + '">' +

            '<td>' +
              '<div class="life-user-date-cell">' +
                '<div class="life-user-name">' +
                  esc(userDisplayName(t.allocated_to)) +
                '</div>' +
                '<div class="life-user-date">Due: ' +
                  esc(formatLifeDateTime(meta.deadline_datetime || t.date)) +
                '</div>' +
              '</div>' +
            '</td>' +

            '<td>' +
              '<div class="life-row-main-text">' +
                esc(meta.category || "—") +
              '</div>' +
            '</td>' +

            '<td>' +
              esc(formatLifeDateTime(meta.deadline_datetime || t.date)) +
            '</td>' +

            '<td>' + priorityPill(t.priority) + '</td>' +

            '<td>' + statusPill(status) + '</td>' +

            '<td>' + renderTaskActionButtons(t) + '</td>' +
            
            '</tr>';
      }).join("")
    : '<tr><td colspan="6" style="text-align:center;color:#8C8C8C;padding:14px">You have not assigned any tasks.</td></tr>';

  bindTaskActionButtons(toBody);
  bindTaskActionButtons(byBody);

  bindClickableTaskRows(toBody);
  bindClickableTaskRows(byBody);
  
  renderTablePagination(toBody, "myTaskTo", toPageData, renderMyTasks);
 renderTablePagination(byBody, "myTaskBy", byPageData, renderMyTasks);
}

function bindClickableTaskRows(scope) {
  (scope || root).querySelectorAll(".life-clickable-row").forEach(function (row) {
    if (row.dataset.boundClickableTaskRow === "1") return;

    row.dataset.boundClickableTaskRow = "1";

    row.addEventListener("click", function (e) {
      // Do not open details when clicking action buttons, links, or form controls
      if (
          e.target.closest("button") ||
          e.target.closest("a") ||
          e.target.closest(".btn") ||
          e.target.closest("input") ||
          e.target.closest("select") ||
          e.target.closest("textarea") ||
          e.target.closest(".attach-chip-table")
        ) {
        return;
      }

      var id = row.dataset.detailHtmlId || "";
      var detail = detailHtmlRegistry[id] || {};

      var doctype = row.dataset.doctype || "";
      var docname = row.dataset.docname || "";

      var html =
        (detail.html || "") +
        modalAttachmentHtml(doctype, docname) +
        (detail.afterHtml || "");

      showRichModal(
        "📄",
        detail.title || "Task Details",
        html
      );
    });
  });
}

function markTaskDone(name) {
  promptWorkflowRemarks(
    "Complete Task",
    "Completion Remarks *",
    100,
    function (remarks) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "ToDo",
          name: name
        },
        callback: function (r) {
          var doc = r.message;

          if (!doc) {
            showModal("⚠️", "Task Not Found", "Unable to load task.");
            return;
          }

          var meta = getTaskMeta(doc);
          var details = getTaskDetails(doc);

          meta.workflow_state = "Completed";
          meta.completed_on = getNowLocalDateTime();
          meta.completed_by = currentUser;
          meta.completed_by_name = currentUserFullName || currentUser;
          meta.completion_remarks = remarks;

          meta.worked_days = calculateWorkedDaysLabel(
            {
              creation: doc.creation,
              modified: doc.modified,
              date: doc.date,
              status: "Closed"
            },
            meta
          );

          meta.completion_history = meta.completion_history || [];
          meta.completion_history.push({
            by: currentUser,
            by_name: currentUserFullName || currentUser,
            on: meta.completed_on,
            remarks: remarks
          });

          // Important: keep ERP ToDo open until assigner closes it
          doc.status = "Open";
          doc.description = buildTaskDescription(details, meta);

          frappe.call({
            method: "frappe.client.save",
            args: {
              doc: doc
            },
            callback: function () {
              toast("Task completion submitted for assigner review.", true);
              loadTasks();
            },
            error: function (err) {
              showModal("⚠️", "Update Failed", getErrorMessage(err));
            }
          });
        },
        error: function (err) {
          showModal("⚠️", "Task Load Failed", getErrorMessage(err));
        }
      });
    }
  );
}

function closeTaskAfterReview(name) {
  frappe.confirm(
    "Are you satisfied with this task completion and want to close it?",
    function () {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "ToDo",
          name: name
        },
        callback: function (r) {
          var doc = r.message;

          if (!doc) {
            showModal("⚠️", "Task Not Found", "Unable to load task.");
            return;
          }

          var meta = getTaskMeta(doc);
          var details = getTaskDetails(doc);

          meta.workflow_state = "Closed";
          meta.closed_on = getNowLocalDateTime();
          meta.closed_by = currentUser;
          meta.closed_by_name = currentUserFullName || currentUser;

          meta.close_history = meta.close_history || [];
          meta.close_history.push({
            by: currentUser,
            by_name: currentUserFullName || currentUser,
            on: meta.closed_on,
            remarks: "Accepted and closed by assigner."
          });

          doc.status = "Closed";
          doc.description = buildTaskDescription(details, meta);

          frappe.call({
            method: "frappe.client.save",
            args: {
              doc: doc
            },
            callback: function () {
              toast("Task closed successfully.", true);
              loadTasks();
            },
            error: function (err) {
              showModal("⚠️", "Close Failed", getErrorMessage(err));
            }
          });
        },
        error: function (err) {
          showModal("⚠️", "Task Load Failed", getErrorMessage(err));
        }
      });
    }
  );
}

function reopenTaskAfterReview(name) {
  promptWorkflowRemarks(
    "Reopen Task",
    "Review Remarks *",
    100,
    function (remarks) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "ToDo",
          name: name
        },
        callback: function (r) {
          var doc = r.message;

          if (!doc) {
            showModal("⚠️", "Task Not Found", "Unable to load task.");
            return;
          }

          var meta = getTaskMeta(doc);
          var details = getTaskDetails(doc);

          meta.workflow_state = "Reopened";
          meta.reopened_on = getNowLocalDateTime();
          meta.reopened_by = currentUser;
          meta.reopened_by_name = currentUserFullName || currentUser;
          meta.reopen_review_remarks = remarks;

          meta.reopen_history = meta.reopen_history || [];
          meta.reopen_history.push({
            by: currentUser,
            by_name: currentUserFullName || currentUser,
            on: meta.reopened_on,
            remarks: remarks
          });

          doc.status = "Open";
          doc.description = buildTaskDescription(details, meta);

          frappe.call({
            method: "frappe.client.save",
            args: {
              doc: doc
            },
            callback: function () {
              toast("Task reopened successfully.", true);
              loadTasks();
            },
            error: function (err) {
              showModal("⚠️", "Reopen Failed", getErrorMessage(err));
            }
          });
        },
        error: function (err) {
          showModal("⚠️", "Task Load Failed", getErrorMessage(err));
        }
      });
    }
  );
}


function undoTaskCompleted(name) {
  frappe.confirm(
    "Do you want to undo completion and reopen this task?",
    function () {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "ToDo",
          name: name
        },
        callback: function (r) {
          var doc = r.message;

          if (!doc) {
            showModal("⚠️", "Task Not Found", "Unable to load task.");
            return;
          }

          var meta = getTaskMeta(doc);
          var details = getTaskDetails(doc);

          delete meta.completed_on;
          delete meta.completed_by;
          delete meta.completed_by_name;
          delete meta.worked_days;

          doc.status = "Open";
          doc.description = buildTaskDescription(details, meta);

          frappe.call({
            method: "frappe.client.save",
            args: {
              doc: doc
            },
            callback: function () {
              toast("Task reopened successfully.", true);
              loadTasks();
            },
            error: function (err) {
              showModal("⚠️", "Undo Failed", getErrorMessage(err));
            }
          });
        },
        error: function (err) {
          showModal("⚠️", "Task Load Failed", getErrorMessage(err));
        }
      });
    }
  );
}


function openTaskDelayReview(name) {
  var task = tasks.find(function (t) {
    return t.name === name;
  });

  if (!task) {
    showModal("⚠️", "Task Not Found", "Unable to find this overdue task.");
    return;
  }

  var status = getTaskStatus(task);

  if (status !== "Overdue") {
    showModal(
      "⚠️",
      "Not Allowed",
      "Deadline can be changed from this button only when the task is overdue."
    );
    return;
  }

  if (!isTaskAssigner(task)) {
    showModal(
      "⚠️",
      "Not Allowed",
      "Only the task assigner can change deadline for an overdue task."
    );
    return;
  }

  var meta = getTaskMeta(task);
  var oldDeadline = meta.deadline_datetime || (task.date ? task.date + "T23:59" : "");

  ensureTaskDelayReviewModal();

  var modal = $("#life-task-delay-modal");
  if (!modal) return;

  modal.dataset.taskName = name || "";
  modal.dataset.oldDeadline = oldDeadline || "";

  var titleEl = modal.querySelector(".life-delay-title");
  var subEl = modal.querySelector(".life-delay-sub");

  if (titleEl) {
    titleEl.textContent = "Change Overdue Task Deadline";
  }

  if (subEl) {
    subEl.textContent = "Only the assigner can extend the deadline. After saving, task will become Open.";
  }

  setText("life-delay-old-deadline", oldDeadline ? formatLifeDateTime(oldDeadline) : "—");

  var suggested = getSuggestedDelayDateTimeParts();

  setValue("life-delay-date", suggested.date);
  setValue("life-delay-hour", suggested.hour);
  setValue("life-delay-minute", suggested.minute);
  setValue("life-delay-ampm", suggested.ampm);
  setValue("life-delay-remarks", "");

  setText("life-delay-wordcount", "0 / 100 words");
  showDelayError("");

  var dateEl = $("#life-delay-date");
  if (dateEl) {
    dateEl.setAttribute("min", getTodayLocalDate());
  }

  modal.classList.add("show");
}



function ensureTaskDelayReviewModal() {
  if ($("#life-task-delay-modal")) return;

  var app = $("#life-tt-app") || root;

  app.insertAdjacentHTML("beforeend", `
    <div id="life-task-delay-modal" class="life-delay-modal">
      <div class="life-delay-box">
        <div class="life-delay-head">
          <div>
            <div class="life-delay-title">Review Delayed Task</div>
            <div class="life-delay-sub">Set a new deadline and mention why the task was delayed</div>
          </div>
          <button type="button" class="life-delay-close" id="life-delay-close-btn">×</button>
        </div>

        <div class="life-delay-body">
          <div class="life-delay-old">
            <strong>Current / Old Deadline:</strong>
            <span id="life-delay-old-deadline">—</span>
          </div>

          <div class="life-delay-grid">
            <div class="field-block">
              <label class="lbl">New Deadline Date <span class="required-mark">*</span></label>
              <input type="date" id="life-delay-date">
            </div>

            <div class="field-block">
              <label class="lbl">New Deadline Time <span class="required-mark">*</span></label>
              <div class="life-delay-time-row">
                <select id="life-delay-hour"></select>
                <select id="life-delay-minute"></select>
                <select id="life-delay-ampm">
                  <option value="AM">AM</option>
                  <option value="PM">PM</option>
                </select>
              </div>
            </div>
          </div>

          <div class="field-block">
            <label class="lbl">Delay Review Remarks <span class="required-mark">*</span></label>
            <textarea id="life-delay-remarks" placeholder="Mention why the task was delayed and why the deadline is being extended."></textarea>
            <div class="life-delay-wordcount" id="life-delay-wordcount">0 / 100 words</div>
          </div>

          <div class="life-delay-error" id="life-delay-error"></div>
        </div>

        <div class="life-delay-footer">
          <button type="button" class="btn btn-gy" id="life-delay-cancel-btn">Cancel</button>
          <button type="button" class="btn btn-n" id="life-delay-save-btn">Save Review</button>
        </div>
      </div>
    </div>
  `);

  populateDelayTimeDropdowns();

  var closeBtn = $("#life-delay-close-btn");
  var cancelBtn = $("#life-delay-cancel-btn");
  var saveBtn = $("#life-delay-save-btn");
  var dateEl = $("#life-delay-date");
  var remarksEl = $("#life-delay-remarks");

  if (closeBtn) closeBtn.addEventListener("click", closeTaskDelayReviewModal);
  if (cancelBtn) cancelBtn.addEventListener("click", closeTaskDelayReviewModal);
  if (saveBtn) saveBtn.addEventListener("click", submitTaskDelayReviewModal);

  if (dateEl) {
    dateEl.addEventListener("change", function () {
      validateDelayDateSoft();
    });
  }

  if (remarksEl) {
  bindWordLimit(remarksEl, $("#life-delay-wordcount"), 100);
}

  var modal = $("#life-task-delay-modal");
  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target === modal) {
        closeTaskDelayReviewModal();
      }
    });
  }
}

function populateDelayTimeDropdowns() {
  var hourEl = $("#life-delay-hour");
  var minuteEl = $("#life-delay-minute");

  if (hourEl) {
    hourEl.innerHTML = "";

    for (var h = 1; h <= 12; h++) {
      var hh = String(h).padStart(2, "0");
      hourEl.innerHTML += '<option value="' + hh + '">' + hh + '</option>';
    }
  }

  if (minuteEl) {
    minuteEl.innerHTML = "";

    for (var m = 0; m < 60; m += 5) {
      var mm = String(m).padStart(2, "0");
      minuteEl.innerHTML += '<option value="' + mm + '">' + mm + '</option>';
    }
  }
}

function getSuggestedDelayDateTimeParts() {
  var d = new Date();

  // Default: current time + 1 hour
  d.setHours(d.getHours() + 1);

  var yyyy = d.getFullYear();
  var mm = String(d.getMonth() + 1).padStart(2, "0");
  var dd = String(d.getDate()).padStart(2, "0");

  var hour24 = d.getHours();
  var minute = Math.ceil(d.getMinutes() / 5) * 5;

  if (minute >= 60) {
    minute = 0;
    hour24 += 1;
  }

  var ampm = hour24 >= 12 ? "PM" : "AM";
  var hour12 = hour24 % 12;
  if (hour12 === 0) hour12 = 12;

  return {
    date: yyyy + "-" + mm + "-" + dd,
    hour: String(hour12).padStart(2, "0"),
    minute: String(minute).padStart(2, "0"),
    ampm: ampm
  };
}

function buildDelayDateTimeValue() {
  var date = getValue("life-delay-date");
  var hour = Number(getValue("life-delay-hour") || 0);
  var minute = getValue("life-delay-minute");
  var ampm = getValue("life-delay-ampm");

  if (!date || !hour || !minute || !ampm) return "";

  if (ampm === "PM" && hour < 12) {
    hour += 12;
  }

  if (ampm === "AM" && hour === 12) {
    hour = 0;
  }

  return date + "T" + String(hour).padStart(2, "0") + ":" + minute;
}

function validateDelayDateSoft() {
  var dateEl = $("#life-delay-date");
  if (!dateEl) return;

  var today = getTodayLocalDate();

  dateEl.setAttribute("min", today);

  if (dateEl.value && dateEl.value < today) {
    dateEl.value = today;
    showDelayError("Past dates are not allowed. Date has been reset to today.");
  } else {
    showDelayError("");
  }
}

function submitTaskDelayReviewModal() {
  var modal = $("#life-task-delay-modal");
  if (!modal) return;

  var name = modal.dataset.taskName || "";
  var oldDeadline = modal.dataset.oldDeadline || "";

  var remarks = getValue("life-delay-remarks");
  var newDeadline = buildDelayDateTimeValue();

  if (!newDeadline) {
    showDelayError("Please select new deadline date and time.");
    return;
  }

  if (newDeadline < getNowLocalDateTime()) {
    showDelayError("New deadline cannot be in the past. Please select a future date/time.");
    return;
  }

  if (!remarks) {
    showDelayError("Please enter delay review remarks.");
    return;
  }

  if (wordCount(remarks) > 100) {
    showDelayError("Delay review remarks cannot exceed 100 words.");
    return;
  }

  closeTaskDelayReviewModal();

  saveTaskDelayReview(name, oldDeadline, {
    new_deadline: newDeadline,
    remarks: remarks
  });
}

function closeTaskDelayReviewModal() {
  var modal = $("#life-task-delay-modal");
  if (modal) modal.classList.remove("show");
}

function showDelayError(message) {
  var el = $("#life-delay-error");
  if (!el) return;

  if (!message) {
    el.textContent = "";
    el.classList.remove("show");
    return;
  }

  el.textContent = message;
  el.classList.add("show");
}


function saveTaskDelayReview(name, oldDeadline, values) {
  var newDeadline = String(values.new_deadline || "").trim();
  var remarks = String(values.remarks || "").trim();

  if (!remarks) {
    showModal("⚠️", "Remarks Required", "Please enter deadline change remarks.");
    return;
  }

  if (wordCount(remarks) > 100) {
    showModal("⚠️", "Remarks Too Long", "Deadline change remarks cannot exceed 100 words.");
    return;
  }

  if (!newDeadline) {
    showModal("⚠️", "New Deadline Required", "Please select a new deadline.");
    return;
  }

  var normalizedNewDeadline = normalizeDateTimeValue(newDeadline);

  if (normalizedNewDeadline < getNowLocalDateTime()) {
    showModal("⚠️", "Past Deadline Not Allowed", "New deadline cannot be in the past.");
    return;
  }

  frappe.call({
    method: "frappe.client.get",
    args: {
      doctype: "ToDo",
      name: name
    },
    callback: function (r) {
      var doc = r.message;

      if (!doc) {
        showModal("⚠️", "Task Not Found", "Unable to load task.");
        return;
      }

      var currentStatus = getTaskStatus(doc);

      if (currentStatus !== "Overdue") {
        showModal(
          "⚠️",
          "Not Allowed",
          "Deadline can be changed only when the task is overdue."
        );
        return;
      }

      if (!isTaskAssigner(doc)) {
        showModal(
          "⚠️",
          "Not Allowed",
          "Only the task assigner can change deadline for this overdue task."
        );
        return;
      }

      var meta = getTaskMeta(doc);
      var details = getTaskDetails(doc);

      meta.delay_reviews = meta.delay_reviews || [];

      meta.delay_reviews.push({
        review_type: "Assigner Deadline Change",
        reviewed_by: currentUser,
        reviewed_by_name: currentUserFullName || currentUser,
        reviewed_on: getNowReadableDateTime(),
        old_deadline: oldDeadline || meta.deadline_datetime || doc.date || "",
        new_deadline: normalizedNewDeadline,
        remarks: remarks
      });

      meta.deadline_datetime = normalizedNewDeadline;
      meta.duration_label = calculateTaskDurationDays(
        meta.start_date || getTaskStartDate(doc, meta),
        normalizedNewDeadline
      );

      // Important:
      // After assigner changes overdue deadline, task becomes Open again.
      meta.workflow_state = "Open";

      doc.status = "Open";
      doc.date = getDatePartFromDateTime(normalizedNewDeadline);
      doc.description = buildTaskDescription(details, meta);

      frappe.call({
        method: "frappe.client.save",
        args: {
          doc: doc
        },
        callback: function () {
          toast("Deadline changed successfully. Task is now Open.", true);
          loadTasks();
        },
        error: function (err) {
          showModal("⚠️", "Deadline Change Failed", getErrorMessage(err));
        }
      });
    },
    error: function (err) {
      showModal("⚠️", "Task Load Failed", getErrorMessage(err));
    }
  });
}


function isTaskAssignee(t) {
  return isCurrentUserValue(t.allocated_to);
}

function isTaskAssigner(t) {
  return (
    isCurrentUserValue(t.assigned_by || "") ||
    isCurrentUserValue(t.owner || "") ||
    t.assigned_by === currentUser ||
    t.owner === currentUser
  );
}

function isTicketResolver(t, meta) {
  meta = meta || getTicketMeta(t);
  return isCurrentUserValue(meta.tag_to || "");
}

function isTicketRaiser(t) {
  return (
    isCurrentUserValue(t.raised_by || "") ||
    isCurrentUserValue(t.owner || "") ||
    t.raised_by === currentUser ||
    t.owner === currentUser
  );
}

function bindDialogRemarksWordLimit(dialog, fieldname, maxWords) {
  setTimeout(function () {
    if (!dialog || !dialog.fields_dict || !dialog.fields_dict[fieldname]) return;

    var field = dialog.fields_dict[fieldname];
    var input = null;

    if (field.$input && field.$input[0]) {
      input = field.$input[0];
    }

    if (!input) return;

    var wrapper = field.$wrapper && field.$wrapper[0] ? field.$wrapper[0] : input.parentNode;

    var countEl = document.createElement("div");
    countEl.className = "wordcount";
    countEl.textContent = "0 / " + maxWords + " words";
    countEl.style.marginTop = "5px";

    wrapper.appendChild(countEl);

    bindWordLimit(input, countEl, maxWords);
  }, 300);
}

function promptWorkflowRemarks(title, label, maxWords, callback) {
  maxWords = maxWords || 100;

  var dialog = frappe.prompt(
    [
      {
        fieldname: "remarks",
        label: (label || "Remarks") + " max " + maxWords + " words",
        fieldtype: "Small Text",
        reqd: 1
      }
    ],
    function (values) {
      var remarks = String(values.remarks || "").trim();

      if (!remarks) {
        showModal("⚠️", "Remarks Required", "Please enter remarks.");
        return;
      }

      if (wordCount(remarks) > maxWords) {
        showModal(
          "⚠️",
          "Too Many Words",
          "Remarks cannot exceed " + maxWords + " words."
        );
        return;
      }

      callback(remarks);
    },
    title || "Remarks",
    "Submit"
  );

  bindDialogRemarksWordLimit(dialog, "remarks", maxWords);
}


function buildWorkflowHistoryHtml(title, rows, typeLabel) {
  rows = rows || [];

  if (!rows.length) {
    return "";
  }

  return '' +
    '<div class="life-detail-section">' +
      '<div class="life-detail-section-title">' + esc(title) + '</div>' +
      '<div class="life-history-list">' +
        rows.map(function (h, idx) {
          return '' +
            '<div class="life-history-card">' +
              '<div class="life-history-head">' +
                '<div class="life-history-title">' +
                  esc(typeLabel || "History") + ' #' + (idx + 1) + ' - ' +
                  esc(h.by_name || h.completed_by_name || h.resolved_by_name || h.reopened_by_name || h.closed_by_name || h.by || "—") +
                '</div>' +
                '<div class="life-history-date">' +
                  esc(formatLifeDateTime(h.on || h.completed_on || h.resolved_on || h.reopened_on || h.closed_on || "")) +
                '</div>' +
              '</div>' +
              '<div class="life-detail-label">Remarks</div>' +
              '<div class="life-history-remarks">' + esc(h.remarks || "—") + '</div>' +
            '</div>';
        }).join("") +
      '</div>' +
    '</div>';
}

function buildTaskWorkflowHistorySection(meta) {
  meta = meta || {};

  return '' +
    buildWorkflowHistoryHtml(
      "Completion History",
      meta.completion_history || [],
      "Completion"
    ) +
    buildWorkflowHistoryHtml(
      "Reopen History",
      meta.reopen_history || [],
      "Reopen"
    ) +
    buildWorkflowHistoryHtml(
      "Close History",
      meta.close_history || [],
      "Close"
    );
}

function buildTaskExtraHistorySection(meta) {
  return ''
    + buildTaskAssignerUpdatesSection(meta)
    + buildTaskWorkflowHistorySection(meta)
    + buildTaskDelayHistorySection(meta);
}


function buildTaskAssignerUpdatesSection(meta) {
  meta = meta || {};

  var rows = meta.assigner_updates || [];

  if (!rows.length) {
    return "";
  }

  return '' +
    '<div class="life-detail-section">' +
      '<div class="life-detail-section-title">Assigner Updates / Reference Notes</div>' +
      '<div class="life-history-list">' +
        rows.map(function (h, idx) {
          var files = h.files || [];

          var fileBlock = "";

          if (files.length) {
            fileBlock =
              '<div class="life-update-files-block">' +
                '<div class="life-detail-label">Files Added In This Update</div>' +
                renderTaskUpdateFileRows(files) +
              '</div>';
          } else if (Number(h.file_count || 0) > 0) {
            // Fallback for old updates saved before this improvement
            fileBlock =
              '<div class="life-update-files-block">' +
                '<div class="life-detail-label">Files Added In This Update</div>' +
                '<div class="life-update-no-files">' +
                  Number(h.file_count || 0) + ' file(s) were added, but file-level mapping is not available for this older update. Check the main attachments section.' +
                '</div>' +
              '</div>';
          } else {
            fileBlock =
              '<div class="life-update-files-block">' +
                '<div class="life-detail-label">Files Added In This Update</div>' +
                '<div class="life-update-no-files">No files added in this update.</div>' +
              '</div>';
          }

          return '' +
            '<div class="life-history-card life-update-history-card">' +
              '<div class="life-history-head">' +
                '<div class="life-history-title">' +
                  'Update #' + (idx + 1) + ' - ' + esc(h.by_name || h.by || "—") +
                '</div>' +
                '<div class="life-history-date">' +
                  esc(formatLifeDateTime(h.on || "")) +
                '</div>' +
              '</div>' +

              '<div class="life-history-grid">' +
                '<div>' +
                  '<div class="life-detail-label">Update Type</div>' +
                  '<div class="life-detail-value">' + esc(h.update_type || "Information") + '</div>' +
                '</div>' +
                '<div>' +
                  '<div class="life-detail-label">Stage</div>' +
                  '<div class="life-detail-value">Assigner Update</div>' +
                '</div>' +
              '</div>' +

              '<div class="life-detail-label">Remarks</div>' +
              '<div class="life-history-remarks">' + esc(h.remarks || "—") + '</div>' +

              fileBlock +
            '</div>';
        }).join("") +
      '</div>' +
    '</div>';
}


function buildTicketWorkflowHistorySection(meta) {
  meta = meta || {};

  return '' +
    buildWorkflowHistoryHtml(
      "Resolution History",
      meta.resolution_history || [],
      "Resolution"
    ) +
    buildWorkflowHistoryHtml(
      "Reopen History",
      meta.reopen_history || [],
      "Reopen"
    ) +
    buildWorkflowHistoryHtml(
      "Close History",
      meta.close_history || [],
      "Close"
    );
}

function renderTaskActionButtons(t) {
  var status = getTaskStatus(t);

  if (status === "Cancelled" || status === "Closed") {
    return "—";
  }

  // OVERDUE RULE:
  // Assignee should not act.
  // Assigner must change deadline first.
  if (status === "Overdue") {
    if (isTaskAssigner(t)) {
      return '' +
        '<button class="btn btn-deadline btn-sm task-change-deadline-btn" data-name="' + esc(t.name) + '">' +
          'Change Deadline' +
        '</button>';
    }

    return '<span class="pill p-o">Waiting for Assigner Deadline Review</span>';
  }

  // Completed task: assigner must close or reopen.
  if (status === "Completed") {
    if (isTaskAssigner(t)) {
      return '' +
        '<div class="life-action-stack">' +
          '<button class="btn btn-g btn-sm task-close-btn" data-name="' + esc(t.name) + '">' +
            'Close Task' +
          '</button>' +
          '<button class="btn btn-undo btn-sm task-reopen-btn" data-name="' + esc(t.name) + '">' +
            'Reopen Task' +
          '</button>' +
        '</div>';
    }

    return '<span class="pill p-o">Waiting for Assigner Review</span>';
  }

  var buttons = [];

  // Assigner can add updates only while task is active, not overdue.
  if (isTaskAssigner(t) && (status === "Open" || status === "Reopened")) {
    buttons.push(
      '<button class="btn btn-info btn-sm task-add-update-btn" data-name="' + esc(t.name) + '">' +
        'Add Update' +
      '</button>'
    );
  }

  // Assignee can complete only Open / Reopened task.
  if (isTaskAssignee(t) && (status === "Open" || status === "Reopened")) {
    buttons.push(
      '<button class="btn btn-g btn-sm task-done-btn" data-name="' + esc(t.name) + '">' +
        'Mark Complete' +
      '</button>'
    );
  }

  if (!buttons.length) {
    return "—";
  }

  return '<div class="life-action-stack">' + buttons.join("") + '</div>';
}


function bindTaskActionButtons(scope) {
  (scope || root).querySelectorAll(".task-done-btn").forEach(function (btn) {
    if (btn.dataset.boundTaskDone === "1") return;

    btn.dataset.boundTaskDone = "1";

    btn.addEventListener("click", function () {
      markTaskDone(btn.dataset.name);
    });
  });

  (scope || root).querySelectorAll(".task-close-btn").forEach(function (btn) {
    if (btn.dataset.boundTaskClose === "1") return;

    btn.dataset.boundTaskClose = "1";

    btn.addEventListener("click", function () {
      closeTaskAfterReview(btn.dataset.name);
    });
  });
  
  (scope || root).querySelectorAll(".task-add-update-btn").forEach(function (btn) {
      if (btn.dataset.boundTaskAddUpdate === "1") return;
    
      btn.dataset.boundTaskAddUpdate = "1";
    
      btn.addEventListener("click", function () {
        openTaskUpdateModal(btn.dataset.name);
      });
    });

  (scope || root).querySelectorAll(".task-reopen-btn").forEach(function (btn) {
    if (btn.dataset.boundTaskReopen === "1") return;

    btn.dataset.boundTaskReopen = "1";

    btn.addEventListener("click", function () {
      reopenTaskAfterReview(btn.dataset.name);
    });
  });
  
  (scope || root).querySelectorAll(".task-change-deadline-btn").forEach(function (btn) {
      if (btn.dataset.boundTaskChangeDeadline === "1") return;
    
      btn.dataset.boundTaskChangeDeadline = "1";
    
      btn.addEventListener("click", function () {
        openTaskDelayReview(btn.dataset.name);
      });
    });

  (scope || root).querySelectorAll(".task-review-delay-btn").forEach(function (btn) {
    if (btn.dataset.boundTaskReview === "1") return;

    btn.dataset.boundTaskReview = "1";

    btn.addEventListener("click", function () {
      openTaskDelayReview(btn.dataset.name);
    });
  });
}

function openTaskUpdateModal(name) {
  var task = tasks.find(function (t) {
    return t.name === name;
  });

  if (!task) {
    showModal("⚠️", "Task Not Found", "Unable to find this task.");
    return;
  }

  var status = getTaskStatus(task);
      if (status === "Overdue") {
      showModal(
        "⚠️",
        "Update Not Allowed",
        "This task is overdue. First the assigner must change the deadline. Updates cannot be added in overdue state."
      );
      return;
    }

  if (status === "Closed" || status === "Cancelled" || status === "Completed") {
    showModal("⚠️", "Not Allowed", "Updates cannot be added to closed or cancelled tasks.");
    return;
  }

  if (!isTaskAssigner(task)) {
    showModal("⚠️", "Not Allowed", "Only the task assigner can add updates.");
    return;
  }

  ensureTaskUpdateModal();

  taskUpdateFiles = [];
  renderTaskUpdateFiles();

  var modal = $("#life-task-update-modal");
  if (!modal) return;

  modal.dataset.taskName = name || "";

  setValue("life-task-update-type", "Information");
  setValue("life-task-update-remarks", "");
  setText("life-task-update-wordcount", "0 / 100 words");
  showTaskUpdateError("");
  
  resetLifePopupScroll(modal);

  modal.classList.add("show");
}

function resetLifePopupScroll(modal) {
  if (!modal) return;

  var box = modal.querySelector(".life-delay-box");
  var body = modal.querySelector(".life-delay-body");

  modal.scrollTop = 0;

  if (box) {
    box.scrollTop = 0;
  }

  if (body) {
    body.scrollTop = 0;
  }

  setTimeout(function () {
    modal.scrollTop = 0;
    if (box) box.scrollTop = 0;
    if (body) body.scrollTop = 0;
  }, 0);

  setTimeout(function () {
    modal.scrollTop = 0;
    if (box) box.scrollTop = 0;
    if (body) body.scrollTop = 0;
  }, 50);
}

function ensureTaskUpdateModal() {
  if ($("#life-task-update-modal")) return;

  var app = $("#life-tt-app") || root;

  app.insertAdjacentHTML("beforeend", `
    <div id="life-task-update-modal" class="life-delay-modal">
      <div class="life-delay-box">
        <div class="life-delay-head">
          <div>
            <div class="life-delay-title">Add Task Update</div>
            <div class="life-delay-sub">Add new information or reference files for the assignee</div>
          </div>
          <button type="button" class="life-delay-close" id="life-task-update-close">×</button>
        </div>

        <div class="life-delay-body">
          <div class="field-block">
            <label class="lbl">Update Type <span class="required-mark">*</span></label>
            <select id="life-task-update-type">
              <option value="Information">Information</option>
              <option value="Reference File">Reference File</option>
              <option value="Correction">Correction</option>
              <option value="Urgent Note">Urgent Note</option>
            </select>
          </div>

          <div class="field-block">
            <label class="lbl">Update Remarks <span class="required-mark">*</span> max 100 words</label>
            <textarea id="life-task-update-remarks" placeholder="Enter the new instruction, clarification, or file reference note."></textarea>
            <div class="life-delay-wordcount" id="life-task-update-wordcount">0 / 100 words</div>
          </div>

          <div class="field-block">
            <label class="lbl">Reference Attachments Optional</label>
            <div class="attach-zone" id="life-task-update-attach-zone">
              📎 Click to attach reference files
            </div>
            <input type="file" id="life-task-update-file-input" multiple style="display:none">
            <div class="attach-list" id="life-task-update-attach-list"></div>
          </div>

          <div class="life-delay-error" id="life-task-update-error"></div>
        </div>

        <div class="life-delay-footer">
          <button type="button" class="btn btn-gy btn-sm" id="life-task-update-cancel">Cancel</button>
          <button type="button" class="btn btn-n btn-sm" id="life-task-update-save">Save Update</button>
        </div>
      </div>
    </div>
  `);

  var closeBtn = $("#life-task-update-close");
  var cancelBtn = $("#life-task-update-cancel");
  var saveBtn = $("#life-task-update-save");
  var zone = $("#life-task-update-attach-zone");
  var fileInput = $("#life-task-update-file-input");
  var remarksEl = $("#life-task-update-remarks");

  if (closeBtn) closeBtn.addEventListener("click", closeTaskUpdateModal);
  if (cancelBtn) cancelBtn.addEventListener("click", closeTaskUpdateModal);
  if (saveBtn) saveBtn.addEventListener("click", submitTaskUpdateModal);

  if (zone && fileInput) {
    zone.addEventListener("click", function () {
      fileInput.click();
    });

    fileInput.addEventListener("change", function () {
      addTaskUpdateFiles(fileInput.files || []);
      fileInput.value = "";
    });
  }

  if (remarksEl) {
    remarksEl.addEventListener("input", function () {
      var count = wordCount(remarksEl.value);
      setText("life-task-update-wordcount", count + " / 100 words");

      var wc = $("#life-task-update-wordcount");
      if (wc) {
        wc.classList.toggle("over", count > 100);
      }
    });
  }
}

function closeTaskUpdateModal() {
  var modal = $("#life-task-update-modal");
  if (modal) modal.classList.remove("show");

  taskUpdateFiles = [];
  renderTaskUpdateFiles();
  showTaskUpdateError("");
}

function showTaskUpdateError(message) {
  var el = $("#life-task-update-error");
  if (!el) return;

  if (!message) {
    el.textContent = "";
    el.classList.remove("show");
    return;
  }

  el.textContent = message;
  el.classList.add("show");
}

function addTaskUpdateFiles(files) {
  var rejected = [];
  var validNewFiles = [];

  Array.prototype.slice.call(files || []).forEach(function (file) {
    var validation = validateAttachmentFile(file);

    if (!validation.ok) {
      rejected.push("• " + (file.name || "File") + " - " + validation.message);
      return;
    }

    var alreadyAdded = taskUpdateFiles.some(function (existingFile) {
      return (
        existingFile.name === file.name &&
        existingFile.size === file.size &&
        existingFile.lastModified === file.lastModified
      );
    });

    var alreadyInNew = validNewFiles.some(function (existingFile) {
      return (
        existingFile.name === file.name &&
        existingFile.size === file.size &&
        existingFile.lastModified === file.lastModified
      );
    });

    if (!alreadyAdded && !alreadyInNew) {
      validNewFiles.push(file);
    }
  });

  if (taskUpdateFiles.length + validNewFiles.length > MAX_ATTACHMENT_COUNT) {
    showTaskUpdateError(
      "You can upload maximum " + MAX_ATTACHMENT_COUNT + " files only.\n\n" +
      "Currently selected: " + taskUpdateFiles.length + "\n" +
      "Trying to add: " + validNewFiles.length + "\n\n" +
      "Please remove some files and try again."
    );
    return;
  }

  validNewFiles.forEach(function (file) {
    taskUpdateFiles.push(file);
  });

  renderTaskUpdateFiles();

  if (rejected.length) {
    showTaskUpdateError(
      "Only allowed documents/images/HTML files up to 5 MB can be attached.\n\n" +
      rejected.join("\n")
    );
  }
}
function renderTaskUpdateFiles() {
  var list = $("#life-task-update-attach-list");
  if (!list) return;

  if (!taskUpdateFiles.length) {
    list.innerHTML = "";
    return;
  }

  list.innerHTML = taskUpdateFiles.map(function (file, idx) {
    var mimeType = String(file.type || "").toLowerCase();
    var icon = mimeType.indexOf("image/") === 0 ? "🖼️" : "📄";

    return '' +
      '<div class="attach-item">' +
        '<span class="an">' + icon + ' ' + esc(file.name || "File") + '</span>' +
        '<span class="asize">' + esc(formatFileSize(file.size || 0)) + '</span>' +
        '<span class="x" data-idx="' + idx + '">×</span>' +
      '</div>';
  }).join("");

  list.querySelectorAll(".attach-item .x").forEach(function (x) {
    x.addEventListener("click", function () {
      var idx = Number(x.dataset.idx || 0);
      taskUpdateFiles.splice(idx, 1);
      renderTaskUpdateFiles();
    });
  });
}

function submitTaskUpdateModal() {
  var modal = $("#life-task-update-modal");
  if (!modal) return;

  var name = modal.dataset.taskName || "";
  var updateType = getValue("life-task-update-type");
  var remarks = getValue("life-task-update-remarks");

  if (!name) {
    showTaskUpdateError("Task reference missing. Please close and try again.");
    return;
  }

  if (!updateType) {
    showTaskUpdateError("Please select update type.");
    return;
  }

  if (!remarks) {
    showTaskUpdateError("Please enter update remarks.");
    return;
  }

  if (wordCount(remarks) > 100) {
    showTaskUpdateError("Update remarks cannot exceed 100 words.");
    return;
  }

  var validation = validateAttachmentList(taskUpdateFiles);

  if (!validation.ok) {
    showTaskUpdateError(validation.message);
    return;
  }

  var saveBtn = $("#life-task-update-save");
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving.";
  }

  saveTaskAssignerUpdate(name, {
    update_type: updateType,
    remarks: remarks,
    files: taskUpdateFiles.slice()
  }, function () {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save Update";
    }
  });
}

function saveTaskAssignerUpdate(name, values, alwaysCallback) {
  values = values || {};

  frappe.call({
    method: "frappe.client.get",
    args: {
      doctype: "ToDo",
      name: name
    },
    callback: function (r) {
      var doc = r.message;

      if (!doc) {
        if (alwaysCallback) alwaysCallback();
        showTaskUpdateError("Unable to load task.");
        return;
      }

      var status = getTaskStatus(doc);

      if (status === "Closed" || status === "Cancelled" || status === "Completed") {
        if (alwaysCallback) alwaysCallback();
        showTaskUpdateError("Updates can be added only while task is Open or Reopened.");
        return;
      }

      if (status === "Overdue") {
        if (alwaysCallback) alwaysCallback();
        showTaskUpdateError("This task is overdue. First change the deadline. Updates cannot be added in overdue state.");
        return;
      }

      if (!isTaskAssigner(doc)) {
        if (alwaysCallback) alwaysCallback();
        showTaskUpdateError("Only the task assigner can add updates.");
        return;
      }

      var filesToUpload = values.files || [];

      uploadFiles("ToDo", doc.name, filesToUpload)
        .then(function (uploadedRows) {
          var meta = getTaskMeta(doc);
          var details = getTaskDetails(doc);

          var updateFiles = normalizeTaskUpdateFiles(uploadedRows, filesToUpload);

          meta.assigner_updates = meta.assigner_updates || [];

          meta.assigner_updates.push({
            update_id: "UPD-" + Date.now(),
            by: currentUser,
            by_name: currentUserFullName || currentUser,
            on: getNowLocalDateTime(),
            update_type: values.update_type || "Information",
            remarks: values.remarks || "",
            file_count: updateFiles.length,
            files: updateFiles
          });

          doc.description = buildTaskDescription(details, meta);

          frappe.call({
            method: "frappe.client.save",
            args: {
              doc: doc
            },
            callback: function () {
              closeTaskUpdateModal();
              toast("Task update added successfully.", true);
              loadTasks();

              if (alwaysCallback) alwaysCallback();
            },
            error: function (err) {
              if (alwaysCallback) alwaysCallback();
              showTaskUpdateError(getErrorMessage(err));
            }
          });
        })
        .catch(function (err) {
          if (alwaysCallback) alwaysCallback();
          showTaskUpdateError(getErrorMessage(err));
        });
    },
    error: function (err) {
      if (alwaysCallback) alwaysCallback();
      showTaskUpdateError(getErrorMessage(err));
    }
  });
}

  // ============================================================
  // TICKETS / ISSUES
  // ============================================================

  function submitTicket() {
    var branch = getValue("ticket-branch");
    var category = getValue("ticket-category");
    var issue = getValue("ticket-issue");
    var otherText = getValue("ticket-other-text");
    var employeeInvolved = getValue("ticket-employee-involved");
    var details = getValue("ticket-details");
    var tagTo = ticketTagTo[0] || "";
    var ccTo = ticketCcTo.slice();

    if (!category) {
      showModal("⚠️", "Category Required", "Please select issue category.");
      return;
    }

    if (!issue) {
      showModal("⚠️", "Issue Required", "Please select the specific issue.");
      return;
    }

    if (issue === "Other" && !otherText) {
      showModal("⚠️", "Issue Description Required", "Please describe the issue because you selected Other.");
      return;
    }

    if (EMPLOYEE_INVOLVED_ISSUES.indexOf(issue) !== -1 && !employeeInvolved) {
      showModal("⚠️", "Employee Required", "Please select the employee involved.");
      return;
    }

    if (!tagTo) {
      showModal("⚠️", "Resolver Required", "Please select Tag To Resolver.");
      return;
    }

    if (!details) {
      showModal("⚠️", "Details Required", "Please describe what happened.");
      return;
    }

    if (!selectedTicketPriority) {
      showModal("⚠️", "Priority Required", "Please select ticket priority.");
      return;
    }

    var meta = {
      branch: branch,
      category: category,
      issue: issue,
      other_text: otherText,
      employee_involved: employeeInvolved,
      tag_to: tagTo,
      cc_to: ccTo
    };

    var subject = category + " - " + issue;

    var doc = {
      doctype: "Issue",
      subject: subject,
      description: buildTicketDescription(details, meta),
      priority: selectedTicketPriority,
      status: "Open",
      raised_by: currentUser
    };
    
    var ticketFileValidation = validateAttachmentList(ticketFiles);

    if (!ticketFileValidation.ok) {
      showModal(
        "⚠️",
        "Invalid Attachment",
        "Please remove invalid ticket attachment(s):\n\n" + ticketFileValidation.message
      );
      return;
    }

    var btn = $("#ticket-submit-btn");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Submitting...";
    }

    frappe.call({
      method: "frappe.client.insert",
      args: {
        doc: doc
      },
      callback: function (r) {
        var saved = r.message || {};

        uploadFiles("Issue", saved.name, ticketFiles)
          .then(function () {
            showModal("✅", "Ticket Submitted", "Ticket " + saved.name + " has been submitted and tagged to " + userLabel(tagTo) + ".");
            resetTicketForm();
            loadTickets();

            if (btn) {
              btn.disabled = false;
              btn.textContent = "✓ Submit Ticket";
            }
          })
          .catch(function (err) {
            showModal("⚠️", "Ticket Saved, Attachment Failed", getErrorMessage(err));
            resetTicketForm();
            loadTickets();

            if (btn) {
              btn.disabled = false;
              btn.textContent = "✓ Submit Ticket";
            }
          });
      },
      error: function (err) {
        showModal("⚠️", "Ticket Save Failed", getErrorMessage(err));

        if (btn) {
          btn.disabled = false;
          btn.textContent = "✓ Submit Ticket";
        }
      }
    });
  }

  function resetTicketForm() {
    setValue("ticket-category", "");
    setValue("ticket-issue", "");
    setValue("ticket-other-text", "");
    setValue("ticket-employee-involved", "");
    setValue("ticket-details", "");

    var issue = $("#ticket-issue");
    if (issue) issue.innerHTML = '<option value="">Select Category First</option>';

    var otherBlock = $("#ticket-other-block");
    var empBlock = $("#ticket-employee-involved-block");

    if (otherBlock) otherBlock.style.display = "none";
    if (empBlock) empBlock.style.display = "none";

    selectedTicketPriority = "";
    $all("#ticket-priority-grp .priority-chip").forEach(function (x) {
      x.classList.remove("sel");
    });

    ticketTagTo = [];
    ticketCcTo = [];
    renderPickerChips("ticketTagTo");
    renderPickerChips("ticketCcTo");

    ticketFiles = [];
    renderSelectedFiles("ticket");
  }

function loadTickets() {
  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "Issue",
      fields: [
        "name",
        "subject",
        "description",
        "priority",
        "status",
        "owner",
        "raised_by",
        "opening_date",
        "creation",
        "modified"
      ],
      order_by: "modified desc",
      limit_page_length: 500
    },
    callback: function (r) {
      tickets = (r.message || []).filter(isTicketVisibleToCurrentUser);

      loadAttachmentCache(
        "Issue",
        tickets.map(function (t) { return t.name; }),
        function () {
          renderTicketReport();
          renderMyTickets();
          renderCounts();
        }
      );
    },
    error: function () {
      tickets = [];
      renderTicketReport();
      renderMyTickets();
      renderCounts();
    }
  });
}


function getTicketMeta(ticket) {
  var meta = parseMeta(ticket.description, "TICKET");

  if (
    meta &&
    (
      meta.branch ||
      meta.category ||
      meta.issue ||
      meta.tag_to ||
      (meta.cc_to && meta.cc_to.length)
    )
  ) {
    return meta;
  }

  var text = stripHtml(removeMeta(ticket.description || ""));

  var fallback = {};

  fallback.branch = extractLabelValue(text, "Branch", ["Category"]);
  fallback.category = extractLabelValue(text, "Category", ["Issue"]);
  fallback.issue = extractLabelValue(text, "Issue", ["Tagged To", "Tag To", "CC To", "Details"]);
  fallback.other_text = extractLabelValue(text, "Other Issue", ["Employee Involved", "Tagged To", "CC To", "Details"]);
  fallback.employee_involved = extractLabelValue(text, "Employee Involved", ["Tagged To", "CC To", "Details"]);

  var tagToText =
    extractLabelValue(text, "Tagged To", ["CC To", "Details"]) ||
    extractLabelValue(text, "Tag To", ["CC To", "Details"]);

  var ccToText = extractLabelValue(text, "CC To", ["Details"]);

  fallback.tag_to = resolveUserValue(tagToText);

  fallback.cc_to = ccToText
    ? ccToText.split(",").map(function (x) {
        return resolveUserValue(x);
      }).filter(Boolean)
    : [];

  return fallback;
}

function renderTicketActionButtons(t) {
  var meta = getTicketMeta(t);

  if (t.status === "Closed") {
    return "—";
  }

  if (t.status === "Resolved") {
    if (isTicketRaiser(t)) {
      return '' +
        '<div class="life-action-stack">' +
          '<button class="btn btn-g btn-sm ticket-close-btn" data-name="' + esc(t.name) + '">' +
            'Close Ticket' +
          '</button>' +
          '<button class="btn btn-undo btn-sm ticket-reopen-btn" data-name="' + esc(t.name) + '">' +
            'Reopen Ticket' +
          '</button>' +
        '</div>';
    }

    return '<span class="pill p-o">Waiting for Raiser Review</span>';
  }

  if (isTicketResolver(t, meta)) {
    return '' +
      '<button class="btn btn-g btn-sm ticket-resolve-btn" data-name="' + esc(t.name) + '">' +
        'Resolve Ticket' +
      '</button>';
  }

  return "—";
}


function bindTicketActionButtons(scope) {
  (scope || root).querySelectorAll(".ticket-resolve-btn").forEach(function (btn) {
    if (btn.dataset.boundTicketResolve === "1") return;

    btn.dataset.boundTicketResolve = "1";

    btn.addEventListener("click", function () {
      markTicketResolved(btn.dataset.name);
    });
  });

  (scope || root).querySelectorAll(".ticket-close-btn").forEach(function (btn) {
    if (btn.dataset.boundTicketClose === "1") return;

    btn.dataset.boundTicketClose = "1";

    btn.addEventListener("click", function () {
      closeTicketAfterReview(btn.dataset.name);
    });
  });

  (scope || root).querySelectorAll(".ticket-reopen-btn").forEach(function (btn) {
    if (btn.dataset.boundTicketReopen === "1") return;

    btn.dataset.boundTicketReopen = "1";

    btn.addEventListener("click", function () {
      reopenTicketAfterReview(btn.dataset.name);
    });
  });
}


function markTicketResolved(name) {
  promptWorkflowRemarks(
    "Resolve Ticket",
    "Resolution Remarks *",
    100,
    function (remarks) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "Issue",
          name: name
        },
        callback: function (r) {
          var doc = r.message;

          if (!doc) {
            showModal("⚠️", "Ticket Not Found", "Unable to load ticket.");
            return;
          }

          var meta = getTicketMeta(doc);
          var details = getTicketDetails(doc);

          meta.workflow_state = "Resolved";
          meta.resolved_on = getNowLocalDateTime();
          meta.resolved_by = currentUser;
          meta.resolved_by_name = currentUserFullName || currentUser;
          meta.resolution_remarks = remarks;

          meta.resolution_history = meta.resolution_history || [];
          meta.resolution_history.push({
            by: currentUser,
            by_name: currentUserFullName || currentUser,
            on: meta.resolved_on,
            remarks: remarks
          });

          doc.status = "Resolved";
          doc.description = buildTicketDescription(details, meta);

          frappe.call({
            method: "frappe.client.save",
            args: {
              doc: doc
            },
            callback: function () {
              toast("Ticket resolved and sent for raiser review.", true);
              loadTickets();
            },
            error: function (err) {
              showModal("⚠️", "Resolve Failed", getErrorMessage(err));
            }
          });
        },
        error: function (err) {
          showModal("⚠️", "Ticket Load Failed", getErrorMessage(err));
        }
      });
    }
  );
}

function closeTicketAfterReview(name) {
  frappe.confirm(
    "Are you satisfied with this ticket resolution and want to close it?",
    function () {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "Issue",
          name: name
        },
        callback: function (r) {
          var doc = r.message;

          if (!doc) {
            showModal("⚠️", "Ticket Not Found", "Unable to load ticket.");
            return;
          }

          var meta = getTicketMeta(doc);
          var details = getTicketDetails(doc);

          meta.workflow_state = "Closed";
          meta.closed_on = getNowLocalDateTime();
          meta.closed_by = currentUser;
          meta.closed_by_name = currentUserFullName || currentUser;

          meta.close_history = meta.close_history || [];
          meta.close_history.push({
            by: currentUser,
            by_name: currentUserFullName || currentUser,
            on: meta.closed_on,
            remarks: "Accepted and closed by ticket raiser."
          });

          doc.status = "Closed";
          doc.description = buildTicketDescription(details, meta);

          frappe.call({
            method: "frappe.client.save",
            args: {
              doc: doc
            },
            callback: function () {
              toast("Ticket closed successfully.", true);
              loadTickets();
            },
            error: function (err) {
              showModal("⚠️", "Close Failed", getErrorMessage(err));
            }
          });
        },
        error: function (err) {
          showModal("⚠️", "Ticket Load Failed", getErrorMessage(err));
        }
      });
    }
  );
}

function reopenTicketAfterReview(name) {
  promptWorkflowRemarks(
    "Reopen Ticket",
    "Review Remarks *",
    100,
    function (remarks) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "Issue",
          name: name
        },
        callback: function (r) {
          var doc = r.message;

          if (!doc) {
            showModal("⚠️", "Ticket Not Found", "Unable to load ticket.");
            return;
          }

          var meta = getTicketMeta(doc);
          var details = getTicketDetails(doc);

          meta.workflow_state = "Reopened";
          meta.reopened_on = getNowLocalDateTime();
          meta.reopened_by = currentUser;
          meta.reopened_by_name = currentUserFullName || currentUser;
          meta.reopen_review_remarks = remarks;

          meta.reopen_history = meta.reopen_history || [];
          meta.reopen_history.push({
            by: currentUser,
            by_name: currentUserFullName || currentUser,
            on: meta.reopened_on,
            remarks: remarks
          });

          doc.status = "Open";
          doc.description = buildTicketDescription(details, meta);

          frappe.call({
            method: "frappe.client.save",
            args: {
              doc: doc
            },
            callback: function () {
              toast("Ticket reopened successfully.", true);
              loadTickets();
            },
            error: function (err) {
              showModal("⚠️", "Reopen Failed", getErrorMessage(err));
            }
          });
        },
        error: function (err) {
          showModal("⚠️", "Ticket Load Failed", getErrorMessage(err));
        }
      });
    }
  );
}



function getTicketDetails(ticket) {
  var text = htmlToReadableText(removeMeta(ticket.description || ""));

  var detailsOnly = extractLabelValue(text, "Details", []);

  return detailsOnly || text;
}

function getTicketStatus(t) {
  var meta = getTicketMeta(t);

  if (t.status === "Closed") {
    return "Closed";
  }

  if (t.status === "Resolved") {
    return "Resolved";
  }

  if (meta.workflow_state === "Reopened" && t.status === "Open") {
    return "Reopened";
  }

  return t.status || "Open";
}



function renderTicketReport() {
  var body = $("#ticket-report-body");
  if (!body) return;

  var catF = getValue("ticr-category");
  var priF = getValue("ticr-priority");
  var statF = getValue("ticr-status");

  var filtered = tickets.filter(function (t) {
    var meta = getTicketMeta(t);

    return (
      (!catF || meta.category === catF) &&
      (!priF || t.priority === priF) &&
      (!statF || getTicketStatus(t) === statF)
    );
  });

  renderTicketTiles();

  setText("ticket-report-count", String(filtered.length));
  filtered = sortByModifiedLatest(filtered);
  var pageData = getPaginatedRows("ticketReport", filtered);

  if (!filtered.length) {
    body.innerHTML =
      '<tr><td colspan="10" style="text-align:center;color:#8C8C8C;padding:18px">No tickets found.</td></tr>';
    return;
  }

  body.innerHTML = pageData.rows.map(function (t) {
    var meta = getTicketMeta(t);

    var detailId = registerDetailHtml(
      "Ticket Details - " + t.name,
      buildTicketDetailsHtml(t, meta),
        buildTicketWorkflowHistorySection(meta)
    );

    return '' +
      '<tr class="life-clickable-row" ' +
        'data-detail-html-id="' + esc(detailId) + '" ' +
        'data-doctype="Issue" ' +
        'data-docname="' + esc(t.name) + '">' +

        '<td>' +
          '<div class="life-user-date-cell">' +
            '<div class="life-user-name">' +
              esc(userDisplayName(t.raised_by || t.owner)) +
            '</div>' +
            '<div class="life-user-date">' +
              esc(formatLifeDate(t.opening_date || t.creation)) +
            '</div>' +
          '</div>' +
        '</td>' +

        '<td>' + esc(meta.branch || "—") + '</td>' +

        '<td>' + esc(meta.category || "—") + '</td>' +

        '<td style="max-width:260px;white-space:normal">' +
          '<div class="life-row-main-text">' +
            esc(shortPreviewText(meta.issue || t.subject || "—", 110)) +
          '</div>' +
        '</td>' +

        '<td>' + esc(userDisplayName(meta.tag_to || "")) + '</td>' +

        '<td style="max-width:160px;white-space:normal">' +
          esc((meta.cc_to || []).map(userDisplayName).join(", ") || "—") +
        '</td>' +

        '<td>' + priorityPill(t.priority) + '</td>' +

        '<td>' + attachmentChip("Issue", t.name) + '</td>' +

        '<td>' + statusPill(getTicketStatus(t)) + '</td>' +

        '<td>' + renderTicketActionButtons(t) + '</td>' +

      '</tr>';
  }).join("");

  bindTicketActionButtons(body);
  bindAttachmentChips(body);
  bindClickableTicketRows(body);
  renderTablePagination(body, "ticketReport", pageData, renderTicketReport);
}

function renderTicketTiles() {
  var box = $("#ticket-tiles");
  if (!box) return;

  var total = tickets.length;

  var open = tickets.filter(function (t) {
    var status = getTicketStatus(t);
    return status === "Open" || status === "Reopened";
  }).length;

  var reviewPending = tickets.filter(function (t) {
    return getTicketStatus(t) === "Resolved";
  }).length;

  var closed = tickets.filter(function (t) {
    return getTicketStatus(t) === "Closed";
  }).length;

  box.innerHTML = [
    { l: "Total Tickets", v: total, c: "t-pn" },
    { l: "Open / Reopened", v: open, c: "t-po" },
    { l: "Review Pending", v: reviewPending, c: "t-pgr" },
    { l: "Closed", v: closed, c: "t-pg" }
  ].map(function (x) {
    return '<div class="tile ' + x.c + '"><div class="tl">' + esc(x.l) + '</div><div class="tv">' + esc(x.v) + '</div></div>';
  }).join("");
}


function renderMyTickets() {
  var toBody = $("#myticket-tome-body");
  var byBody = $("#myticket-byme-body");

  if (!toBody || !byBody) return;

  var toMe = tickets.filter(function (t) {
    var meta = getTicketMeta(t);

    return (
      isCurrentUserValue(meta.tag_to) ||
      (meta.cc_to || []).some(isCurrentUserValue)
    );
  });

  var byMe = tickets.filter(function (t) {
    return (
      t.owner === currentUser ||
      t.raised_by === currentUser ||
      userDisplayName(t.owner) === currentUserFullName ||
      userDisplayName(t.raised_by) === currentUserFullName
    );
  });

  setText("myticket-tome-count", String(toMe.length));
  setText("myticket-byme-count", String(byMe.length));
  toMe = sortByModifiedLatest(toMe);
    byMe = sortByModifiedLatest(byMe);
  var toMePageData = getPaginatedRows("myTicketToMe", toMe);
  var byMePageData = getPaginatedRows("myTicketByMe", byMe);

  // ============================================================
  // Tagged To Me / CC'd To Me
  // New columns:
  // From | Issue | Priority | Status | Action
  // Row click opens ticket details
  // ============================================================

  toBody.innerHTML = toMe.length
    ? toMePageData.rows.map(function (t) {
        var meta = getTicketMeta(t);

        var detailId = registerDetailHtml(
          "Ticket Details - " + t.name,
          buildTicketDetailsHtml(t, meta),
            buildTicketWorkflowHistorySection(meta)
        );

        return '' +
          '<tr class="life-clickable-row" ' +
          'data-detail-html-id="' + esc(detailId) + '" ' +
          'data-doctype="Issue" ' +
          'data-docname="' + esc(t.name) + '">' +

            '<td>' +
              '<div class="life-user-date-cell">' +
                '<div class="life-user-name">' +
                  esc(userDisplayName(t.raised_by || t.owner)) +
                '</div>' +
                '<div class="life-user-date">' +
                  esc(formatLifeDate(t.opening_date || t.creation)) +
                '</div>' +
              '</div>' +
            '</td>' +

            '<td>' +
              '<div class="life-row-main-text">' +
                esc(shortPreviewText(meta.issue || t.subject || "—", 90)) +
              '</div>' +
            '</td>' +

            '<td>' + priorityPill(t.priority) + '</td>' +

            '<td>' + statusPill(getTicketStatus(t)) + '</td>' +

            '<td>' + renderTicketActionButtons(t) + '</td>' +

          '</tr>';
      }).join("")
    : '<tr><td colspan="5" style="text-align:center;color:#8C8C8C;padding:14px">No tickets tagged to you.</td></tr>';

  // ============================================================
  // Raised By Me
  // New columns:
  // Issue | Tag To | Priority | Status
  // Row click opens ticket details
  // ============================================================

  byBody.innerHTML = byMe.length
    ? byMePageData.rows.map(function (t) {
        var meta = getTicketMeta(t);

        var detailId = registerDetailHtml(
          "Ticket Details - " + t.name,
          buildTicketDetailsHtml(t, meta),
            buildTicketWorkflowHistorySection(meta)
        );

        return '' +
          '<tr class="life-clickable-row" ' +
          'data-detail-html-id="' + esc(detailId) + '" ' +
          'data-doctype="Issue" ' +
          'data-docname="' + esc(t.name) + '">' +

            '<td>' +
              '<div class="life-row-main-text">' +
                esc(shortPreviewText(meta.issue || t.subject || "—", 110)) +
              '</div>' +
            '</td>' +

            '<td>' + esc(userDisplayName(meta.tag_to || "")) + '</td>' +

            '<td>' + priorityPill(t.priority) + '</td>' +

           '<td>' + statusPill(getTicketStatus(t)) + '</td>' +

            '<td>' + renderTicketActionButtons(t) + '</td>' +
            
            '</tr>';
      }).join("")
    : '<tr><td colspan="5" style="text-align:center;color:#8C8C8C;padding:14px">You have not raised any tickets.</td></tr>';

  bindTicketActionButtons(toBody);
  bindTicketActionButtons(byBody);

  bindClickableTicketRows(toBody);
  bindClickableTicketRows(byBody);
  
  renderTablePagination(toBody, "myTicketToMe", toMePageData, renderMyTickets);
renderTablePagination(byBody, "myTicketByMe", byMePageData, renderMyTickets);
}

function bindClickableTicketRows(scope) {
  (scope || root).querySelectorAll(".life-clickable-row").forEach(function (row) {
    if (row.dataset.boundClickableRow === "1") return;

    row.dataset.boundClickableRow = "1";

    row.addEventListener("click", function (e) {
      if (
        e.target.closest("button") ||
        e.target.closest("a") ||
        e.target.closest(".btn") ||
        e.target.closest("input") ||
        e.target.closest("select") ||
        e.target.closest("textarea") ||
        e.target.closest(".attach-chip-table")
      ) {
        return;
      }

      var id = row.dataset.detailHtmlId || "";
      var detail = detailHtmlRegistry[id] || {};

      var doctype = row.dataset.doctype || "Issue";
      var docname = row.dataset.docname || "";

      var html =
        (detail.html || "") +
        (docname ? modalAttachmentHtml(doctype, docname) : "") +
        (detail.afterHtml || "");

      showRichModal("📄", detail.title || "Ticket Details", html);
    });
  });
}


  // ============================================================
  // COUNTS
  // ============================================================

  function renderCounts() {
    var taskPending = tasks.filter(function (t) {
      var status = getTaskStatus(t);
    
      return (
        t.allocated_to === currentUser &&
        status !== "Completed" &&
        status !== "Closed" &&
        status !== "Cancelled"
      );
    }).length;

    var ticketPending = tickets.filter(function (t) {
      var meta = getTicketMeta(t);
      return (
        (isCurrentUserValue(meta.tag_to) || (meta.cc_to || []).some(isCurrentUserValue)) &&
        t.status !== "Resolved" &&
        t.status !== "Closed"
      );
    }).length;

    setText("task-pending-cnt", String(taskPending));
    setText("ticket-pending-cnt", String(ticketPending));
  }
  
  /* ============================================================
   TASK QUEUE NUMBER PATCH
   Paste above init();
   Uses custom_task_queue_no, custom_queue_active,
   custom_queue_updated_by, custom_queue_updated_on, custom_completed_on
   ============================================================ */

function queueNow() {
  var v = getNowReadableDateTime ? getNowReadableDateTime() : "";
  if (!v) {
    var d = new Date();
    var yyyy = d.getFullYear();
    var mm = String(d.getMonth() + 1).padStart(2, "0");
    var dd = String(d.getDate()).padStart(2, "0");
    var hh = String(d.getHours()).padStart(2, "0");
    var mi = String(d.getMinutes()).padStart(2, "0");
    v = yyyy + "-" + mm + "-" + dd + " " + hh + ":" + mi;
  }
  return v.length === 16 ? v + ":00" : v;
}

function qCall(method, args) {
  return new Promise(function (resolve, reject) {
    frappe.call({
      method: method,
      args: args || {},
      callback: function (r) {
        resolve(r.message);
      },
      error: function (err) {
        reject(err);
      }
    });
  });
}

function setTodoValues(name, values) {
  values.custom_queue_updated_by = currentUser;
  values.custom_queue_updated_on = queueNow();

  return qCall("frappe.client.set_value", {
    doctype: "ToDo",
    name: name,
    fieldname: values
  });
}

function getQueueNo(t) {
  return Number(t.custom_task_queue_no || 0);
}

function isTaskQueueActive(t) {
  var status = getTaskStatus(t);
  return ["Completed", "Closed", "Cancelled"].indexOf(status) === -1;
}

function queueNoHtml(t) {
  if (!isTaskQueueActive(t)) {
    return '<span class="life-queue-empty">—</span>';
  }

  var no = getQueueNo(t);

  if (!no) {
    return '<span class="life-queue-empty">Pending</span>';
  }

  return '<span class="life-queue-pill">#' + esc(no) + '</span>';
}

function sortQueueRows(rows) {
  return (rows || []).slice().sort(function (a, b) {
    var aq = getQueueNo(a) || 999999;
    var bq = getQueueNo(b) || 999999;

    if (aq !== bq) return aq - bq;

    return getModifiedTime(a) - getModifiedTime(b);
  });
}

function fetchAssigneeQueue(assignee) {
  return qCall("frappe.client.get_list", {
    doctype: "ToDo",
    fields: [
      "name",
      "description",
      "allocated_to",
      "assigned_by",
      "priority",
      "status",
      "date",
      "creation",
      "modified",
      "owner",
      "custom_task_queue_no",
      "custom_queue_active",
      "custom_queue_updated_by",
      "custom_queue_updated_on",
      "custom_completed_on"
    ],
    filters: {
      allocated_to: assignee
    },
    order_by: "custom_task_queue_no asc, modified asc",
    limit_page_length: 500
  }).then(function (rows) {
    rows = rows || [];

    rows = rows.filter(function (t) {
      return isTaskQueueActive(t);
    });

    return sortQueueRows(rows);
  });
}

function saveQueueOrder(assignee, orderedNames) {
  var now = queueNow();

  var chain = Promise.resolve();

  orderedNames.forEach(function (name, idx) {
    name = typeof name === 'string' ? name : name && name.name;
    if (!name) throw new Error('A task document name is required to reorder the queue.');
    chain = chain.then(function () {
      return setTodoValues(name, {
        custom_task_queue_no: idx + 1,
        custom_queue_active: 1,
        custom_queue_updated_by: currentUser,
        custom_queue_updated_on: now
      });
    });
  });

  return chain;
}

function rebuildQueueForAssignee(assignee) {
  if (!assignee) return Promise.resolve();

  return qCall("frappe.client.get_list", {
    doctype: "ToDo",
    fields: [
      "name",
      "description",
      "allocated_to",
      "assigned_by",
      "priority",
      "status",
      "date",
      "creation",
      "modified",
      "owner",
      "custom_task_queue_no",
      "custom_queue_active",
      "custom_completed_on"
    ],
    filters: {
      allocated_to: assignee
    },
    order_by: "custom_task_queue_no asc, modified asc",
    limit_page_length: 500
  }).then(function (rows) {
    rows = rows || [];

    var active = [];
    var inactive = [];

    rows.forEach(function (t) {
      if (isTaskQueueActive(t)) active.push(t);
      else inactive.push(t);
    });

    active = sortQueueRows(active);

    var chain = Promise.resolve();

    inactive.forEach(function (t) {
      chain = chain.then(function () {
        return setTodoValues(t.name, {
          custom_task_queue_no: 0,
          custom_queue_active: 0
        });
      });
    });

    return chain.then(function () {
      return saveQueueOrder(
        assignee,
        active.map(function (t) { return t.name; })
      );
    });
  });
}

function normalizeRequestedQueueNo(value, maxAllowed) {
  var no = Number(value || 0);

  if (!no || no < 1) no = maxAllowed;
  if (no > maxAllowed) no = maxAllowed;

  return no;
}

function refreshTaskQueueDefault() {
  var assignee = taskAssignTo[0] || "";
  var input = $("#task-queue-no");
  var help = $("#task-queue-help");

  if (!input) return;

  if (!assignee) {
    input.value = "";
    if (help) help.textContent = "Select an assignee to auto-calculate the running task number.";
    return;
  }

  if (help) help.textContent = "Checking current running tasks...";

  fetchAssigneeQueue(assignee)
    .then(function (queue) {
      var nextNo = queue.length + 1;
      input.value = nextNo;

      if (help) {
        help.textContent =
          queue.length
            ? userDisplayName(assignee) + " has " + queue.length + " running task(s). New task will be #" + nextNo + " by default."
            : userDisplayName(assignee) + " has no running tasks. New task will be #1.";
      }
    })
    .catch(function () {
      if (help) help.textContent = "Unable to calculate queue number. It will be assigned on submit.";
    });
}

function createTaskWithQueue(doc, requestedQueueNo) {
  var assignee = doc.allocated_to;

  return fetchAssigneeQueue(assignee).then(function (queueBefore) {
    var maxAllowed = queueBefore.length + 1;
    var finalNo = normalizeRequestedQueueNo(requestedQueueNo, maxAllowed);

    doc.custom_task_queue_no = finalNo;
    doc.custom_queue_active = 1;
    doc.custom_queue_updated_by = currentUser;
    doc.custom_queue_updated_on = queueNow();

    return qCall("frappe.client.insert", {
      doc: doc
    }).then(function (saved) {
      saved = saved || {};

      return fetchAssigneeQueue(assignee).then(function (queueAfter) {
        queueAfter = queueAfter.filter(function (t) {
          return t.name !== saved.name;
        });

        queueAfter = sortQueueRows(queueAfter);
        queueAfter.splice(finalNo - 1, 0, saved);

        return saveQueueOrder(
          assignee,
          queueAfter.map(function (t) { return t.name; }),
          "New task inserted into running queue."
        ).then(function () {
          return saved;
        });
      });
    });
  });
}

/* ------------------------------------------------------------
   Inject queue field and manage button into existing HTML
   ------------------------------------------------------------ */

function ensureTaskQueueUI() {
  if (!$("#task-queue-no")) {
    var priorityBlock = $("#task-priority-grp")
      ? $("#task-priority-grp").closest(".field-block")
      : null;

    if (priorityBlock) {
      priorityBlock.insertAdjacentHTML(
        "afterend",
        '' +
        '<div class="field-block" id="task-queue-block">' +
          '<label class="lbl">Task Number <span class="required-mark">*</span></label>' +
          '<input type="number" id="task-queue-no" min="1" placeholder="Auto">' +
          '<div class="life-queue-help" id="task-queue-help">' +
            'Select an assignee to auto-calculate the running task number.' +
          '</div>' +
        '</div>'
      );
    }
  }

  if (!$("#life-manage-queue-btn")) {
    var fbar = $("#task-sub-1 .fbar");

    if (fbar) {
      fbar.insertAdjacentHTML(
        "beforeend",
        '<button type="button" class="apbtn life-manage-queue-btn" id="life-manage-queue-btn">↕ Manage Assignee Queue</button>'
      );
    }
  }

  if ($("#life-manage-queue-btn") && !$("#life-manage-queue-btn").dataset.boundQueueManage) {
    $("#life-manage-queue-btn").dataset.boundQueueManage = "1";
    $("#life-manage-queue-btn").addEventListener("click", openManageQueuePrompt);
  }

  addQueueHeader("#task-report-body", "Task No");
  addQueueHeader("#mytask-to-body", "Task No");
  addQueueHeader("#mytask-by-body", "Task No");
}

function addQueueHeader(bodySelector, label) {
  var body = $(bodySelector);
  if (!body) return;

  var table = body.closest("table");
  if (!table) return;

  var tr = table.querySelector("thead tr");
  if (!tr) return;

  if (tr.querySelector(".life-queue-th")) return;

  tr.insertAdjacentHTML("afterbegin", '<th class="life-queue-th">' + esc(label) + '</th>');
}

/* ------------------------------------------------------------
   Keep default queue number updated when assignee is selected
   ------------------------------------------------------------ */

var oldRenderPickerChipsForQueue = renderPickerChips;

renderPickerChips = function (key) {
  oldRenderPickerChipsForQueue(key);

  if (key === "taskAssignTo") {
    refreshTaskQueueDefault();
  }
};

/* ------------------------------------------------------------
   Replace loadTasks to include queue fields
   ------------------------------------------------------------ */

loadTasks = function () {
  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "ToDo",
      fields: [
        "name",
        "description",
        "allocated_to",
        "assigned_by",
        "priority",
        "status",
        "date",
        "creation",
        "modified",
        "owner",
        "custom_task_queue_no",
        "custom_queue_active",
        "custom_queue_updated_by",
        "custom_queue_updated_on",
        "custom_completed_on"
      ],
      order_by: "modified desc",
      limit_page_length: 500
    },
    callback: function (r) {
      tasks = (r.message || []).filter(isTaskVisibleToCurrentUser);

      loadAttachmentCache(
        "ToDo",
        tasks.map(function (t) { return t.name; }),
        function () {
          renderTaskReport();
          renderMyTasks();
          renderCounts();
        }
      );
    },
    error: function () {
      tasks = [];
      renderTaskReport();
      renderMyTasks();
      renderCounts();
    }
  });
};

/* ------------------------------------------------------------
   Replace submitTask to create task with queue shifting
   ------------------------------------------------------------ */

submitTask = function () {
  var assignTo = taskAssignTo[0] || "";
  var category = getValue("task-category");
  var startDate = getValue("task-startdate");
  var deadlineDateTime = getValue("task-deadline");
  var deadline = getDatePartFromDateTime(deadlineDateTime);
  var details = getValue("task-details");
  var requestedQueueNo = Number(getValue("task-queue-no") || 0);

  if (!assignTo) {
    showModal("⚠️", "Select Assignee", "Please search and select who this task is being assigned to.");
    return;
  }

  if (!category) {
    showModal("⚠️", "Category Required", "Please select a task category.");
    return;
  }

  var dateValidation = validateTaskDatesBeforeSubmit(startDate, deadlineDateTime);

  if (!dateValidation.ok) {
    showModal("⚠️", "Invalid Task Dates", dateValidation.message);
    return;
  }

  if (!details) {
    showModal("⚠️", "Details Required", "Please enter task details.");
    return;
  }

  if (wordCount(details) > 100) {
    showModal("⚠️", "Too Many Words", "Task details cannot exceed 100 words.");
    return;
  }

  if (!selectedTaskPriority) {
    showModal("⚠️", "Priority Required", "Please select task priority.");
    return;
  }

  var taskFileValidation = validateAttachmentList(taskFiles);

  if (!taskFileValidation.ok) {
    showModal(
      "⚠️",
      "Invalid Attachment",
      "Please remove invalid task attachment(s):\n\n" + taskFileValidation.message
    );
    return;
  }

  var updateTo = taskUpdateTo.slice();

  if (updateTo.indexOf(currentUser) === -1) {
    updateTo.push(currentUser);
  }

  var meta = {
    category: category,
    start_date: startDate,
    deadline_datetime: deadlineDateTime,
    duration_label: calculateTaskDurationDays(startDate, deadlineDateTime),
    update_to: updateTo
  };

  var doc = {
    doctype: "ToDo",
    description: buildTaskDescription(details, meta),
    allocated_to: assignTo,
    assigned_by: currentUser,
    priority: selectedTaskPriority,
    status: "Open",
    date: deadline
  };

  var btn = $("#task-submit-btn");

  function finalSubmit() {
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Assigning...";
    }

    createTaskWithQueue(doc, requestedQueueNo)
      .then(function (saved) {
        return uploadFiles("ToDo", saved.name, taskFiles).then(function () {
          showModal(
            "✅",
            "Task Assigned",
            "Task " + saved.name + " assigned to " + userLabel(assignTo) + " as Task #" + getValue("task-queue-no") + "."
          );

          resetTaskForm();

          if ($("#task-queue-no")) {
            $("#task-queue-no").value = "";
          }

          loadTasks();

          if (btn) {
            btn.disabled = false;
            btn.textContent = "✓ Assign Task";
          }
        }).catch(function (err) {
          showModal("⚠️", "Task Saved, Attachment Failed", getErrorMessage(err));
          resetTaskForm();
          loadTasks();

          if (btn) {
            btn.disabled = false;
            btn.textContent = "✓ Assign Task";
          }
        });
      })
      .catch(function (err) {
        showModal("⚠️", "Task Save Failed", getErrorMessage(err));

        if (btn) {
          btn.disabled = false;
          btn.textContent = "✓ Assign Task";
        }
      });
  }

  fetchAssigneeQueue(assignTo)
    .then(function (queue) {
      var maxAllowed = queue.length + 1;
      requestedQueueNo = normalizeRequestedQueueNo(requestedQueueNo, maxAllowed);

      if ($("#task-queue-no")) {
        $("#task-queue-no").value = requestedQueueNo;
      }

      if (requestedQueueNo === 1 && queue.length > 0) {
        var confirmed = window.confirm(
          "This will place the new task as #1 for " +
            userDisplayName(assignTo) +
            ". Existing running tasks will move down by one number. Continue?"
        );

        if (confirmed) {
          finalSubmit();
        }
      } else {
        finalSubmit();
      }
    })
    .catch(function (err) {
      showModal("⚠️", "Queue Check Failed", getErrorMessage(err));
    });
};

/* ------------------------------------------------------------
   Reset queue field also
   ------------------------------------------------------------ */

var oldResetTaskFormForQueue = resetTaskForm;

resetTaskForm = function () {
  oldResetTaskFormForQueue();

  if ($("#task-queue-no")) $("#task-queue-no").value = "";
  if ($("#task-queue-help")) {
    $("#task-queue-help").textContent =
      "Select an assignee to auto-calculate the running task number.";
  }
};

/* ------------------------------------------------------------
   Add Edit Queue button to existing task actions
   ------------------------------------------------------------ */

var oldRenderTaskActionButtonsForQueue = renderTaskActionButtons;

renderTaskActionButtons = function (t) {
  var originalHtml = oldRenderTaskActionButtonsForQueue(t);
  var status = getTaskStatus(t);

  if (
    isTaskQueueActive(t) &&
    (isTaskAssigner(t) || isManager)
  ) {
    var editBtn =
      '<button class="btn btn-review btn-sm task-edit-queue-btn" data-name="' + esc(t.name) + '">' +
        'Edit No' +
      '</button>';

    if (!originalHtml || originalHtml === "—") {
      return '<div class="life-action-stack">' + editBtn + '</div>';
    }

    if (originalHtml.indexOf("life-action-stack") !== -1) {
      return originalHtml.replace("</div>", editBtn + "</div>");
    }

    return '<div class="life-action-stack">' + originalHtml + editBtn + '</div>';
  }

  return originalHtml;
};

var oldBindTaskActionButtonsForQueue = bindTaskActionButtons;

bindTaskActionButtons = function (scope) {
  oldBindTaskActionButtonsForQueue(scope);

  (scope || root).querySelectorAll(".task-edit-queue-btn").forEach(function (btn) {
    if (btn.dataset.boundQueueEdit === "1") return;

    btn.dataset.boundQueueEdit = "1";

    btn.addEventListener("click", function () {
      openEditTaskQueueModal(btn.dataset.name);
    });
  });
};

function openEditTaskQueueModal(name) {
  var task = tasks.find(function (t) {
    return t.name === name;
  });

  if (!task) {
    showModal(
      "⚠️",
      "Task Not Found",
      "Unable to find this task."
    );
    return;
  }

  if (!isTaskQueueActive(task)) {
    showModal(
      "⚠️",
      "Not Allowed",
      "Completed, closed, and cancelled tasks are not part of the running queue."
    );
    return;
  }

  if (!(isTaskAssigner(task) || isManager)) {
    showModal(
      "⚠️",
      "Not Allowed",
      "Only the assigner or manager can change task numbers."
    );
    return;
  }

  ensureManageQueueWebStyles();
  closeManageQueueWebModal();

  var currentNo = getQueueNo(task) || 1;

  var overlay = document.createElement("div");
  overlay.id = "life-web-queue-overlay";
  overlay.className = "life-web-queue-overlay";

  overlay.innerHTML =
    '<div class="life-web-queue-dialog" style="width:470px;" role="dialog" aria-modal="true">' +

      '<div class="life-web-queue-head">' +
        '<div class="life-web-queue-title">Change Task Number</div>' +
        '<button type="button" class="life-web-queue-close" id="life-web-edit-q-close">&times;</button>' +
      '</div>' +

      '<div class="life-web-queue-body">' +
        '<div class="life-web-queue-note">' +
          'Change the running task number for <strong>' +
            esc(shortPreviewText(getTaskDetails(task) || task.name, 90)) +
          '</strong>.' +
        '</div>' +

        '<label style="' +
          'display:block;margin-bottom:6px;color:#0F3D1E;' +
          'font-size:9.5px;font-weight:800;text-transform:uppercase;">' +
          'New Task Number' +
        '</label>' +

        '<input type="number" min="1" id="life-web-edit-q-input" ' +
          'value="' + esc(currentNo) + '" class="life-web-queue-no" ' +
          'style="width:100%;max-width:160px;text-align:left;padding:0 10px;">' +
      '</div>' +

      '<div class="life-web-queue-foot">' +
        '<button type="button" class="life-web-queue-btn life-web-queue-cancel" ' +
          'id="life-web-edit-q-cancel">Cancel</button>' +
        '<button type="button" class="life-web-queue-btn life-web-queue-save" ' +
          'id="life-web-edit-q-save">Save</button>' +
      '</div>' +

    '</div>';

  document.body.appendChild(overlay);

  var input = overlay.querySelector("#life-web-edit-q-input");
  var closeBtn = overlay.querySelector("#life-web-edit-q-close");
  var cancelBtn = overlay.querySelector("#life-web-edit-q-cancel");
  var saveBtn = overlay.querySelector("#life-web-edit-q-save");

  function closeEdit() {
    closeManageQueueWebModal();
  }

  function saveEdit() {
    var newNo = Number(input ? input.value : 0);

    if (!Number.isFinite(newNo) || newNo < 1) {
      showModal(
        "⚠️",
        "Invalid Task Number",
        "Please enter a valid task number starting from 1."
      );
      return;
    }

    closeEdit();
    moveTaskInQueue(name, newNo);
  }

  if (closeBtn) closeBtn.addEventListener("click", closeEdit);
  if (cancelBtn) cancelBtn.addEventListener("click", closeEdit);
  if (saveBtn) saveBtn.addEventListener("click", saveEdit);

  if (input) {
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        saveEdit();
      }
    });

    window.setTimeout(function () {
      input.focus();
      input.select();
    }, 30);
  }

  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) closeEdit();
  });
}

function moveTaskInQueue(name, newNo) {
  qCall("frappe.client.get", {
    doctype: "ToDo",
    name: name
  }).then(function (doc) {
    if (!doc) {
      showModal("⚠️", "Task Not Found", "Unable to load task.");
      return;
    }

    if (!(isTaskAssigner(doc) || isManager)) {
      showModal("⚠️", "Not Allowed", "Only the assigner or manager can change task numbers.");
      return;
    }

    return fetchAssigneeQueue(doc.allocated_to).then(function (queue) {
      queue = queue.filter(function (t) {
        return t.name !== name;
      });

      var maxAllowed = queue.length + 1;
      var finalNo = normalizeRequestedQueueNo(newNo, maxAllowed);

      function applyMove() {
        queue.splice(finalNo - 1, 0, doc);

        return saveQueueOrder(
          doc.allocated_to,
          queue.map(function (t) { return t.name; }),
          "Task number manually changed."
        ).then(function () {
          toast("Task queue updated.", true);
          loadTasks();
        });
      }

      if (finalNo === 1 && queue.length > 0) {
        var confirmed = window.confirm(
          "This will move this task to #1. Existing running tasks for " +
            userDisplayName(doc.allocated_to) +
            " will move down. Continue?"
        );

        if (confirmed) {
          return applyMove();
        }

        return;
      } else {
        return applyMove();
      }
    });
  }).catch(function (err) {
    showModal("⚠️", "Queue Update Failed", getErrorMessage(err));
  });
}

/* ------------------------------------------------------------
   Manage full queue for one assignee
   ------------------------------------------------------------ */

function openManageQueuePrompt() {
  /*
    Web Page-safe replacement for frappe.prompt().
    Select an employee, then open that employee's running queue.
  */
  ensureManageQueueWebStyles();
  closeManageQueueWebModal();

  if (!users || !users.length) {
    loadUsers(function () {
      if (!users || !users.length) {
        showModal(
          "⚠️",
          "Employees Not Available",
          "Unable to load the employee/user list for Manage Assignee Queue."
        );
        return;
      }

      openManageQueuePrompt();
    });

    return;
  }

  var overlay = document.createElement("div");
  overlay.id = "life-web-queue-overlay";
  overlay.className = "life-web-queue-overlay";

  overlay.innerHTML =
    '<div class="life-web-queue-dialog life-web-assignee-picker-dialog" ' +
      'role="dialog" aria-modal="true" aria-labelledby="life-web-assignee-picker-title">' +

      '<div class="life-web-queue-head">' +
        '<div>' +
          '<div class="life-web-queue-title" id="life-web-assignee-picker-title">' +
            'Manage Assignee Queue' +
          '</div>' +
          '<div style="margin-top:3px;font-size:10.5px;font-weight:500;color:rgba(255,255,255,.74);">' +
            'Search and select an employee to manage their running task order.' +
          '</div>' +
        '</div>' +

        '<button type="button" class="life-web-queue-close" ' +
          'id="life-web-assignee-picker-close" aria-label="Close">&times;</button>' +
      '</div>' +

      '<div class="life-web-queue-body">' +
        '<div style="max-width:700px;margin:0 auto;">' +

          '<label style="' +
            'display:block;margin-bottom:6px;color:#0F3D1E;' +
            'font-size:9.5px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;">' +
            'Assignee / Employee' +
          '</label>' +

          '<div style="position:relative;">' +
            '<input type="text" id="life-web-assignee-search" ' +
              'placeholder="Search employee name or email..." autocomplete="off" ' +
              'style="' +
                'width:100%;height:40px;padding:0 12px;' +
                'border:1.5px solid #CFE1D2;border-radius:8px;' +
                'background:#FFFFFF;color:#152418;font-family:inherit;' +
                'font-size:12px;outline:none;">' +
          '</div>' +

          '<div id="life-web-assignee-results" style="' +
            'margin-top:8px;max-height:360px;overflow-y:auto;' +
            'background:#FFFFFF;border:1px solid #DCE9DE;border-radius:9px;">' +
          '</div>' +

        '</div>' +
      '</div>' +

      '<div class="life-web-queue-foot">' +
        '<button type="button" class="life-web-queue-btn life-web-queue-cancel" ' +
          'id="life-web-assignee-picker-cancel">Cancel</button>' +
      '</div>' +

    '</div>';

  document.body.appendChild(overlay);

  var input = overlay.querySelector("#life-web-assignee-search");
  var results = overlay.querySelector("#life-web-assignee-results");
  var closeBtn = overlay.querySelector("#life-web-assignee-picker-close");
  var cancelBtn = overlay.querySelector("#life-web-assignee-picker-cancel");

  function closePicker() {
    closeManageQueueWebModal();
  }

  function renderAssigneeResults(query) {
    query = String(query || "").trim().toLowerCase();

    var matches = (users || [])
      .filter(function (u) {
        var email = String(u.name || "");
        var name = String(u.full_name || "");
        var haystack = (name + " " + email).toLowerCase();

        return !query || haystack.indexOf(query) !== -1;
      })
      .slice(0, 40);

    if (!matches.length) {
      results.innerHTML =
        '<div style="padding:18px;text-align:center;color:#5F6F63;font-size:11.5px;">' +
          'No matching employee found.' +
        '</div>';
      return;
    }

    results.innerHTML = matches.map(function (u) {
      var name = u.full_name || u.name || "—";
      var email = u.name || "";

      return '' +
        '<button type="button" class="life-web-assignee-item" ' +
          'data-email="' + esc(email) + '" ' +
          'style="' +
            'width:100%;display:flex;align-items:center;gap:10px;' +
            'padding:10px 12px;text-align:left;cursor:pointer;' +
            'background:#FFFFFF;border:0;border-bottom:1px solid #EEF4EF;' +
            'font-family:inherit;">' +

          '<span style="' +
            'width:30px;height:30px;flex:0 0 auto;border-radius:50%;' +
            'display:inline-flex;align-items:center;justify-content:center;' +
            'background:#E8F5E9;color:#1B5E20;border:1px solid #A5D6A7;' +
            'font-size:10px;font-weight:800;">' +
            esc(initials(name)) +
          '</span>' +

          '<span style="min-width:0;">' +
            '<span style="' +
              'display:block;color:#0F3D1E;font-size:12px;font-weight:700;' +
              'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
              esc(name) +
            '</span>' +

            '<span style="' +
              'display:block;margin-top:2px;color:#5F6F63;font-size:10.5px;font-weight:500;' +
              'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
              esc(email) +
            '</span>' +
          '</span>' +

        '</button>';
    }).join("");

    results.querySelectorAll(".life-web-assignee-item").forEach(function (btn) {
      btn.addEventListener("mouseenter", function () {
        btn.style.background = "#F3FAF4";
      });

      btn.addEventListener("mouseleave", function () {
        btn.style.background = "#FFFFFF";
      });

      btn.addEventListener("click", function () {
        var assignee = String(btn.dataset.email || "").trim();

        if (!assignee) return;

        closePicker();
        openManageQueueDialog(assignee);
      });
    });
  }

  renderAssigneeResults("");

  if (input) {
    input.addEventListener("input", function () {
      renderAssigneeResults(input.value);
    });

    window.setTimeout(function () {
      input.focus();
    }, 30);
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", closePicker);
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", closePicker);
  }

  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) {
      closePicker();
    }
  });
}

function queuePriorityBadge(priority) {
  priority = String(priority || "—");

  var cls = "life-q-low";

  if (priority === "High") cls = "life-q-high";
  else if (priority === "Medium") cls = "life-q-medium";
  else if (priority === "Low") cls = "life-q-low";

  return '<span class="life-q-badge ' + cls + '">' + esc(priority) + '</span>';
}

function queueStatusBadge(status) {
  status = String(status || "—");

  var cls = "life-q-open";

  if (status === "Overdue") cls = "life-q-overdue";
  else if (status === "Completed" || status === "Closed") cls = "life-q-completed";
  else if (status === "Cancelled") cls = "life-q-cancelled";
  else cls = "life-q-open";

  return '<span class="life-q-badge ' + cls + '">' + esc(status) + '</span>';
}

function ensureManageQueueWebStyles() {
  if (document.getElementById("life-manage-queue-web-style")) return;

  var style = document.createElement("style");
  style.id = "life-manage-queue-web-style";
  style.textContent = `
    .life-web-queue-overlay {
      position: fixed;
      inset: 0;
      z-index: 1000005;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding: 38px 18px;
      overflow-y: auto;
      background: rgba(15, 61, 30, 0.58);
      font-family: Inter, "Segoe UI", Arial, sans-serif;
    }

    .life-web-queue-dialog {
      width: 980px;
      max-width: 96vw;
      max-height: 88vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: #FFFFFF;
      border: 1px solid #CFE1D2;
      border-radius: 14px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.28);
    }

    .life-web-queue-head {
      flex: 0 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 18px;
      color: #FFFFFF;
      background: linear-gradient(135deg, #0F3D1E 0%, #1B5E20 100%);
    }

    .life-web-queue-title {
      font-size: 15px;
      font-weight: 800;
      line-height: 1.3;
    }

    .life-web-queue-close {
      width: 30px;
      height: 30px;
      flex: 0 0 auto;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(255,255,255,0.35);
      border-radius: 50%;
      background: transparent;
      color: #FFFFFF;
      font-size: 20px;
      line-height: 1;
      cursor: pointer;
    }

    .life-web-queue-close:hover {
      background: rgba(255,255,255,0.12);
    }

    .life-web-queue-body {
      flex: 1 1 auto;
      min-height: 0;
      overflow: auto;
      padding: 18px 20px 10px;
      background: #F8FCF8;
    }

    .life-web-queue-note {
      margin-bottom: 15px;
      padding: 10px 13px;
      color: #14501F;
      background: #E8F5E9;
      border: 1px solid #B9DFBE;
      border-left: 4px solid #43A047;
      border-radius: 8px;
      font-size: 11.5px;
      font-weight: 600;
      line-height: 1.5;
    }

    .life-web-queue-table-wrap {
      width: 100%;
      overflow-x: auto;
      background: #FFFFFF;
      border: 1px solid #CFE1D2;
      border-radius: 10px;
    }

    .life-web-queue-table {
      width: 100%;
      min-width: 810px;
      border-collapse: collapse;
      table-layout: fixed;
      background: #FFFFFF;
    }

    .life-web-queue-table th {
      padding: 10px 12px;
      color: #14501F;
      background: #E8F5E9;
      border-right: 1px solid #C7DFC9;
      border-bottom: 2px solid #43A047;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.05em;
      text-align: left;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .life-web-queue-table th:last-child {
      border-right: 0;
    }

    .life-web-queue-table td {
      padding: 10px 12px;
      color: #26372A;
      background: #FFFFFF;
      border-right: 1px solid #E1ECE3;
      border-bottom: 1px solid #E5EFE6;
      font-size: 11.5px;
      vertical-align: middle;
    }

    .life-web-queue-table td:last-child {
      border-right: 0;
    }

    .life-web-queue-table tbody tr:nth-child(even) td {
      background: #F7FBF7;
    }

    .life-web-queue-no {
      width: 62px;
      height: 34px;
      padding: 0 7px;
      color: #0F3D1E;
      background: #FFFFFF;
      border: 1.5px solid #43A047;
      border-radius: 7px;
      outline: none;
      font-family: inherit;
      font-size: 13px;
      font-weight: 800;
      text-align: center;
    }

    .life-web-queue-no:focus {
      border-color: #1B5E20;
      box-shadow: 0 0 0 3px rgba(67,160,71,0.14);
    }

    .life-web-queue-task {
      color: #152418;
      font-size: 12px;
      font-weight: 600;
      line-height: 1.4;
      white-space: normal;
      word-break: break-word;
    }

    .life-web-queue-deadline {
      color: #35633D;
      font-size: 11px;
      font-weight: 600;
      line-height: 1.35;
      white-space: normal;
    }

    .life-web-queue-foot {
      flex: 0 0 auto;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 9px;
      padding: 13px 20px 16px;
      background: #FFFFFF;
      border-top: 1px solid #DCE9DE;
    }

    .life-web-queue-btn {
      min-width: 96px;
      height: 36px;
      padding: 0 16px;
      border-radius: 8px;
      font-family: inherit;
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
    }

    .life-web-queue-cancel {
      color: #35633D;
      background: #FFFFFF;
      border: 1px solid #CFE1D2;
    }

    .life-web-queue-cancel:hover {
      background: #F3FAF4;
    }

    .life-web-queue-save {
      color: #FFFFFF;
      background: linear-gradient(135deg, #2E7D32, #1B5E20);
      border: 1px solid #1B5E20;
    }

    .life-web-queue-save:hover {
      background: linear-gradient(135deg, #388E3C, #14501F);
    }

    .life-web-queue-save:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    @media (max-width: 700px) {
      .life-web-queue-overlay {
        padding: 18px 8px;
      }

      .life-web-queue-dialog {
        max-width: 99vw;
        max-height: 94vh;
      }

      .life-web-queue-body {
        padding: 12px;
      }

      .life-web-queue-foot {
        padding: 11px 12px;
      }
    }
  `;

  document.head.appendChild(style);
}

function closeManageQueueWebModal() {
  var overlay = document.getElementById("life-web-queue-overlay");

  if (overlay && overlay.parentNode) {
    overlay.parentNode.removeChild(overlay);
  }
}

function openManageQueueDialog(assignee) {
  assignee = String(assignee || "").trim();

  if (!assignee || assignee === "Unassigned") {
    showModal(
      "⚠️",
      "Assignee Required",
      "Unable to identify the assignee for this queue."
    );
    return;
  }

  ensureManageQueueWebStyles();
  closeManageQueueWebModal();

  fetchAssigneeQueue(assignee)
    .then(function (queue) {
      queue = queue || [];

      if (!queue.length) {
        showModal(
          "ℹ️",
          "No Running Tasks",
          userDisplayName(assignee) + " has no running tasks."
        );
        return;
      }

      var rowsHtml = queue.map(function (t, idx) {
        var meta = getTaskMeta(t);
        var details = getTaskDetails(t);
        var status = getTaskStatus(t);

        return '' +
          '<tr>' +
            '<td>' +
              '<input type="number" min="1" class="life-bulk-qno life-web-queue-no" ' +
                'data-name="' + esc(t.name) + '" ' +
                'value="' + esc(getQueueNo(t) || (idx + 1)) + '">' +
            '</td>' +

            '<td>' +
              '<div class="life-web-queue-task">' +
                esc(shortPreviewText(details || "No task details", 120)) +
              '</div>' +
            '</td>' +

            '<td>' +
              queuePriorityBadge(t.priority) +
            '</td>' +

            '<td>' +
              '<div class="life-web-queue-deadline">' +
                esc(formatLifeDateTime(meta.deadline_datetime || t.date)) +
              '</div>' +
            '</td>' +

            '<td>' +
              queueStatusBadge(status) +
            '</td>' +
          '</tr>';
      }).join("");

      var overlay = document.createElement("div");
      overlay.id = "life-web-queue-overlay";
      overlay.className = "life-web-queue-overlay";

      overlay.innerHTML =
        '<div class="life-web-queue-dialog" role="dialog" aria-modal="true" aria-labelledby="life-web-queue-title">' +

          '<div class="life-web-queue-head">' +
            '<div class="life-web-queue-title" id="life-web-queue-title">' +
              'Manage Assignee Queue — ' + esc(userDisplayName(assignee)) +
            '</div>' +

            '<button type="button" class="life-web-queue-close" id="life-web-queue-close" aria-label="Close">&times;</button>' +
          '</div>' +

          '<div class="life-web-queue-body">' +

            '<div class="life-web-queue-note">' +
              'Edit the running task numbers for <strong>' +
                esc(userDisplayName(assignee)) +
              '</strong>. Lower task number means higher running priority. ' +
              'Completed tasks are not included in this queue.' +
            '</div>' +

            '<div class="life-web-queue-table-wrap">' +
              '<table class="life-web-queue-table">' +

                '<colgroup>' +
                  '<col style="width:90px">' +
                  '<col style="width:330px">' +
                  '<col style="width:120px">' +
                  '<col style="width:160px">' +
                  '<col style="width:120px">' +
                '</colgroup>' +

                '<thead>' +
                  '<tr>' +
                    '<th>Task No</th>' +
                    '<th>Task</th>' +
                    '<th>Priority</th>' +
                    '<th>Deadline</th>' +
                    '<th>Status</th>' +
                  '</tr>' +
                '</thead>' +

                '<tbody>' +
                  rowsHtml +
                '</tbody>' +

              '</table>' +
            '</div>' +

          '</div>' +

          '<div class="life-web-queue-foot">' +
            '<button type="button" class="life-web-queue-btn life-web-queue-cancel" id="life-web-queue-cancel">Cancel</button>' +
            '<button type="button" class="life-web-queue-btn life-web-queue-save" id="life-web-queue-save">Save Queue</button>' +
          '</div>' +

        '</div>';

      document.body.appendChild(overlay);

      var closeBtn = overlay.querySelector("#life-web-queue-close");
      var cancelBtn = overlay.querySelector("#life-web-queue-cancel");
      var saveBtn = overlay.querySelector("#life-web-queue-save");

      function closeModalLocal() {
        document.removeEventListener('keydown', escHandler);
        closeManageQueueWebModal();
      }

      if (closeBtn) {
        closeBtn.addEventListener("click", closeModalLocal);
      }

      if (cancelBtn) {
        cancelBtn.addEventListener("click", closeModalLocal);
      }

      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) {
          closeModalLocal();
        }
      });

      var escHandler = function (e) {
        if (e.key === "Escape") {
          closeModalLocal();
          document.removeEventListener("keydown", escHandler);
        }
      };

      document.addEventListener("keydown", escHandler);

      if (saveBtn) {
        saveBtn.addEventListener("click", function () {
          var inputs = overlay.querySelectorAll(".life-bulk-qno");
          var rows = [];

          inputs.forEach(function (input) {
            rows.push({
              name: input.dataset.name || "",
              no: Number(input.value || 0)
            });
          });

          saveBtn.disabled = true;
          saveBtn.textContent = "Saving...";

          applyBulkQueue(
            assignee,
            rows,
            {
              hide: function () {
                document.removeEventListener("keydown", escHandler);
                closeModalLocal();
              },
              setBusy: function (busy) {
                saveBtn.disabled = !!busy;
                saveBtn.textContent = busy ? "Saving..." : "Save Queue";
              }
            }
          );
        });
      }

      var firstInput = overlay.querySelector(".life-bulk-qno");

      if (firstInput) {
        window.setTimeout(function () {
          firstInput.focus();
          firstInput.select();
        }, 30);
      }
    })
    .catch(function (err) {
      void 0;

      showModal(
        "⚠️",
        "Queue Load Failed",
        getErrorMessage(err)
      );
    });
}

function applyBulkQueue(assignee, rows, dialog) {
  rows = rows || [];

  var invalid = rows.some(function (r) {
    return !r.name || !Number.isFinite(r.no) || r.no < 1;
  });

  if (invalid) {
    if (dialog && typeof dialog.setBusy === "function") {
      dialog.setBusy(false);
    }

    showModal(
      "⚠️",
      "Invalid Task Number",
      "Every running task must have a valid task number starting from 1."
    );
    return;
  }

  var used = {};
  var duplicate = false;

  rows.forEach(function (r) {
    if (used[r.no]) duplicate = true;
    used[r.no] = true;
  });

  if (duplicate) {
    if (dialog && typeof dialog.setBusy === "function") {
      dialog.setBusy(false);
    }

    showModal(
      "⚠️",
      "Duplicate Task Number",
      "Duplicate task numbers are not allowed. Give every running task a unique number."
    );
    return;
  }

  rows.sort(function (a, b) {
    return a.no - b.no;
  });

  saveQueueOrder(
    assignee,
    rows.map(function (r) {
      return r.name;
    }),
    "Bulk task number update from Manage Assignee Queue."
  )
    .then(function () {
      if (dialog && typeof dialog.hide === "function") {
        dialog.hide();
      }

      toast(
        "Assignee queue updated successfully.",
        true
      );

      loadTasks();
    })
    .catch(function (err) {
      void 0;

      if (dialog && typeof dialog.setBusy === "function") {
        dialog.setBusy(false);
      }

      showModal(
        "⚠️",
        "Queue Save Failed",
        getErrorMessage(err)
      );
    });
}

/* ------------------------------------------------------------
   Render task tables with Task No column
   ------------------------------------------------------------ */

var oldRenderTaskReportForQueue = renderTaskReport;

renderTaskReport = function () {
  ensureTaskQueueUI();

  var body = $("#task-report-body");
  if (!body) return;

  var catF = getValue("tr-category");
  var priF = getValue("tr-priority");
  var statF = getValue("tr-status");

  var filtered = tasks.filter(function (t) {
    var meta = getTaskMeta(t);
    var status = getTaskStatus(t);

    return (
      (!catF || meta.category === catF) &&
      (!priF || t.priority === priF) &&
      (!statF || status === statF) && taskMatchesAssigneeSearch(t)
    );
  });

  filtered = sortByModifiedLatest(filtered);

  renderTaskTiles();

  setText("task-report-count", String(filtered.length));
  var pageData = getPaginatedRows("taskReport", filtered);

  if (!filtered.length) {
    body.innerHTML =
      '<tr><td colspan="10" style="text-align:center;color:#8C8C8C;padding:18px">No tasks found.</td></tr>';
    return;
  }

  body.innerHTML = pageData.rows.map(function (t) {
    var meta = getTaskMeta(t);
    var status = getTaskStatus(t);
    var details = getTaskDetails(t);
    var updateTo = (meta.update_to || []).map(userDisplayName).join(", ") || "—";
    var workedDays = calculateWorkedDaysLabel(t, meta);

    var detailId = registerDetailHtml(
      "Task Details - " + t.name,
      buildTaskDetailsHtml(t, meta, details, updateTo),
      buildTaskExtraHistorySection(meta)
    );

    return '' +
      '<tr class="life-clickable-row" ' +
        'data-detail-html-id="' + esc(detailId) + '" ' +
        'data-doctype="ToDo" ' +
        'data-docname="' + esc(t.name) + '">' +

        '<td>' + queueNoHtml(t) + '</td>' +

        '<td>' +
          '<div class="life-user-date-cell">' +
            '<div class="life-user-name">' + esc(userDisplayName(t.assigned_by || t.owner)) + '</div>' +
            '<div class="life-user-date">Start: ' + esc(formatLifeDate(meta.start_date || t.creation)) + '</div>' +
          '</div>' +
        '</td>' +

        '<td>' +
          '<div class="life-user-date-cell">' +
            '<div class="life-user-name">' + esc(userDisplayName(t.allocated_to)) + '</div>' +
            '<div class="life-user-date">Due: ' + esc(formatLifeDateTime(meta.deadline_datetime || t.date)) + '</div>' +
            '<div class="life-user-date">Worked: ' + esc(workedDays) + '</div>' +
          '</div>' +
        '</td>' +

        '<td><div class="life-row-main-text">' + esc(meta.category || "—") + '</div></td>' +

        '<td style="max-width:280px;white-space:normal">' +
          '<div class="life-row-main-text">' + esc(shortPreviewText(details || "—", 110)) + '</div>' +
        '</td>' +

        '<td>' + priorityPill(t.priority) + '</td>' +
        '<td style="max-width:180px;white-space:normal">' + esc(updateTo) + '</td>' +
        '<td>' + attachmentChip("ToDo", t.name) + '</td>' +
        '<td>' + statusPill(status) + '</td>' +
        '<td>' + renderTaskActionButtons(t) + '</td>' +
      '</tr>';
  }).join("");

  bindTaskActionButtons(body);
  bindAttachmentChips(body);
  bindClickableTaskRows(body);
  renderTablePagination(body, "taskReport", pageData, renderTaskReport);
};

renderMyTasks = function () {
  ensureTaskQueueUI();

  var toBody = $("#mytask-to-body");
  var byBody = $("#mytask-by-body");

  if (!toBody || !byBody) return;

  var toMe = tasks.filter(function (t) {
    return isCurrentUserValue(t.allocated_to);
  });

  var byMe = tasks.filter(function (t) {
    return (
      t.owner === currentUser ||
      t.assigned_by === currentUser ||
      userDisplayName(t.owner) === currentUserFullName ||
      userDisplayName(t.assigned_by) === currentUserFullName
    );
  });

  setText("mytask-to-count", String(toMe.length));
  setText("mytask-by-count", String(byMe.length));

  toMe = toMe.slice().sort(function (a, b) {
    if (isTaskQueueActive(a) && isTaskQueueActive(b)) {
      return (getQueueNo(a) || 999999) - (getQueueNo(b) || 999999);
    }
    return getModifiedTime(b) - getModifiedTime(a);
  });

  byMe = sortByModifiedLatest(byMe);

  var toPageData = getPaginatedRows("myTaskTo", toMe);
  var byPageData = getPaginatedRows("myTaskBy", byMe);

  toBody.innerHTML = toMe.length
    ? toPageData.rows.map(function (t) {
        var meta = getTaskMeta(t);
        var status = getTaskStatus(t);
        var details = getTaskDetails(t);
        var updateTo = (meta.update_to || []).map(userDisplayName).join(", ") || "—";

        var detailId = registerDetailHtml(
          "Task Details - " + t.name,
          buildTaskDetailsHtml(t, meta, details, updateTo),
          buildTaskExtraHistorySection(meta)
        );

        return '' +
          '<tr class="life-clickable-row" data-detail-html-id="' + esc(detailId) + '" data-doctype="ToDo" data-docname="' + esc(t.name) + '">' +
            '<td>' + queueNoHtml(t) + '</td>' +
            '<td>' +
              '<div class="life-user-date-cell">' +
                '<div class="life-user-name">' + esc(userDisplayName(t.assigned_by || t.owner)) + '</div>' +
                '<div class="life-user-date">Start: ' + esc(formatLifeDate(meta.start_date || t.creation)) + '</div>' +
              '</div>' +
            '</td>' +
            '<td><div class="life-row-main-text">' + esc(meta.category || "—") + '</div></td>' +
            '<td>' + esc(formatLifeDateTime(meta.deadline_datetime || t.date)) + '</td>' +
            '<td>' + priorityPill(t.priority) + '</td>' +
            '<td>' + statusPill(status) + '</td>' +
            '<td>' + renderTaskActionButtons(t) + '</td>' +
          '</tr>';
      }).join("")
    : '<tr><td colspan="7" style="text-align:center;color:#8C8C8C;padding:14px">No tasks assigned to you.</td></tr>';

  byBody.innerHTML = byMe.length
    ? byPageData.rows.map(function (t) {
        var meta = getTaskMeta(t);
        var status = getTaskStatus(t);
        var details = getTaskDetails(t);
        var updateTo = (meta.update_to || []).map(userDisplayName).join(", ") || "—";

        var detailId = registerDetailHtml(
          "Task Details - " + t.name,
          buildTaskDetailsHtml(t, meta, details, updateTo),
          buildTaskExtraHistorySection(meta)
        );

        return '' +
          '<tr class="life-clickable-row" data-detail-html-id="' + esc(detailId) + '" data-doctype="ToDo" data-docname="' + esc(t.name) + '">' +
            '<td>' + queueNoHtml(t) + '</td>' +
            '<td>' +
              '<div class="life-user-date-cell">' +
                '<div class="life-user-name">' + esc(userDisplayName(t.allocated_to)) + '</div>' +
                '<div class="life-user-date">Due: ' + esc(formatLifeDateTime(meta.deadline_datetime || t.date)) + '</div>' +
              '</div>' +
            '</td>' +
            '<td><div class="life-row-main-text">' + esc(meta.category || "—") + '</div></td>' +
            '<td>' + esc(formatLifeDateTime(meta.deadline_datetime || t.date)) + '</td>' +
            '<td>' + priorityPill(t.priority) + '</td>' +
            '<td>' + statusPill(status) + '</td>' +
            '<td>' + renderTaskActionButtons(t) + '</td>' +
          '</tr>';
      }).join("")
    : '<tr><td colspan="7" style="text-align:center;color:#8C8C8C;padding:14px">You have not assigned any tasks.</td></tr>';

  bindTaskActionButtons(toBody);
  bindTaskActionButtons(byBody);

  bindClickableTaskRows(toBody);
  bindClickableTaskRows(byBody);

  renderTablePagination(toBody, "myTaskTo", toPageData, renderMyTasks);
  renderTablePagination(byBody, "myTaskBy", byPageData, renderMyTasks);
};

/* ------------------------------------------------------------
   Make completed tasks leave queue
   ------------------------------------------------------------ */

var oldMarkTaskDoneForQueue = markTaskDone;

markTaskDone = function (name) {
  promptWorkflowRemarks(
    "Complete Task",
    "Completion Remarks *",
    100,
    function (remarks) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "ToDo",
          name: name
        },
        callback: function (r) {
          var doc = r.message;

          if (!doc) {
            showModal("⚠️", "Task Not Found", "Unable to load task.");
            return;
          }

          var assignee = doc.allocated_to;
          var meta = getTaskMeta(doc);
          var details = getTaskDetails(doc);

          meta.workflow_state = "Completed";
          meta.completed_on = getNowLocalDateTime();
          meta.completed_by = currentUser;
          meta.completed_by_name = currentUserFullName || currentUser;
          meta.completion_remarks = remarks;

          meta.worked_days = calculateWorkedDaysLabel(
            {
              creation: doc.creation,
              modified: doc.modified,
              date: doc.date,
              status: "Closed"
            },
            meta
          );

          meta.completion_history = meta.completion_history || [];
          meta.completion_history.push({
            by: currentUser,
            by_name: currentUserFullName || currentUser,
            on: meta.completed_on,
            remarks: remarks
          });

          doc.status = "Open";
          doc.description = buildTaskDescription(details, meta);
          doc = appendQueueHistoryToDoc(
          doc,
          0,
          "Task completed and removed from running queue.",
          assignee
          );
        
          doc.custom_queue_active = 0;
          doc.custom_task_queue_no = 0;
          doc.custom_completed_on = queueNow();
          doc.custom_queue_updated_by = currentUser;
          doc.custom_queue_updated_on = queueNow();

          frappe.call({
            method: "frappe.client.save",
            args: {
              doc: doc
            },
            callback: function () {
              rebuildQueueForAssignee(assignee).then(function () {
                toast("Task completion submitted and removed from running queue.", true);
                loadTasks();
              });
            },
            error: function (err) {
              showModal("⚠️", "Update Failed", getErrorMessage(err));
            }
          });
        },
        error: function (err) {
          showModal("⚠️", "Task Load Failed", getErrorMessage(err));
        }
      });
    }
  );
};

/* ------------------------------------------------------------
   Initial UI injection
   ------------------------------------------------------------ */

ensureTaskQueueUI();

/* ============================================================
   TASK QUEUE HISTORY PATCH
   Paste above init();
   ============================================================ */

function makeQueueHistoryEntry(oldNo, newNo, reason, assignee) {
  return {
    old_no: Number(oldNo || 0),
    new_no: Number(newNo || 0),
    changed_by: currentUser,
    changed_by_name: currentUserFullName || currentUser,
    changed_on: getNowLocalDateTime(),
    assignee: assignee || "",
    reason: reason || "Task number changed."
  };
}

function appendQueueHistoryToDoc(doc, newNo, reason, assignee) {
  doc = doc || {};

  var oldNo = Number(doc.custom_task_queue_no || 0);
  newNo = Number(newNo || 0);

  if (oldNo === newNo) {
    return doc;
  }

  var meta = getTaskMeta(doc);
  var details = getTaskDetails(doc);

  meta.queue_history = meta.queue_history || [];

  meta.queue_history.push(
    makeQueueHistoryEntry(
      oldNo,
      newNo,
      reason,
      assignee || doc.allocated_to || ""
    )
  );

  /* Keep last 100 queue changes only, to avoid very heavy description */
  if (meta.queue_history.length > 100) {
    meta.queue_history = meta.queue_history.slice(-100);
  }

  doc.description = buildTaskDescription(details, meta);

  return doc;
}

/* Override existing setTodoValues so queue no changes are recorded */
setTodoValues = function (name, values, reason) {
  values = values || {};

  var hasQueueNoChange = Object.prototype.hasOwnProperty.call(
    values,
    "custom_task_queue_no"
  );

  values.custom_queue_updated_by = currentUser;
  values.custom_queue_updated_on = queueNow();

  if (!hasQueueNoChange) {
    return qCall("frappe.client.set_value", {
      doctype: "ToDo",
      name: name,
      fieldname: values
    });
  }

  return qCall("frappe.client.get", {
    doctype: "ToDo",
    name: name
  }).then(function (doc) {
    doc = appendQueueHistoryToDoc(
      doc,
      Number(values.custom_task_queue_no || 0),
      reason || "Task number changed.",
      doc.allocated_to
    );

    Object.keys(values).forEach(function (key) {
      doc[key] = values[key];
    });

    return qCall("frappe.client.save", {
      doc: doc
    });
  });
};

/* Override queue save so every reorder writes history */
saveQueueOrder = function (assignee, orderedNames, reason) {
  var chain = Promise.resolve();

  orderedNames.forEach(function (name, idx) {
    name = typeof name === 'string' ? name : name && name.name;
    if (!name) throw new Error('A task document name is required to reorder the queue.');
    chain = chain.then(function () {
      return setTodoValues(
        name,
        {
          custom_task_queue_no: idx + 1,
          custom_queue_active: 1
        },
        reason || "Queue reordered for " + userDisplayName(assignee) + "."
      );
    });
  });

  return chain;
};

/* Queue history UI inside Task Details modal */
function buildTaskQueueHistoryHtml(history) {
  history = history || [];

  if (!history.length) {
    return '<div class="life-empty-history">No task number change history available.</div>';
  }

  return '' +
    '<div class="life-queue-history-list">' +
      history.slice().reverse().map(function (h) {
        var oldNo = Number(h.old_no || 0);
        var newNo = Number(h.new_no || 0);

        return '' +
          '<div class="life-queue-history-card">' +

            '<div class="life-queue-history-top">' +
              '<div class="life-queue-history-title">' +
                esc(h.changed_by_name || h.changed_by || "—") +
              '</div>' +
              '<div class="life-queue-history-date">' +
                esc(formatLifeDateTime(h.changed_on || "")) +
              '</div>' +
            '</div>' +

            '<div class="life-queue-history-change">' +
              '<span>Old: ' + esc(oldNo || "—") + '</span>' +
              '<span>→</span>' +
              '<span>New: ' + esc(newNo || "—") + '</span>' +
            '</div>' +

            '<div class="life-queue-history-meta">' +
              'Assignee: ' + esc(userDisplayName(h.assignee || "")) +
            '</div>' +

            '<div class="life-queue-history-reason">' +
              esc(h.reason || "Task number changed.") +
            '</div>' +

          '</div>';
      }).join("") +
    '</div>';
}

function buildTaskQueueHistorySection(meta) {
  meta = meta || {};

  return '' +
    '<div class="life-detail-section">' +
      '<div class="life-detail-section-title">Task Number Change History</div>' +
      buildTaskQueueHistoryHtml(meta.queue_history || []) +
    '</div>';
}

/* Attach queue history to existing task extra history section */
var oldBuildTaskExtraHistorySectionForQueueHistory =
  typeof buildTaskExtraHistorySection === "function"
    ? buildTaskExtraHistorySection
    : function () { return ""; };

buildTaskExtraHistorySection = function (meta) {
  meta = meta || {};

  return (
    oldBuildTaskExtraHistorySectionForQueueHistory(meta) +
    buildTaskQueueHistorySection(meta)
  );
};

/* ============================================================
   ALL TASKS — GROUP OPEN TASKS BY ASSIGNEE
   Paste above init();
   ============================================================ */

var lifeRenderTaskReportBaseForAssigneeGroup = renderTaskReport;

function ensureAssigneeGroupViewUI() {
  if ($("#tr-view-mode")) return;

  var fbar = $("#task-sub-1 .fbar");
  if (!fbar) return;

  fbar.insertAdjacentHTML(
    "beforeend",
    '' +
    '<div class="life-view-mode-control">' +
      '<label class="lbl">View</label>' +
      '<select id="tr-view-mode">' +
        '<option value="list">Normal List</option>' +
        '<option value="assignee_open">Open Tasks by Assignee</option>' +
      '</select>' +
    '</div>'
  );

  var viewMode = $("#tr-view-mode");

  if (viewMode) {
    viewMode.addEventListener("change", function () {
      resetTablePage("taskReport");

      if (viewMode.value === "assignee_open") {
        var statusFilter = $("#tr-status");

        /*
          Keep Status as All when entering grouped view.
          In grouped view, All means only Open / Reopened / Overdue.
        */
        if (statusFilter) statusFilter.value = "";
      }

      renderTaskReport();
    });
  }
}

function getTaskReportViewMode() {
  var el = $("#tr-view-mode");
  return el ? String(el.value || "list") : "list";
}

function isOpenTaskForAssigneeGroup(t) {
  var status = getTaskStatus(t);

  return (
    status === "Open" ||
    status === "Reopened" ||
    status === "Overdue"
  );
}

function getTaskDeadlineSortValue(t) {
  var meta = getTaskMeta(t);
  var value = meta.deadline_datetime || t.date || t.modified || t.creation || "";

  value = String(value || "").replace(" ", "T");

  var time = new Date(value).getTime();

  return isNaN(time) ? 9999999999999 : time;
}

function sortTasksInsideAssigneeGroup(rows) {
  return (rows || []).slice().sort(function (a, b) {
    var aq = getQueueNo(a) || 999999;
    var bq = getQueueNo(b) || 999999;

    if (aq !== bq) return aq - bq;

    var ad = getTaskDeadlineSortValue(a);
    var bd = getTaskDeadlineSortValue(b);

    if (ad !== bd) return ad - bd;

    return getModifiedTime(b) - getModifiedTime(a);
  });
}

function groupTasksByAssignee(rows) {
  var groups = {};

  (rows || []).forEach(function (t) {
    var assignee = t.allocated_to || "Unassigned";

    if (!groups[assignee]) {
      groups[assignee] = [];
    }

    groups[assignee].push(t);
  });

  return groups;
}


function buildGroupedTaskReportRowHtml(t) {
  var meta = getTaskMeta(t);
  var status = getTaskStatus(t);
  var details = getTaskDetails(t);
  var updateTo = (meta.update_to || []).map(userDisplayName).join(", ") || "—";
  var workedDays = calculateWorkedDaysLabel(t, meta);

  var detailId = registerDetailHtml(
    "Task Details - " + t.name,
    buildTaskDetailsHtml(t, meta, details, updateTo),
    buildTaskExtraHistorySection(meta)
  );

  return '' +
    '<tr class="life-clickable-row" ' +
      'data-detail-html-id="' + esc(detailId) + '" ' +
      'data-doctype="ToDo" ' +
      'data-docname="' + esc(t.name) + '">' +

      '<td>' + queueNoHtml(t) + '</td>' +

      '<td>' +
        '<div class="life-user-date-cell">' +
          '<div class="life-user-name">' + esc(userDisplayName(t.assigned_by || t.owner)) + '</div>' +
          '<div class="life-user-date">Start: ' + esc(formatLifeDate(meta.start_date || t.creation)) + '</div>' +
        '</div>' +
      '</td>' +

      '<td>' +
        '<div class="life-user-date-cell">' +
          '<div class="life-user-name">' + esc(userDisplayName(t.allocated_to)) + '</div>' +
          '<div class="life-user-date">Due: ' + esc(formatLifeDateTime(meta.deadline_datetime || t.date)) + '</div>' +
          '<div class="life-user-date">Worked: ' + esc(workedDays) + '</div>' +
        '</div>' +
      '</td>' +

      '<td><div class="life-row-main-text">' + esc(meta.category || "—") + '</div></td>' +

      '<td style="max-width:280px;white-space:normal">' +
        '<div class="life-row-main-text">' + esc(shortPreviewText(details || "—", 110)) + '</div>' +
      '</td>' +

      '<td>' + priorityPill(t.priority) + '</td>' +
      '<td style="max-width:180px;white-space:normal">' + esc(updateTo) + '</td>' +
      '<td>' + attachmentChip("ToDo", t.name) + '</td>' +
      '<td>' + statusPill(status) + '</td>' +
      '<td>' + renderTaskActionButtons(t) + '</td>' +

    '</tr>';
}

function clearTaskReportPagerForGroupedView() {
  var pager = $("#life-pager-taskReport");
  if (pager) pager.innerHTML = "";
}

function bindAssigneeGroupButtons(scope) {
  (scope || root).querySelectorAll(".life-group-manage-btn").forEach(function (btn) {
    if (btn.dataset.boundAssigneeGroup === "1") return;

    btn.dataset.boundAssigneeGroup = "1";

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      var assignee = btn.dataset.assignee || "";

      if (assignee && assignee !== "Unassigned") {
        openManageQueueDialog(assignee);
      }
    });
  });
}

function renderTaskReportGroupedByAssignee() {
  ensureTaskQueueUI();
  ensureAssigneeGroupViewUI();

  var body = $("#task-report-body");
  if (!body) return;

  var catF = getValue("tr-category");
  var priF = getValue("tr-priority");
  var statF = getValue("tr-status");

  var filtered = tasks.filter(function (t) {
    var meta = getTaskMeta(t);
    var status = getTaskStatus(t);

    /*
      In grouped view:
      - If Status is All, show only running/open tasks.
      - If a Status is selected, respect that selected status.
    */
    var statusOk = statF
      ? status === statF
      : isOpenTaskForAssigneeGroup(t);

    return (
      (!catF || meta.category === catF) &&
      (!priF || t.priority === priF) &&
      statusOk
    );
  });

  renderTaskTiles();
  setText("task-report-count", String(filtered.length));
  clearTaskReportPagerForGroupedView();

  if (!filtered.length) {
    body.innerHTML =
      '<tr><td colspan="10" style="text-align:center;color:#8C8C8C;padding:18px">' +
        'No running tasks found for grouping.' +
      '</td></tr>';
    return;
  }

  var groups = groupTasksByAssignee(filtered);

  var assigneeKeys = Object.keys(groups).sort(function (a, b) {
    return userDisplayName(a).localeCompare(userDisplayName(b));
  });

  var html = "";

  assigneeKeys.forEach(function (assignee) {
    var rows = sortTasksInsideAssigneeGroup(groups[assignee]);

    html += buildAssigneeGroupHeaderHtml(assignee, rows);

    html += rows.map(function (t) {
      return buildGroupedTaskReportRowHtml(t);
    }).join("");
  });

  body.innerHTML = html;

  bindTaskActionButtons(body);
  bindAttachmentChips(body);
  bindClickableTaskRows(body);
  bindAssigneeGroupButtons(body);
}

/* Final override of All Tasks Report */
renderTaskReport = function () {
  ensureAssigneeGroupViewUI();

  if (getTaskReportViewMode() === "assignee_open") {
    renderTaskReportGroupedByAssignee();
    return;
  }

  lifeRenderTaskReportBaseForAssigneeGroup();
};

/* ============================================================
   FORCE ALL TASKS DEFAULT VIEW AS GROUPED BY ASSIGNEE
   Paste below existing grouping patch and above init();
   ============================================================ */

function forceAssigneeGroupedViewDefault() {
  ensureAssigneeGroupViewUI();

  var mode = $("#tr-view-mode");

  if (!mode) return;

  if (mode.dataset.lifeDefaultGrouped !== "1") {
    mode.value = "assignee_open";
    mode.dataset.lifeDefaultGrouped = "1";
  }
}

/* Final final override */
renderTaskReport = function () {
  forceAssigneeGroupedViewDefault();

  if (getTaskReportViewMode() === "assignee_open") {
    renderTaskReportGroupedByAssignee();
    return;
  }

  lifeRenderTaskReportBaseForAssigneeGroup();
};

/* ============================================================
   ASSIGNEE GROUP ACCORDION PATCH
   Paste BELOW existing grouped-view patch and ABOVE init();
   ============================================================ */

var lifeAssigneeGroupOpenState = lifeAssigneeGroupOpenState || {};

function isAssigneeGroupExpanded(assignee) {
  return lifeAssigneeGroupOpenState[assignee] === true;
}

function toggleAssigneeGroup(assignee) {
  lifeAssigneeGroupOpenState[assignee] = !isAssigneeGroupExpanded(assignee);
  renderTaskReportGroupedByAssignee();
}


function bindAssigneeGroupButtons(scope) {
  (scope || root).querySelectorAll(".life-assignee-toggle-zone").forEach(function (zone) {
    if (zone.dataset.boundAssigneeToggle === "1") return;

    zone.dataset.boundAssigneeToggle = "1";

    zone.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      var assignee = zone.dataset.assignee || "";

      if (assignee) {
        toggleAssigneeGroup(assignee);
      }
    });
  });

  (scope || root).querySelectorAll(".life-group-manage-btn").forEach(function (btn) {
    if (btn.dataset.boundAssigneeGroup === "1") return;

    btn.dataset.boundAssigneeGroup = "1";

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      var assignee = btn.dataset.assignee || "";

      if (assignee && assignee !== "Unassigned") {
        openManageQueueDialog(assignee);
      }
    });
  });
}

renderTaskReportGroupedByAssignee = function () {
  ensureTaskQueueUI();
  ensureAssigneeGroupViewUI();

  var body = $("#task-report-body");
  if (!body) return;

  var catF = getValue("tr-category");
  var priF = getValue("tr-priority");
  var statF = getValue("tr-status");

  var filtered = tasks.filter(function (t) {
    var meta = getTaskMeta(t);
    var status = getTaskStatus(t);

    var statusOk = statF
      ? status === statF
      : isOpenTaskForAssigneeGroup(t);

    return (
      (!catF || meta.category === catF) &&
      (!priF || t.priority === priF) &&
      statusOk
    );
  });

  renderTaskTiles();
  setText("task-report-count", String(filtered.length));
  clearTaskReportPagerForGroupedView();

  if (!filtered.length) {
    body.innerHTML =
      '<tr><td colspan="10" style="text-align:center;color:#8C8C8C;padding:18px">' +
        'No running tasks found for grouping.' +
      '</td></tr>';
    return;
  }

  var groups = groupTasksByAssignee(filtered);

  var assigneeKeys = Object.keys(groups).sort(function (a, b) {
    return userDisplayName(a).localeCompare(userDisplayName(b));
  });

  var html = "";

  assigneeKeys.forEach(function (assignee) {
    var rows = sortTasksInsideAssigneeGroup(groups[assignee]);
    var expanded = isAssigneeGroupExpanded(assignee);

    html += buildAssigneeGroupHeaderHtml(assignee, rows, expanded);

    if (expanded) {
      html += rows.map(function (t) {
        return buildGroupedTaskReportRowHtml(t);
      }).join("");
    }
  });

  body.innerHTML = html;

  bindTaskActionButtons(body);
  bindAttachmentChips(body);
  bindClickableTaskRows(body);
  bindAssigneeGroupButtons(body);
};

/* ============================================================
   COMPLETED TASKS IN GROUPED VIEW - CLEAN DISPLAY PATCH
   Paste below grouped accordion patch and above init();
   ============================================================ */

function getGroupedTaskModeLabel() {
  var statF = getValue("tr-status");

  if (statF === "Completed") return "completed";
  if (statF === "Closed") return "closed";
  if (statF === "Cancelled") return "cancelled";

  return "running";
}

function groupedQueueNoHtml(t) {
  var status = getTaskStatus(t);

  if (status === "Completed") {
    return '<span class="life-queue-empty">Done</span>';
  }

  if (status === "Closed") {
    return '<span class="life-queue-empty">Closed</span>';
  }

  if (status === "Cancelled") {
    return '<span class="life-queue-empty">Cancelled</span>';
  }

  return queueNoHtml(t);
}

/* Override grouped task row to show Done instead of queue no for completed */
function buildGroupedTaskReportRowHtml(t) {
  var meta = getTaskMeta(t);
  var status = getTaskStatus(t);
  var details = getTaskDetails(t);
  var updateTo = (meta.update_to || []).map(userDisplayName).join(", ") || "—";
  var workedDays = calculateWorkedDaysLabel(t, meta);

  var detailId = registerDetailHtml(
    "Task Details - " + t.name,
    buildTaskDetailsHtml(t, meta, details, updateTo),
    buildTaskExtraHistorySection(meta)
  );

  return '' +
    '<tr class="life-clickable-row" ' +
      'data-detail-html-id="' + esc(detailId) + '" ' +
      'data-doctype="ToDo" ' +
      'data-docname="' + esc(t.name) + '">' +

      '<td>' + groupedQueueNoHtml(t) + '</td>' +

      '<td>' +
        '<div class="life-user-date-cell">' +
          '<div class="life-user-name">' + esc(userDisplayName(t.assigned_by || t.owner)) + '</div>' +
          '<div class="life-user-date">Start: ' + esc(formatLifeDate(meta.start_date || t.creation)) + '</div>' +
        '</div>' +
      '</td>' +

      '<td>' +
        '<div class="life-user-date-cell">' +
          '<div class="life-user-name">' + esc(userDisplayName(t.allocated_to)) + '</div>' +
          '<div class="life-user-date">Due: ' + esc(formatLifeDateTime(meta.deadline_datetime || t.date)) + '</div>' +
          '<div class="life-user-date">Worked: ' + esc(workedDays) + '</div>' +
        '</div>' +
      '</td>' +

      '<td><div class="life-row-main-text">' + esc(meta.category || "—") + '</div></td>' +

      '<td style="max-width:280px;white-space:normal">' +
        '<div class="life-row-main-text">' + esc(shortPreviewText(details || "—", 110)) + '</div>' +
      '</td>' +

      '<td>' + priorityPill(t.priority) + '</td>' +
      '<td style="max-width:180px;white-space:normal">' + esc(updateTo) + '</td>' +
      '<td>' + attachmentChip("ToDo", t.name) + '</td>' +
      '<td>' + statusPill(status) + '</td>' +
      '<td>' + renderTaskActionButtons(t) + '</td>' +

    '</tr>';
}

/* Override group header so completed view does not say running task(s) */
function buildAssigneeGroupHeaderHtml(assignee, rows, expanded) {
  rows = rows || [];

  var sortedRows = sortTasksInsideAssigneeGroup(rows);
  var modeLabel = getGroupedTaskModeLabel();

  var overdueCount = rows.filter(function (t) {
    return getTaskStatus(t) === "Overdue";
  }).length;

  var highCount = rows.filter(function (t) {
    return t.priority === "High";
  }).length;

  var openCount = rows.filter(function (t) {
    var s = getTaskStatus(t);
    return s === "Open" || s === "Reopened";
  }).length;

  var completedCount = rows.filter(function (t) {
    return getTaskStatus(t) === "Completed";
  }).length;

  var nextTask = sortedRows[0];

  var nextLabel = modeLabel === "running" ? "Next" : "Latest";

  var nextText = nextTask
    ? shortPreviewText(getTaskDetails(nextTask) || "No task details", 90)
    : "No task";

  return '' +
    '<tr class="life-assignee-group-row" data-assignee="' + esc(assignee) + '">' +
      '<td colspan="10">' +
        '<div class="life-assignee-accordion-head">' +

          '<div class="life-assignee-toggle-zone" data-assignee="' + esc(assignee) + '">' +
            '<span class="life-assignee-arrow">' + (expanded ? "▼" : "▶") + '</span>' +

            '<div class="life-assignee-title-box">' +
              '<div class="life-assignee-group-name">' +
                  '<span class="life-assignee-user-icon" aria-hidden="true">' +
                    '<svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor">' +
                      '<path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v1.5c0 .28.22.5.5.5h15c.28 0 .5-.22.5-.5V18c0-2.66-5.33-4-8-4z"></path>' +
                    '</svg>' +
                  '</span>' +
                  '<span>' + esc(userDisplayName(assignee)) + '</span>' +
                '</div>' +
              '<div class="life-assignee-group-next">' +
                nextLabel + ': ' + esc(nextText) +
              '</div>' +
            '</div>' +
          '</div>' +

          '<div class="life-assignee-group-info-row">' +
            '<span class="life-assignee-stat gold">' +
              esc(rows.length) + ' ' + esc(modeLabel) + ' task(s)' +
            '</span>' +

            (
              modeLabel === "running"
                ? '<span class="life-assignee-stat green">Open: ' + esc(openCount) + '</span>' +
                  '<span class="life-assignee-stat">High: ' + esc(highCount) + '</span>' +
                  '<span class="life-assignee-stat red">Overdue: ' + esc(overdueCount) + '</span>' +
                  '<button type="button" class="life-group-manage-btn" data-assignee="' + esc(assignee) + '">' +
                    'Manage Queue' +
                  '</button>'
                : '<span class="life-assignee-stat green">Completed: ' + esc(completedCount) + '</span>' +
                  '<span class="life-assignee-stat">High: ' + esc(highCount) + '</span>'
            ) +

            (
              expanded
                ? ''
                : '<span class="life-assignee-collapsed-note">Click employee name to expand tasks</span>'
            ) +
          '</div>' +

        '</div>' +
      '</td>' +
    '</tr>';
}

/* ============================================================
   ALL TASKS HEADER EMPLOYEE SEARCH FILTER
   Paste below grouped/accordion patches and above init();
   ============================================================ */

function ensureAllTasksEmployeeSearchUI() {
  var body = $("#task-report-body");
  if (!body) return;

  var card = body.closest(".card");
  if (!card) return;

  var hdr = card.querySelector(".card-hdr");
  if (!hdr) return;

  if (hdr.dataset.lifeAssigneeSearchReady === "1") return;
  hdr.dataset.lifeAssigneeSearchReady = "1";

  var countBadge = $("#task-report-count");

  hdr.innerHTML =
    '<div class="life-alltasks-head-left">' +
      '<span>All Tasks</span>' +
    '</div>' +
    '<div class="life-alltasks-head-actions">' +
      '<input type="text" id="life-task-assignee-search" class="life-task-assignee-search" ' +
        'placeholder="Search employee / assignee...">' +
      '<button type="button" id="life-task-assignee-clear" class="life-task-assignee-clear">Clear</button>' +
      '<span class="badge" id="task-report-count">' + esc(countBadge ? countBadge.textContent : "0") + '</span>' +
    '</div>';

  var searchInput = $("#life-task-assignee-search");
  var clearBtn = $("#life-task-assignee-clear");

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      resetTablePage("taskReport");
      renderTaskReport();
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      var input = $("#life-task-assignee-search");

      if (input) {
        input.value = "";
      }

      resetTablePage("taskReport");
      renderTaskReport();
    });
  }
}

function getAssigneeSearchText() {
  var input = $("#life-task-assignee-search");
  return input ? String(input.value || "").trim().toLowerCase() : "";
}

function taskMatchesAssigneeSearch(t) {
  var q = getAssigneeSearchText();

  if (!q) return true;

  var assignee = t.allocated_to || "";
  var assigneeName = userDisplayName(assignee);
  var label = userLabel(assignee);

  var text = [
    assignee,
    assigneeName,
    label
  ].join(" ").toLowerCase();

  return text.indexOf(q) !== -1;
}

/* Override grouped renderer with employee-search support */
renderTaskReportGroupedByAssignee = function () {
  ensureTaskQueueUI();
  ensureAssigneeGroupViewUI();
  ensureAllTasksEmployeeSearchUI();

  var body = $("#task-report-body");
  if (!body) return;

  var catF = getValue("tr-category");
  var priF = getValue("tr-priority");
  var statF = getValue("tr-status");
  var assigneeSearch = getAssigneeSearchText();

  var filtered = tasks.filter(function (t) {
    var meta = getTaskMeta(t);
    var status = getTaskStatus(t);

    var statusOk = statF
      ? status === statF
      : isOpenTaskForAssigneeGroup(t);

    return (
      (!catF || meta.category === catF) &&
      (!priF || t.priority === priF) &&
      statusOk &&
      taskMatchesAssigneeSearch(t)
    );
  });

  renderTaskTiles();
  setText("task-report-count", String(filtered.length));
  clearTaskReportPagerForGroupedView();

  if (!filtered.length) {
    body.innerHTML =
      '<tr><td colspan="10" style="text-align:center;color:#8C8C8C;padding:18px">' +
        (
          assigneeSearch
            ? 'No task groups found for "' + esc(assigneeSearch) + '".'
            : 'No running tasks found for grouping.'
        ) +
      '</td></tr>';
    return;
  }

  var groups = groupTasksByAssignee(filtered);

  var assigneeKeys = Object.keys(groups).sort(function (a, b) {
    return userDisplayName(a).localeCompare(userDisplayName(b));
  });

  var html = "";

  assigneeKeys.forEach(function (assignee) {
    var rows = sortTasksInsideAssigneeGroup(groups[assignee]);
    var expanded = isAssigneeGroupExpanded(assignee);

    html += buildAssigneeGroupHeaderHtml(assignee, rows, expanded);

    if (expanded) {
      html += rows.map(function (t) {
        return buildGroupedTaskReportRowHtml(t);
      }).join("");
    }
  });

  body.innerHTML = html;

  bindTaskActionButtons(body);
  bindAttachmentChips(body);
  bindClickableTaskRows(body);
  bindAssigneeGroupButtons(body);
};

/* Final override so header search is always created */
var lifeRenderTaskReportAfterAssigneeSearch = renderTaskReport;

renderTaskReport = function () {
  ensureAllTasksEmployeeSearchUI();

  if (typeof forceAssigneeGroupedViewDefault === "function") {
    forceAssigneeGroupedViewDefault();
  }

  if (getTaskReportViewMode && getTaskReportViewMode() === "assignee_open") {
    renderTaskReportGroupedByAssignee();
    return;
  }

  lifeRenderTaskReportAfterAssigneeSearch();
};

/* ============================================================
   TASK CANCEL / REOPEN WITH REMARK HISTORY
   Paste near bottom of JS, before final init();
   ============================================================ */

function isTaskCanceller(t) {
  return isTaskAssigner(t) || isManager;
}

function canCancelTask(t) {
  var status = getTaskStatus(t);

  return (
    isTaskCanceller(t) &&
    ["Completed", "Closed", "Cancelled"].indexOf(status) === -1
  );
}

function canReopenCancelledTask(t) {
  return isTaskCanceller(t) && getTaskStatus(t) === "Cancelled";
}

function makeTaskStatusHistoryEntry(action, oldStatus, newStatus, remark) {
  return {
    action: action || "",
    old_status: oldStatus || "",
    new_status: newStatus || "",
    remark: remark || "",
    changed_by: currentUser,
    changed_by_name: currentUserFullName || currentUser,
    changed_on: getNowLocalDateTime()
  };
}

function appendTaskStatusHistoryToDoc(doc, action, oldStatus, newStatus, remark) {
  doc = doc || {};

  var meta = getTaskMeta(doc);
  var details = getTaskDetails(doc);

  meta.status_history = meta.status_history || [];

  meta.status_history.push(
    makeTaskStatusHistoryEntry(action, oldStatus, newStatus, remark)
  );

  if (meta.status_history.length > 100) {
    meta.status_history = meta.status_history.slice(-100);
  }

  doc.description = buildTaskDescription(details, meta);

  return doc;
}

function buildTaskStatusHistoryHtml(history) {
  history = history || [];

  if (!history.length) {
    return '<div class="life-empty-history">No cancel / reopen history available.</div>';
  }

  return '' +
    '<div class="life-history-list">' +
      history.slice().reverse().map(function (h, idx) {
        return '' +
          '<div class="life-history-card">' +
            '<div class="life-history-head">' +
              '<div class="life-history-title">' +
                esc(h.action || "Status Update") + ' - ' +
                esc(h.changed_by_name || h.changed_by || "—") +
              '</div>' +
              '<div class="life-history-date">' +
                esc(formatLifeDateTime(h.changed_on || "")) +
              '</div>' +
            '</div>' +

            '<div class="life-history-grid">' +
              '<div>' +
                '<div class="life-detail-label">Old Status</div>' +
                '<div class="life-detail-value">' + esc(h.old_status || "—") + '</div>' +
              '</div>' +
              '<div>' +
                '<div class="life-detail-label">New Status</div>' +
                '<div class="life-detail-value">' + esc(h.new_status || "—") + '</div>' +
              '</div>' +
            '</div>' +

            '<div class="life-detail-label">Remark</div>' +
            '<div class="life-history-remarks">' + esc(h.remark || "—") + '</div>' +
          '</div>';
      }).join("") +
    '</div>';
}

function buildTaskStatusHistorySection(meta) {
  meta = meta || {};

  return '' +
    '<div class="life-detail-section">' +
      '<div class="life-detail-section-title">Cancel / Reopen History</div>' +
      buildTaskStatusHistoryHtml(meta.status_history || []) +
    '</div>';
}

/* Add cancel/reopen history into existing Task Details modal */
var oldBuildTaskExtraHistorySectionForCancelReopen =
  typeof buildTaskExtraHistorySection === "function"
    ? buildTaskExtraHistorySection
    : function () { return ""; };

buildTaskExtraHistorySection = function (meta) {
  meta = meta || {};

  return (
    oldBuildTaskExtraHistorySectionForCancelReopen(meta) +
    buildTaskStatusHistorySection(meta)
  );
};

function openCancelTaskDialog(name) {
  var task = tasks.find(function (t) {
    return t.name === name;
  });

  if (!task) {
    showModal("⚠️", "Task Not Found", "Unable to find this task.");
    return;
  }

  if (!canCancelTask(task)) {
    showModal("⚠️", "Not Allowed", "Only the assigner or manager can cancel a running task.");
    return;
  }

  var d = new frappe.ui.Dialog({
    title: "Cancel Task",
    fields: [
      {
        fieldtype: "Small Text",
        fieldname: "remark",
        label: "Cancellation Remark",
        reqd: 1
      }
    ],
    primary_action_label: "Cancel Task",
    primary_action: function (values) {
      var remark = String(values.remark || "").trim();

      if (!remark) {
        frappe.msgprint("Please enter cancellation remark.");
        return;
      }

      d.hide();
      cancelTaskWithRemark(name, remark);
    }
  });

  d.show();
}

function cancelTaskWithRemark(name, remark) {
  qCall("frappe.client.get", {
    doctype: "ToDo",
    name: name
  }).then(function (doc) {
    var oldStatus = getTaskStatus(doc);
    var assignee = doc.allocated_to || "";

    if (!canCancelTask(doc)) {
      throw new Error("Only the assigner or manager can cancel this task.");
    }

    doc = appendTaskStatusHistoryToDoc(
      doc,
      "Cancelled",
      oldStatus,
      "Cancelled",
      remark
    );

    doc = appendQueueHistoryToDoc(
      doc,
      0,
      "Task cancelled and removed from running queue.",
      assignee
    );

    doc.status = "Cancelled";
    doc.custom_queue_active = 0;
    doc.custom_task_queue_no = 0;
    doc.custom_queue_updated_by = currentUser;
    doc.custom_queue_updated_on = queueNow();

    return qCall("frappe.client.save", {
      doc: doc
    }).then(function () {
      return rebuildQueueForAssignee(assignee);
    });
  }).then(function () {
    toast("Task cancelled and removed from running queue.", true);
    loadTasks();
  }).catch(function (err) {
    showModal("⚠️", "Cancel Failed", getErrorMessage(err));
  });
}

function openReopenTaskDialog(name) {
  var task = tasks.find(function (t) {
    return t.name === name;
  });

  if (!task) {
    showModal("⚠️", "Task Not Found", "Unable to find this task.");
    return;
  }

  if (!canReopenCancelledTask(task)) {
    showModal("⚠️", "Not Allowed", "Only cancelled tasks can be reopened by the assigner or manager.");
    return;
  }

  var d = new frappe.ui.Dialog({
    title: "Reopen Cancelled Task",
    fields: [
      {
        fieldtype: "Small Text",
        fieldname: "remark",
        label: "Reopen Remark",
        reqd: 1
      }
    ],
    primary_action_label: "Reopen Task",
    primary_action: function (values) {
      var remark = String(values.remark || "").trim();

      if (!remark) {
        frappe.msgprint("Please enter reopen remark.");
        return;
      }

      d.hide();
      reopenCancelledTaskWithRemark(name, remark);
    }
  });

  d.show();
}

function reopenCancelledTaskWithRemark(name, remark) {
  qCall("frappe.client.get", {
    doctype: "ToDo",
    name: name
  }).then(function (doc) {
    var oldStatus = getTaskStatus(doc);
    var assignee = doc.allocated_to || "";

    if (!canReopenCancelledTask(doc)) {
      throw new Error("Only cancelled tasks can be reopened by the assigner or manager.");
    }

    return fetchAssigneeQueue(assignee).then(function (runningRows) {
      var nextNo = (runningRows || []).length + 1;

      doc = appendTaskStatusHistoryToDoc(
        doc,
        "Reopened",
        oldStatus,
        "Open",
        remark
      );

      doc = appendQueueHistoryToDoc(
        doc,
        nextNo,
        "Cancelled task reopened and added back to running queue.",
        assignee
      );

      doc.status = "Open";
      doc.custom_queue_active = 1;
      doc.custom_task_queue_no = nextNo;
      doc.custom_completed_on = null;
      doc.custom_queue_updated_by = currentUser;
      doc.custom_queue_updated_on = queueNow();

      return qCall("frappe.client.save", {
        doc: doc
      });
    });
  }).then(function () {
    toast("Task reopened and added back to running queue.", true);
    loadTasks();
  }).catch(function (err) {
    showModal("⚠️", "Reopen Failed", getErrorMessage(err));
  });
}

/* Add Cancel / Reopen buttons to task action column */
var oldRenderTaskActionButtonsForCancelReopen = renderTaskActionButtons;

renderTaskActionButtons = function (t) {
  var originalHtml = oldRenderTaskActionButtonsForCancelReopen(t);
  var extraHtml = "";

  if (canCancelTask(t)) {
    extraHtml +=
      '<button class="btn btn-sm life-task-cancel-btn task-cancel-btn" data-name="' + esc(t.name) + '">' +
        'Cancel' +
      '</button>';
  }

  if (canReopenCancelledTask(t)) {
    extraHtml +=
      '<button class="btn btn-sm life-task-reopen-btn task-reopen-cancelled-btn" data-name="' + esc(t.name) + '">' +
        'Reopen' +
      '</button>';
  }

  if (!extraHtml) return originalHtml;

  if (!originalHtml || originalHtml === "—") {
    return '<div class="life-action-stack">' + extraHtml + '</div>';
  }

  if (originalHtml.indexOf("life-action-stack") !== -1) {
    return originalHtml.replace("</div>", extraHtml + "</div>");
  }

  return '<div class="life-action-stack">' + originalHtml + extraHtml + '</div>';
};

var oldBindTaskActionButtonsForCancelReopen = bindTaskActionButtons;

bindTaskActionButtons = function (scope) {
  oldBindTaskActionButtonsForCancelReopen(scope);

  (scope || root).querySelectorAll(".task-cancel-btn").forEach(function (btn) {
    if (btn.dataset.boundCancelTask === "1") return;

    btn.dataset.boundCancelTask = "1";

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      openCancelTaskDialog(btn.dataset.name);
    });
  });

  (scope || root).querySelectorAll(".task-reopen-cancelled-btn").forEach(function (btn) {
    if (btn.dataset.boundReopenTask === "1") return;

    btn.dataset.boundReopenTask = "1";

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      openReopenTaskDialog(btn.dataset.name);
    });
  });
};

/* ============================================================
   TASK REASSIGN PATCH
   Paste near bottom of JS, before final init();
   ============================================================ */

function isTaskReassigner(t) {
  return isTaskAssigner(t) || isManager;
}

function canReassignTask(t) {
  var status = getTaskStatus(t);

  return (
    isTaskReassigner(t) &&
    ["Completed", "Closed", "Cancelled"].indexOf(status) === -1
  );
}

function makeTaskReassignHistoryEntry(oldAssignee, newAssignee, remark, newQueueNo) {
  return {
    old_assignee: oldAssignee || "",
    old_assignee_name: userDisplayName(oldAssignee || ""),
    new_assignee: newAssignee || "",
    new_assignee_name: userDisplayName(newAssignee || ""),
    new_queue_no: Number(newQueueNo || 0),
    remark: remark || "",
    changed_by: currentUser,
    changed_by_name: currentUserFullName || currentUser,
    changed_on: getNowLocalDateTime()
  };
}

function appendTaskReassignHistoryToDoc(doc, oldAssignee, newAssignee, remark, newQueueNo) {
  doc = doc || {};

  var meta = getTaskMeta(doc);
  var details = getTaskDetails(doc);

  meta.reassign_history = meta.reassign_history || [];

  meta.reassign_history.push(
    makeTaskReassignHistoryEntry(
      oldAssignee,
      newAssignee,
      remark,
      newQueueNo
    )
  );

  if (meta.reassign_history.length > 100) {
    meta.reassign_history = meta.reassign_history.slice(-100);
  }

  doc.description = buildTaskDescription(details, meta);

  return doc;
}

function buildTaskReassignHistoryHtml(history) {
  history = history || [];

  if (!history.length) {
    return '<div class="life-empty-history">No reassignment history available.</div>';
  }

  return '' +
    '<div class="life-history-list">' +
      history.slice().reverse().map(function (h) {
        return '' +
          '<div class="life-history-card life-update-history-card">' +
            '<div class="life-history-head">' +
              '<div class="life-history-title">' +
                'Reassigned by ' + esc(h.changed_by_name || h.changed_by || "—") +
              '</div>' +
              '<div class="life-history-date">' +
                esc(formatLifeDateTime(h.changed_on || "")) +
              '</div>' +
            '</div>' +

            '<div class="life-history-grid">' +
              '<div>' +
                '<div class="life-detail-label">Old Assignee</div>' +
                '<div class="life-detail-value">' + esc(h.old_assignee_name || h.old_assignee || "—") + '</div>' +
              '</div>' +

              '<div>' +
                '<div class="life-detail-label">New Assignee</div>' +
                '<div class="life-detail-value">' + esc(h.new_assignee_name || h.new_assignee || "—") + '</div>' +
              '</div>' +

              '<div>' +
                '<div class="life-detail-label">New Queue No</div>' +
                '<div class="life-detail-value">#' + esc(h.new_queue_no || "—") + '</div>' +
              '</div>' +
            '</div>' +

            '<div class="life-detail-label">Remark</div>' +
            '<div class="life-history-remarks">' + esc(h.remark || "—") + '</div>' +
          '</div>';
      }).join("") +
    '</div>';
}

function buildTaskReassignHistorySection(meta) {
  meta = meta || {};

  return '' +
    '<div class="life-detail-section">' +
      '<div class="life-detail-section-title">Reassignment History</div>' +
      buildTaskReassignHistoryHtml(meta.reassign_history || []) +
    '</div>';
}

/* Add reassignment history into Task Details modal */
var oldBuildTaskExtraHistorySectionForReassign =
  typeof buildTaskExtraHistorySection === "function"
    ? buildTaskExtraHistorySection
    : function () { return ""; };

buildTaskExtraHistorySection = function (meta) {
  meta = meta || {};

  return (
    oldBuildTaskExtraHistorySectionForReassign(meta) +
    buildTaskReassignHistorySection(meta)
  );
};

function openReassignTaskDialog(name) {
  var task = tasks.find(function (t) {
    return t.name === name;
  });

  if (!task) {
    showModal("⚠️", "Task Not Found", "Unable to find this task.");
    return;
  }

  if (!canReassignTask(task)) {
    showModal(
      "⚠️",
      "Not Allowed",
      "Only the assigner or manager can reassign a running task."
    );
    return;
  }

  var oldAssignee = task.allocated_to || "";

  var d = new frappe.ui.Dialog({
    title: "Reassign Task",
    fields: [
      {
        fieldtype: "Link",
        fieldname: "new_assignee",
        label: "New Assignee",
        options: "User",
        reqd: 1,
        onchange: function () {
          var newAssignee = String(d.get_value("new_assignee") || "").trim();

          if (!newAssignee || newAssignee === oldAssignee) {
            d.set_value("new_queue_no", "");
            return;
          }

          fetchAssigneeQueue(newAssignee).then(function (rows) {
            var nextNo = (rows || []).length + 1;
            d.set_value("new_queue_no", nextNo);

            var help = d.fields_dict.reassign_queue_help;
            if (help && help.$wrapper) {
              help.$wrapper.html(
                '<div style="margin-top:4px;color:#64748B;font-size:11px;font-weight:700;">' +
                  'Current running tasks for new assignee: <b>' + (rows || []).length + '</b>. ' +
                  'Suggested task number: <b>#' + nextNo + '</b>. ' +
                  'You can change it to insert the task in-between.' +
                '</div>'
              );
            }
          });
        }
      },
      {
        fieldtype: "Int",
        fieldname: "new_queue_no",
        label: "Task Number For New Assignee",
        reqd: 1,
        default: 1
      },
      {
        fieldtype: "HTML",
        fieldname: "reassign_queue_help",
        options:
          '<div style="margin-top:4px;color:#64748B;font-size:11px;font-weight:700;">' +
            'Select a new assignee to calculate task number.' +
          '</div>'
      },
      {
        fieldtype: "Small Text",
        fieldname: "remark",
        label: "Reassignment Remark",
        reqd: 1
      }
    ],
    primary_action_label: "Reassign Task",
    primary_action: function (values) {
      var newAssignee = String(values.new_assignee || "").trim();
      var newQueueNo = Number(values.new_queue_no || 0);
      var remark = String(values.remark || "").trim();

      if (!newAssignee) {
        frappe.msgprint("Please select new assignee.");
        return;
      }

      if (newAssignee === oldAssignee) {
        frappe.msgprint("New assignee cannot be same as current assignee.");
        return;
      }

      if (!newQueueNo || newQueueNo < 1) {
        frappe.msgprint("Please enter valid task number.");
        return;
      }

      if (!remark) {
        frappe.msgprint("Please enter reassignment remark.");
        return;
      }

      d.hide();
      reassignTaskWithRemark(name, newAssignee, remark, newQueueNo);
    }
  });

  d.show();
}


function reassignTaskWithRemark(name, newAssignee, remark, requestedQueueNo) {
  var oldAssignee = "";
  var finalQueueNo = 1;

  qCall("frappe.client.get", {
    doctype: "ToDo",
    name: name
  }).then(function (doc) {
    if (!doc) {
      throw new Error("Unable to load task.");
    }

    if (!canReassignTask(doc)) {
      throw new Error("Only the assigner or manager can reassign this task.");
    }

    oldAssignee = doc.allocated_to || "";

    if (!newAssignee || newAssignee === oldAssignee) {
      throw new Error("Please select a different assignee.");
    }

    return fetchAssigneeQueue(newAssignee).then(function (runningRows) {
      runningRows = runningRows || [];

      finalQueueNo = normalizeRequestedQueueNo(
        requestedQueueNo,
        runningRows.length + 1
      );

      doc = appendTaskReassignHistoryToDoc(
        doc,
        oldAssignee,
        newAssignee,
        remark,
        finalQueueNo
      );

      doc = appendQueueHistoryToDoc(
        doc,
        finalQueueNo,
        "Task reassigned from " +
          userDisplayName(oldAssignee) +
          " to " +
          userDisplayName(newAssignee) +
          " at task number #" +
          finalQueueNo +
          ".",
        newAssignee
      );

      doc.allocated_to = newAssignee;
      doc.custom_queue_active = 1;
      doc.custom_task_queue_no = finalQueueNo;
      doc.custom_queue_updated_by = currentUser;
      doc.custom_queue_updated_on = queueNow();

      return qCall("frappe.client.save", {
        doc: doc
      });
    });
  }).then(function () {
    return rebuildQueueForAssignee(oldAssignee);
  }).then(function () {
    return fetchAssigneeQueue(newAssignee);
  }).then(function (newRows) {
    newRows = newRows || [];

    var movedTask = null;
    var otherRows = [];

    newRows.forEach(function (row) {
      if (row.name === name) {
        movedTask = row;
      } else {
        otherRows.push(row);
      }
    });

    if (!movedTask) {
      return rebuildQueueForAssignee(newAssignee);
    }

    otherRows = sortQueueRows(otherRows);

    var insertIndex = Math.max(0, Math.min(finalQueueNo - 1, otherRows.length));
    otherRows.splice(insertIndex, 0, movedTask);

    return saveQueueOrder(
      newAssignee,
      otherRows,
      "Task reassigned and inserted into new assignee queue."
    );
  }).then(function () {
    toast("Task reassigned successfully.", true);
    loadTasks();
  }).catch(function (err) {
    showModal("⚠️", "Reassign Failed", getErrorMessage(err));
  });
}


/* Add Reassign button to task action column */
var oldRenderTaskActionButtonsForReassign = renderTaskActionButtons;

renderTaskActionButtons = function (t) {
  var originalHtml = oldRenderTaskActionButtonsForReassign(t);
  var extraHtml = "";

  if (canReassignTask(t)) {
    extraHtml +=
      '<button class="btn btn-sm life-task-reassign-btn task-reassign-btn" data-name="' + esc(t.name) + '">' +
        'Reassign' +
      '</button>';
  }

  if (!extraHtml) return originalHtml;

  if (!originalHtml || originalHtml === "—") {
    return '<div class="life-action-stack">' + extraHtml + '</div>';
  }

  if (originalHtml.indexOf("life-action-stack") !== -1) {
    return originalHtml.replace("</div>", extraHtml + "</div>");
  }

  return '<div class="life-action-stack">' + originalHtml + extraHtml + '</div>';
};

var oldBindTaskActionButtonsForReassign = bindTaskActionButtons;

bindTaskActionButtons = function (scope) {
  oldBindTaskActionButtonsForReassign(scope);

  (scope || root).querySelectorAll(".task-reassign-btn").forEach(function (btn) {
    if (btn.dataset.boundReassignTask === "1") return;

    btn.dataset.boundReassignTask = "1";

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      openReassignTaskDialog(btn.dataset.name);
    });
  });
};


  init();
  return { refresh: refreshTaskTicketBlock };

}
