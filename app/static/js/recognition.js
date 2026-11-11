/*
 * Face check-in page: camera -> one still photo -> POST /recognition/check-in.
 *
 * The server decides everything (recognition, eligibility, duplicate
 * protection). This script only shows the answer, and blocks repeated clicks:
 * one request at a time, then a short pause before the next capture.
 * Every POST carries the CSRF token.
 */
(function () {
  "use strict";

  const app = document.getElementById("recognition-app");
  if (!app) return;

  const COOLDOWN_MS = 3000;
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
  const el = (id) => document.getElementById(id);
  const video = el("camera");
  const preview = el("preview");
  const placeholder = el("camera-placeholder");
  const canvas = el("snapshot");
  const message = el("capture-message");
  const startButton = el("start-camera");
  const checkInButton = el("check-in");
  const fileInput = el("file-input");
  const result = el("result");
  const resultTitle = el("result-title");
  const resultDetail = el("result-detail");
  let stream = null;
  let previewUrl = null;
  let busy = false;

  // outcome -> [card style, title]
  const OUTCOMES = {
    recorded: ["match", "Attendance recorded"],
    already_recorded: ["info", "Already checked in today"],
    unknown: ["unknown", "Unknown face — no attendance recorded"],
    ambiguous: ["warning", "Ambiguous match — no attendance recorded"],
    consent_required: ["warning", "Consent required — no attendance recorded"],
    inactive: ["warning", "Inactive employee — no attendance recorded"],
    enrolment_incomplete: ["warning", "Enrolment incomplete — no attendance recorded"],
  };

  function say(text, kind) {
    message.textContent = text;
    message.className = "capture-message" + (kind ? " capture-" + kind : "");
  }

  function showResult(kind, title, detail) {
    result.className = "result-card result-" + kind;
    resultTitle.textContent = title;
    resultDetail.textContent = detail;
  }

  function setBusy(value) {
    busy = value;
    checkInButton.disabled = value;
    fileInput.disabled = value;
  }

  function showPreview(blob) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(blob);
    preview.src = previewUrl;
    preview.hidden = false;
    video.hidden = true;
    placeholder.hidden = true;
  }

  function showLive() {
    preview.hidden = true;
    video.hidden = !stream;
    placeholder.hidden = Boolean(stream);
  }

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      say("This browser cannot open the camera here. Use http://127.0.0.1:5000.", "error");
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      startButton.hidden = true;
      checkInButton.hidden = false;
      showLive();
      say("Camera ready. One person, facing the camera, in good light.");
    } catch (error) {
      say(error && error.name === "NotAllowedError"
        ? "Camera permission was denied. Allow it in the address bar and try again."
        : "The camera could not be started. Use the photo option instead.", "error");
    }
  }

  function describe(data) {
    const who = data.employee ? data.employee.full_name + " (" + data.employee.employee_code + ")" : "";
    const score = data.similarity === null ? "" : " Similarity " + data.similarity.toFixed(3) + ".";
    const when = data.attendance ? " " + data.attendance.date + " at " + data.attendance.time + "." : "";
    return [who, data.message + when + score].filter(Boolean).join(" — ");
  }

  // Callers must call lock() first, so a second click can never start a second request.
  function lock() {
    if (busy) return false;
    setBusy(true);
    return true;
  }

  async function send(blob) {
    showPreview(blob);
    say("Checking…");
    const form = new FormData();
    form.append("image", blob, "capture.jpg");
    try {
      const response = await fetch(app.dataset.checkInUrl, {
        method: "POST",
        body: form,
        credentials: "same-origin",
        headers: { "X-CSRF-Token": csrfToken, Accept: "application/json" },
      });
      const data = await response.json().catch(() => ({}));
      const known = OUTCOMES[data.outcome];
      if (!response.ok) {
        // Any error status: never show success.
        showResult("error", "Not recorded", data.error || "A server error occurred. Attendance was NOT recorded.");
        say("Adjust and try again.", "error");
      } else if (known) {
        showResult(known[0], known[1], describe(data));
        say(data.recorded ? "Done." : "No attendance recorded.", data.recorded ? "success" : "");
      } else {
        showResult("error", "Not recorded", "Unexpected server response. Attendance was NOT recorded.");
      }
    } catch (error) {
      showResult("error", "Not recorded", "Network error. Attendance was NOT recorded. Is the app still running?");
    } finally {
      // Short pause before the next attempt prevents accidental double check-ins.
      setTimeout(() => {
        setBusy(false);
        if (stream) showLive();
      }, COOLDOWN_MS);
    }
  }

  function captureAndSend() {
    if (!video.videoWidth) {
      say("The camera has not produced a frame yet.", "error");
      return;
    }
    // Lock immediately: canvas.toBlob is asynchronous, and a second click
    // during encoding must not start another request.
    if (!lock()) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) send(blob);
      else {
        setBusy(false);
        say("The photo could not be captured. Try again.", "error");
      }
    }, "image/jpeg", 0.92);
  }

  startButton.addEventListener("click", startCamera);
  checkInButton.addEventListener("click", captureAndSend);
  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    fileInput.value = "";
    if (file && lock()) send(file);
  });
  window.addEventListener("pagehide", () => {
    if (stream) stream.getTracks().forEach((track) => track.stop());
  });
})();
