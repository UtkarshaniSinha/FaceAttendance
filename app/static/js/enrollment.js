/*
 * Browser side of face enrolment.
 *
 *   camera (getUserMedia) -> <video> live view
 *   "Capture photo"       -> draw the current video frame on a <canvas> -> JPEG Blob
 *   preview               -> employee decides: "Use this photo" or "Retake"
 *   "Use this photo"      -> POST the Blob to the server, which validates it
 *   accepted              -> thumbnail added (kept only in this tab's memory)
 *   rejected              -> server's reason is shown; retake
 *
 * Every POST carries the CSRF token from <meta name="csrf-token">.
 */
(function () {
  "use strict";

  const app = document.getElementById("capture-app");
  if (!app) return;

  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
  const uploadUrl = app.dataset.uploadUrl;
  const deleteUrlTemplate = app.dataset.deleteUrl; // ends in /samples/0/delete
  const minimum = Number(app.dataset.minimum);
  const maximum = Number(app.dataset.maximum);

  const el = (id) => document.getElementById(id);
  const video = el("camera");
  const preview = el("preview");
  const placeholder = el("camera-placeholder");
  const canvas = el("snapshot");
  const message = el("capture-message");
  const startButton = el("start-camera");
  const takeButton = el("take-photo");
  const useButton = el("use-photo");
  const retakeButton = el("retake-photo");
  const fileInput = el("file-input");
  const sampleList = el("sample-list");
  const sampleCount = el("sample-count");
  const progressBar = el("progress-bar");
  const completeButton = el("complete-button");

  let stream = null;
  let pendingBlob = null;
  let pendingUrl = null;
  let count = sampleList.children.length;

  function say(text, kind) {
    message.textContent = text;
    message.className = "capture-message" + (kind ? " capture-" + kind : "");
  }

  function show(element, visible) {
    element.hidden = !visible;
  }

  function updateCount(newCount) {
    count = newCount;
    sampleCount.textContent = String(count);
    progressBar.style.width = Math.min(100, (count / minimum) * 100) + "%";
    completeButton.disabled = count < minimum;
    takeButton.disabled = count >= maximum;
    fileInput.disabled = count >= maximum;
  }

  function clearPending() {
    if (pendingUrl) URL.revokeObjectURL(pendingUrl);
    pendingBlob = null;
    pendingUrl = null;
    preview.removeAttribute("src");
  }

  function showLiveView() {
    clearPending();
    show(preview, false);
    show(useButton, false);
    show(retakeButton, false);
    show(video, Boolean(stream));
    show(placeholder, !stream);
    show(takeButton, Boolean(stream));
    show(startButton, !stream);
  }

  function showPreview(blob) {
    clearPending();
    pendingBlob = blob;
    pendingUrl = URL.createObjectURL(blob);
    preview.src = pendingUrl;
    show(preview, true);
    show(video, false);
    show(placeholder, false);
    show(takeButton, false);
    show(startButton, false);
    show(useButton, true);
    show(retakeButton, true);
    say("Check the photo: is the face clear, centred and well lit?");
  }

  function cameraErrorText(error) {
    switch (error && error.name) {
      case "NotAllowedError":
        return "Camera permission was denied. Allow camera access in the browser's address bar, then try again.";
      case "NotFoundError":
      case "OverconstrainedError":
        return "No camera was found. Connect a webcam or use the photo upload option.";
      case "NotReadableError":
        return "The camera is busy in another app (for example Zoom or Teams). Close it and try again.";
      default:
        return "The camera could not be started. You can use the photo upload option instead.";
    }
  }

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      say("This browser cannot open the camera here. Open the app at http://127.0.0.1:5000 or http://localhost:5000.", "error");
      return;
    }
    startButton.disabled = true;
    say("Starting camera…");
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      showLiveView();
      say("Camera ready. Look at the camera and press “Capture photo”.");
    } catch (error) {
      stream = null;
      say(cameraErrorText(error), "error");
    } finally {
      startButton.disabled = false;
    }
  }

  function stopCamera() {
    if (stream) stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  function capturePhoto() {
    if (!video.videoWidth) {
      say("The camera has not produced a frame yet. Try again in a moment.", "error");
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) showPreview(blob);
      else say("The photo could not be captured. Try again.", "error");
    }, "image/jpeg", 0.92);
  }

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: "POST",
      body: body,
      credentials: "same-origin",
      headers: { "X-CSRF-Token": csrfToken, Accept: "application/json" },
    });
    let data = {};
    try {
      data = await response.json();
    } catch (ignored) {
      data = { error: "Unexpected server response (" + response.status + ")." };
    }
    return { ok: response.ok, data: data };
  }

  function setBusy(busy) {
    [useButton, retakeButton, takeButton, fileInput].forEach((control) => {
      control.disabled = busy;
    });
    if (!busy) updateCount(count);
  }

  function addSampleItem(sampleId, thumbnailUrl, quality) {
    const item = document.createElement("li");
    item.dataset.sampleId = String(sampleId);
    const thumb = document.createElement("img");
    thumb.className = "thumb";
    thumb.alt = "Accepted photo";
    thumb.src = thumbnailUrl;
    const label = document.createElement("span");
    label.textContent = "Accepted · sharpness " + quality.sharpness + ", brightness " + quality.brightness;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "link-button";
    remove.dataset.remove = "";
    remove.textContent = "Remove";
    item.append(thumb, label, remove);
    sampleList.append(item);
  }

  async function usePhoto() {
    if (!pendingBlob) return;
    const form = new FormData();
    form.append("image", pendingBlob, "capture.jpg");
    setBusy(true);
    say("Checking the photo on the server…");
    try {
      const { ok, data } = await postJson(uploadUrl, form);
      if (!ok) {
        say((data.error || "The photo was rejected.") + " Press “Retake” to try again.", "error");
        show(useButton, false); // the same photo would be rejected again
        return;
      }
      // Keep the thumbnail URL alive for the list; do not revoke it in clearPending.
      addSampleItem(data.sample_id, pendingUrl, data.quality);
      pendingUrl = null;
      updateCount(data.accepted_sample_count);
      showLiveView();
      const remaining = Math.max(0, minimum - data.accepted_sample_count);
      say(remaining > 0
        ? "Photo accepted. " + remaining + " more needed."
        : "Photo accepted. You can complete the enrolment or add more photos.", "success");
    } catch (error) {
      say("Network error. Check that the app is still running, then retry.", "error");
    } finally {
      setBusy(false);
    }
  }

  async function removeSample(item) {
    const sampleId = item.dataset.sampleId;
    const url = deleteUrlTemplate.replace("/samples/0/", "/samples/" + encodeURIComponent(sampleId) + "/");
    const { ok, data } = await postJson(url, new FormData());
    if (!ok) {
      say(data.error || "The image could not be removed.", "error");
      return;
    }
    const thumb = item.querySelector("img.thumb");
    if (thumb) URL.revokeObjectURL(thumb.src);
    item.remove();
    updateCount(data.accepted_sample_count);
    say("Image removed and deleted from storage.", "success");
  }

  startButton.addEventListener("click", startCamera);
  takeButton.addEventListener("click", capturePhoto);
  useButton.addEventListener("click", usePhoto);
  retakeButton.addEventListener("click", () => {
    showLiveView();
    say(stream ? "Ready for another photo." : "");
  });
  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    fileInput.value = "";
    if (file) showPreview(file);
  });
  sampleList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (button) removeSample(button.closest("li"));
  });
  window.addEventListener("pagehide", stopCamera);

  updateCount(count);
})();
