// SentinelAI - Modern Dashboard Controller

document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const selectedFileName = document.getElementById("selectedFileName");
    const uploadForm = document.getElementById("uploadForm");
    const submitBtn = document.getElementById("submitBtn");
    const statusAlert = document.getElementById("statusAlert");
    const tableSearchInput = document.getElementById("tableSearchInput");
    const documentsTable = document.getElementById("documentsTable");

    // Table Live Search Filtering
    if (tableSearchInput && documentsTable) {
        tableSearchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase();
            const rows = documentsTable.querySelectorAll("tbody tr");
            rows.forEach((row) => {
                const nameEl = row.querySelector(".doc-name");
                if (nameEl) {
                    const text = nameEl.textContent.toLowerCase();
                    row.style.display = text.includes(query) ? "" : "none";
                }
            });
        });
    }

    if (!dropZone || !fileInput) return;

    // Dropzone interaction
    dropZone.addEventListener("click", () => fileInput.click());

    ["dragenter", "dragover"].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add("dragover");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove("dragover");
        }, false);
    });

    dropZone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        if (dt.files && dt.files.length > 0) {
            fileInput.files = dt.files;
            updateFileInfo(dt.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files && fileInput.files.length > 0) {
            updateFileInfo(fileInput.files[0]);
        }
    });

    function updateFileInfo(file) {
        const sizeFormatted = file.size > 1048576 
            ? (file.size / 1048576).toFixed(2) + " MB" 
            : (file.size / 1024).toFixed(1) + " KB";
            
        selectedFileName.innerHTML = `
            <i class="bi bi-file-check-fill text-success me-1"></i>
            <strong>${file.name}</strong> (${sizeFormatted})
        `;
        selectedFileName.className = "badge bg-primary-subtle text-primary border border-primary-subtle px-3 py-2";
    }

    // Form submission
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (!fileInput.files || fileInput.files.length === 0) {
            showAlert("danger", "Please select a valid PDF, JPG, or PNG document file.");
            return;
        }

        const formData = new FormData(uploadForm);
        const originalBtnHtml = submitBtn.innerHTML;

        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            <span>Running OCR &amp; Mathematical Validation...</span>
        `;
        hideAlert();

        try {
            const response = await fetch("/api/v1/documents/process", {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                const errMsg = data.error?.message || "Failed to process document.";
                const errCode = data.error?.code ? `[${data.error.code}] ` : "";
                showAlert("danger", `${errCode}${errMsg}`);
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHtml;
                return;
            }

            showAlert("success", `Document '${data.document_name}' successfully processed and audited! Redirecting to report...`);
            setTimeout(() => {
                window.location.href = `/documents/${encodeURIComponent(data.document_name)}`;
            }, 1000);

        } catch (err) {
            console.error("Processing error:", err);
            showAlert("danger", "Network error or server unavailable. Please ensure the backend is running.");
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnHtml;
        }
    });

    function showAlert(type, message) {
        statusAlert.className = `alert alert-${type} mt-3 d-flex align-items-center gap-2 border-0 shadow-sm`;
        statusAlert.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle-fill' : 'exclamation-octagon-fill'} fs-5"></i>
            <div class="small fw-semibold">${message}</div>
        `;
        statusAlert.classList.remove("d-none");
    }

    function hideAlert() {
        statusAlert.classList.add("d-none");
    }
});
