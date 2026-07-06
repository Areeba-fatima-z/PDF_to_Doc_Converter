# PDF to DOCX Converter

A full-stack web application to convert pdf files into doxc files.

---

## Short Description
A drag-and-drop web tool that converts PDF files into editable Word documents. It handles validation, background processing, and lets users download files individually or as a ZIP.

---

## Features

- **One or Multiple files** - Let users upload one or muliple files at a time
- **Zip Folder** - Create zip folder and let the user download it from Download All(Zip) button
- **Individual files** - Lists individual converted files to download seperatly
- **Status** - Responsive status show of the job uploaded

---

## Constraints

- **Upload limit** - 100 Files (maximum) at a time
- **Files size** - Maximum 100MB 
- **Corrupted or encrypted** - Don't accept corrupted or password protected files
--**Formate allowed** - Only pdfs are allowed to upload

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Database | Redis |
| Job Queue| RQ |
| Converter | pdf2doxc |
| pdf reading | Fitz / PyMupdf |

---

## Project Structure

```
student_Performance_Tracker/
├── app.py              Flask backend + API routes
├── task.py             Helper functions
├── index.html          Frontend structure
├── style.css           Styling 
├── script.js           API calls
├── requirements.txt    Python dependencies
└── .gitignore          Ignored files
```

---

## Run Locally

**1. Clone the repository**
```bash
git clone https://github.com/Areeba-fatima-z/PDF_to_Doc_Converter.git
cd PDF_to_Doc_Converter
```

**2. Install dependencies**
```bash
pip install -r requirement.txt
```

**3. Run the Flask server**
```bash
python app.py
```
**4. Run worker**
```bash
rq worker
```
**5. Open in browser**
```
http://localhost:5000
```

---