#Tech stack : Python , flask , pyMuPDF , pdf2docx , python-docx, RQ , local storage

from flask import Flask, jsonify, request, send_file ,send_from_directory
from flask_cors import CORS
import redis #for RQ 
import json
import os
import uuid  # generates unique id 
import shutil #Delets folder
import fitz  # PyMuPDF
from pdf2docx import Converter # conversion
from rq import Queue
from datetime import timedelta
from task import r , q, save_job ,save_files,convert_pdf,cleanup
from werkzeug.utils import secure_filename

app=Flask(__name__)
CORS(app)

# Redis connection 
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
q = Queue(connection=r)


UPLOAD_DIR = 'uploads'
OUTPUT_DIR= 'output'


def generate_job_id():
    return str(uuid.uuid4())

def get_job(job_id):
    g_job = r.get(f"Job:{job_id}")
    if g_job :
        #json.loads () convert string into dictionary 
        return json.loads(g_job)
    else:
        return None 
 
def get_files(job_id):
    g_file=r.get(f"Files:{job_id}")
    if g_file:
        return json.loads(g_file)
    else:
        return []
    
def validate_pdf(file):
     try:
        pdf_bytes = file.read()
        file.seek(0)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        if doc.is_encrypted:
            doc.close()
            return False, "Password protected PDF."

        for page in doc:
            page.get_text()

        doc.close()
        return True, ""

     except Exception:
        return False, "Corrupted or invalid PDF."




#################################################################################################
# Rest API's

#POST /convert/pdf-to-docp
@app.route('/convert/pdf-to-doc' , methods = ['POST'])
def upload_and_convert():
    file = request.files.getlist('files')

    if len(file)==0:
        return jsonify({'error':'File not Uploaded'}),400 # Not found error code
    # Upload limit check : Max 100 files 
    if len(file) >100:
        return jsonify({'error':'Can not Upload more than 100 files'}),400
    
    #unique job id 
    job_id = generate_job_id()
    # folder path like : 'uploads/a1b2c3d4' 
    job_folder = os.path.join(UPLOAD_DIR, job_id)
    # Folder creation    |  if already exists continue
    os.makedirs(job_folder, exist_ok=True)

    for f in file :
        #Move cursor to the end of file
        f.seek(0,os.SEEK_END)
        #Current position of cursor
        size = f.tell()
        f.seek(0)
        
        # check pdf formate
        if not f.filename.lower().endswith('.pdf'):
            return jsonify({'error':'Wrong Foramte file uploaded'}),400
        
        # File size check : Max 100MB
        # 1MB = 1024KB = 1024 *1024 byte
        if size >= 100*1024*1024 :
            return jsonify({'error': 'File size exceeds the upload limit (100MB)'}),400
        #Check protected files
        valid, reason = validate_pdf(f)
        if not valid:
            return jsonify({'error': f'{f.filename}: {reason}'}), 400
        safe_name = secure_filename(f.filename)
        f.save(os.path.join(job_folder,secure_filename))
    save_job(job_id,{'status':'queued','total_files':len(file),'succeeded':0,'failed':0 })
    q.enqueue(convert_pdf, job_id)
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202


#GET /jobs/{job_id}
@app.route('/jobs/<job_id>',methods =['GET'])
def check_conversion_status(job_id):
    Job = get_job(job_id)
    if not Job:
        return jsonify({'error':'Job not Found'}),404
    # ** unpack to use data.status
    # data = {'job_id': job_id, **Job}
    return jsonify({'job_id': job_id, **Job}), 200 # request done 


#GET /jobs/{job_id}/files
@app.route('/jobs/<job_id>/files',methods=['GET'])
def list_converted_files(job_id):
    if not get_job(job_id):
        return jsonify({'error':'Job not found'}),400
    files = get_files(job_id)
    
    result = []
    for f in files:
        new_file={
            'filename':f['output_name'],
            'size': f['size_bytes'],
            'download_url': f"/jobs/{job_id}/files/{f['output_name']}"
        }
        result.append(new_file)

    return jsonify({"files": result}), 200


#GET /jobs/{job_id}/download   zip file 
@app.route('/jobs/<job_id>/download',methods=['GET'])
def download_zip(job_id):
    zip_path = os.path.join(OUTPUT_DIR,f"{job_id}.zip")
    
    if not os.path.exists(zip_path):
        output_folder = os.path.join(OUTPUT_DIR, job_id)
        if not os.path.exists(output_folder):
            return jsonify({'error': 'Files not ready yet'}), 404
    shutil.make_archive(os.path.join(OUTPUT_DIR, job_id), 'zip', output_folder)
    # as_attachment = dialogue box asking save as
    return send_file(zip_path, as_attachment=True)

#GET /jobs/<job_id>/files/<filename> single file download 
@app.route('/jobs/<job_id>/files/<filename>',methods=['GET'])
def download_singlefile(job_id,filename):
    job = get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}) , 400
    safe_name = secure_filename(filename)
    file_path = os.path.join(OUTPUT_DIR,job_id,safe_name)
    if not os.path.exists(file_path):
        return jsonify({'error':'File not found!'}),400
    
    return send_file(file_path,as_attachment=True)

#DELETE /jobs/{job_id}
@app.route('/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    r.delete(f"Job:{job_id}")
    r.delete(f"Files:{job_id}")
    
    # Remove tree = Folder - sub Folder - files
    shutil.rmtree(os.path.join(UPLOAD_DIR,job_id),ignore_errors=True)
    shutil.rmtree(os.path.join(OUTPUT_DIR,job_id),ignore_errors=True)

    zip_path= os.path.join(OUTPUT_DIR,f"{job_id}.zip")
    if  os.path.exists(zip_path):
        os.remove(zip_path)
    return jsonify({'message': 'Job deleted successfully'}), 200



##################################################################################

if __name__ == '__main__':
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True)











    












        
