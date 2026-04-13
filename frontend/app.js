(function () {
  const API_BASE = "";

  const form = document.getElementById("pipelineForm");
  const liveLog = document.getElementById("liveLog");
  const resultsSection = document.getElementById("resultsSection");
  const submitBtn = document.getElementById("submitBtn");
  const btnDownloadCr = document.getElementById("btnDownloadCr");
  const btnDownloadPlan = document.getElementById("btnDownloadPlan");
  const btnDownloadRaid = document.getElementById("btnDownloadRaid");
  const btnJira = document.getElementById("btnJira");
  const btnSmartsheet = document.getElementById("btnSmartsheet");
  const crPreview = document.getElementById("crPreview");
  const planPreview = document.getElementById("planPreview");
  const raidPreview = document.getElementById("raidPreview");
  const resultSummary = document.getElementById("resultSummary");

  let currentEventSource = null;
  let lastJiraUrl = null;
  let lastSmartsheetUrl = null;

  function appendLog(stage, message, isError) {
    const line = document.createElement("div");
    line.className = "log-line";
    line.innerHTML =
      '<span class="stage">' +
      escapeHtml(stage) +
      "</span> — " +
      (isError ? '<span class="err">' : "") +
      escapeHtml(message) +
      (isError ? "</span>" : "");
    liveLog.appendChild(line);
    liveLog.scrollTop = liveLog.scrollHeight;
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function resetUi() {
    liveLog.innerHTML = "";
    resultsSection.classList.add("hidden");
    if (currentEventSource) {
      currentEventSource.close();
      currentEventSource = null;
    }
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    resetUi();

    const meeting = document.getElementById("meeting").files[0];
    const scope = document.getElementById("scope").files[0];
    const kickoff = document.getElementById("kickoff").files[0];
    if (!meeting && !scope) {
      appendLog("error", "Please select a meeting file and/or a scope document.", true);
      return;
    }

    const fd = new FormData();
    if (meeting) fd.append("meeting", meeting);
    if (scope) fd.append("scope", scope);
    if (kickoff) fd.append("kickoff", kickoff);
    fd.append("use_llm", document.getElementById("useLlm").checked ? "true" : "false");
    fd.append("create_jira", document.getElementById("createJira").checked ? "true" : "false");
    fd.append("syncSmartsheet", document.getElementById("syncSmartsheet").checked ? "true" : "false");

    submitBtn.disabled = true;
    appendLog("client", "Submitting pipeline job…", false);

    try {
      const res = await fetch(API_BASE + "/api/v1/pipeline/jobs", {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      const data = await res.json();
      const jobId = data.job_id;
      appendLog("client", "Job id: " + jobId + " — listening for events…", false);

      const url = API_BASE + "/api/v1/pipeline/jobs/" + jobId + "/events";
      currentEventSource = new EventSource(url);

      currentEventSource.onmessage = function (ev) {
        let payload;
        try {
          payload = JSON.parse(ev.data);
        } catch {
          appendLog("parse", "Invalid event payload", true);
          return;
        }

        appendLog(payload.stage || "?", payload.message || "", !!payload.error);

        if (payload.error && payload.done) {
          currentEventSource.close();
          submitBtn.disabled = false;
          resultSummary.textContent = "Pipeline failed: " + payload.error;
          resultsSection.classList.remove("hidden");
          return;
        }

        if (payload.done && !payload.error) {
          currentEventSource.close();
          submitBtn.disabled = false;
          showResults(jobId, payload);
        }
      };

      currentEventSource.onerror = function () {
        appendLog("events", "EventSource connection error (server may have closed stream).", true);
      };
    } catch (err) {
      appendLog("error", String(err.message || err), true);
      submitBtn.disabled = false;
    }
  });

  function showResults(jobId, lastPayload) {
    const art = lastPayload.artifacts || {};
    const ran = lastPayload.ran_agents || [];
    resultsSection.classList.remove("hidden");
    resultSummary.textContent =
      "Job " +
      jobId +
      " completed. Agents run: " +
      (ran.length ? ran.join(", ") : "(none)") +
      ". Use the buttons below to download when available.";

    crPreview.textContent = art.cr_markdown || "(CR not generated — scope document required.)";
    planPreview.textContent = art.plan_markdown || "(Plan not generated — scope document required.)";
    raidPreview.textContent = art.raid_markdown || (art.raid_title ? "Title: " + art.raid_title : "(see Excel)");

    var hasCr = !!(art.cr_docx || art.cr_file);
    var hasPlan = !!art.plan_file;
    var hasRaid = !!art.raid_excel;

    btnDownloadCr.href = API_BASE + "/api/v1/pipeline/jobs/" + jobId + "/download/cr";
    btnDownloadPlan.href = API_BASE + "/api/v1/pipeline/jobs/" + jobId + "/download/plan";
    btnDownloadRaid.href = API_BASE + "/api/v1/pipeline/jobs/" + jobId + "/download/raid";

    btnDownloadCr.classList.toggle("hidden", !hasCr);
    btnDownloadPlan.classList.toggle("hidden", !hasPlan);
    btnDownloadRaid.classList.toggle("hidden", !hasRaid);

    lastJiraUrl = art.jira_primary_url || (art.jira_urls && art.jira_urls[0]) || null;
    lastSmartsheetUrl = art.smartsheet_url || null;

    btnJira.disabled = !lastJiraUrl;
    btnSmartsheet.disabled = !lastSmartsheetUrl;
  }

  btnJira.addEventListener("click", function () {
    if (lastJiraUrl) window.open(lastJiraUrl, "_blank", "noopener,noreferrer");
  });

  btnSmartsheet.addEventListener("click", function () {
    if (lastSmartsheetUrl) window.open(lastSmartsheetUrl, "_blank", "noopener,noreferrer");
  });
})();
