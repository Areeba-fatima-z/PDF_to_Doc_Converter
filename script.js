const upload_btn = document.getElementById('convert_btn')
const pdfFile = document.getElementById('pdfFile')
const status1 = document.getElementById('status')
const download1 = document.getElementById('download')
const fileList = document.getElementById('fileList')
const API_BASE = 'http://127.0.0.1:5000';

// on click upload button
//async => wait for the function to complete
upload_btn.addEventListener('click', async (e) => {
    e.preventDefault();
    if (pdfFile.files.length == 0) {
        status1.textContent = 'Select files!';
        return;
    }
    //Formdata object to store files
    const formData = new FormData()

    for (const files of pdfFile.files) {
        formData.append('files', files)
    }

    // show status => uploading
    status1.textContent = 'Uploading File';


    try {
        //give request to backend 
        const response = await fetch(`${API_BASE}/convert/pdf-to-doc`, {
            method: 'POST', body: formData
        });
        // backend reply
        const data = await response.json()
        // True => 4**/5** False => 2** 
        if (!response.ok) {
            // error message from backend
            status1.textContent = `error: ${data.error}`;
            return;
        }

        status1.textContent = `Job queued! ID: ${data.job_id}`;
        pollJobStatus(data.job_id);
    }
    catch (err) {
        status1.textContent = 'Upload failed: ' + err.message;
    }

})


function pollJobStatus(jobId) {
    console.log('✅ Polling started for:', jobId);

    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/jobs/${jobId}`);
            const job = await response.json();

            console.log('📡 Poll response:', job);   // 👈 har 2 sec mein ye dikhna chahiye

            status1.textContent = `Status: ${job.status} (${job.succeeded}/${job.total_files} done)`;

            if (job.status === 'completed') {
                console.log('🎉 Completed! Showing button now...');
                clearInterval(interval);
                showDownloadButton(jobId);
                console.log('🔽 download div HTML is now:', download.innerHTML);
                showIndividualFiles(jobId);
            }
        } catch (err) {
            console.error('Status check failed:', err);
        }
    }, 2000);
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

        if (!response.ok || !data.files) {
            return;
        }

        // har file ke liye ek download link banao
        let html = '<h3>Individual Files:</h3><ul>';
        for (const file of data.files) {
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


