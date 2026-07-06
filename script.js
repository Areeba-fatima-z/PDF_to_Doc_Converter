const upload_btn = document.getElementById('convert_btn')
const pdfFile = document.getElementById('pdfFile')
const status1 = document.getElementById('status')
const download1 = document.getElementById('download')
const fileList = document.getElementById('fileList')
const API_BASE = 'http://127.0.0.1:5000';


upload_btn.addEventListener('click', async (e) => {
    e.preventDefault();
    if (pdfFile.files.length == 0) {
        status1.textContent = 'No Files selected to upload!';
        return;
    }

    const formData = new FormData()
    for (const files of pdfFile.files) {
        formData.append('files', files)
    }

    status1.textContent = 'Uploading ..........';
    //
    try {
        const response = await fetch(`${API_BASE}/convert/pdf-to-doc`, {
            method: 'POST', body: formData
        });
        const data = await response.json()

        if (!response.ok) {
            status1.textContent = `error: ${data.error} -- Rejected Files : ${data.rejected}`;
            return;
        }

        let msg = `Job queued! Accepted: ${data.accepted} file `;
        if (data.rejected && data.rejected.length > 0) {
            msg += `-- Skipped ${data.rejected.length} file `;
            msg += data.rejected.map(r => `--${r.filename} (${r.reason})`).join(', ');
        }

        status1.textContent = msg;
        pollJobStatus(data.job_id);
    }
    catch (err) {
        status1.textContent = 'Upload failed: ' + err.message;
    }
})


function pollJobStatus(jobId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/jobs/${jobId}`);
            const job = await response.json();
            const done = (job.succeeded || 0) + (job.failed || 0);

            if (job.status === 'processing') {
                const rejectedCount = (job.rejected || []).length;
                const totalOriginal = job.total_files + rejectedCount;
                status1.textContent = `Converting... ${done}/${job.total_files} -- (${rejectedCount} skipped)`;
            }
            else if (job.status === 'completed') {
                const rejectedCount = (job.rejected || []).length;

                let msg = `Done! ${job.succeeded} converted successfully`;

                if (job.failed > 0) {
                    msg += `-- ${job.failed} failed during conversion`;
                }

                if (rejectedCount > 0) {
                    msg += `-- ${rejectedCount} rejected (invalid file)`;
                }

                status1.textContent = msg;
                // stop status updated 
                clearInterval(interval);
                showDownloadButton(jobId);
                showIndividualFiles(jobId);
                // delete in 1 min from upload and output
                setTimeout(() => {
                    fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' });
                }, 60 * 1000);
            }
        } catch (err) {
            console.error('Status check failed:', err);
        }
    }, 1000);
}


function showDownloadButton(jobId) {
    download1.innerHTML = `
        <a href="${API_BASE}/jobs/${jobId}/download" target="_blank">
            <button>Download All (ZIP)</button>
        </a>
    `;
}


async function showIndividualFiles(jobId) {
    try {
        const response = await fetch(`${API_BASE}/jobs/${jobId}/files`);
        const data = await response.json();

        if (!response.ok || !data.files) return;

        let html = '<h3>Individual Files:</h3><ul>';
        for (const file of data.files) {
            // tofixed (1) - rounf of to decimal 1
            html += `
                <li>
                    ${file.filename} (${(file.size / 1024).toFixed(1)} KB)
                    <a href="${API_BASE}/jobs/${jobId}/files/${encodeURIComponent(file.filename)}" target="_blank">
                        <button>Download</button>
                    </a>
                </li>
            `;
        }
        html += '</ul>';
        fileList.innerHTML = html;
    } catch (err) {
        console.error('Failed to load file list:', err);
    }
}