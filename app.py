from flask import Flask, jsonify, request, send_file ,render_template
from flask_cors import CORS
import redis # connection to store data 
import json
import os
import uuid  # generates unique id 
import shutil #Delets folder
import fitz  # PyMuPDF
from rq import Queue 
from task import r , save_job ,convert_pdf,get_job
from werkzeug.utils import secure_filename 
import time

app=Flask(__name__)
CORS(app)

# Redis connection 
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
# queue of jobs 
q = Queue(connection=r)

# Directories to store files
UPLOAD_DIR = 'uploads'
OUTPUT_DIR= 'output'

# API routes to render html file 

@app.route('/')
def serve():
    return render_template('index.html')

# genertaes unique job id
def generate_job_id():
    return str(uuid.uuid4())

 # fetch files in job if job exists
def get_files(job_id):
    g_file=r.get(f"Files:{job_id}")
    if g_file:
        return json.loads(g_file)
    else:
        return []
    
# validate if pdf is corrupted or password protected
# with fitz - pyMUPDF 
def validate_pdf(file):
     try:
        # read till end of pdf
        pdf_bytes = file.read()
        # cursor reset to 0
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
    # flask component imported
    file = request.files.getlist('files')

    if len(file)==0:
        return jsonify({'error':'No file Uploaded'}),400 # Not found error code
    # Upload limit check : Max 100 files 
    if len(file) >100:
        return jsonify({'error':'Can not Upload more than 100 files'}),400
    

    #unique job id 
    job_id = generate_job_id()
    # folder path like : 'uploads/a1b2c3d4' 
    job_folder = os.path.join(UPLOAD_DIR, job_id)
    # Folder creation    |  if already exists continue
    os.makedirs(job_folder, exist_ok=True)


    accepted=0
    rejected=[]

    for f in file :
        #Move cursor to the end of file
        f.seek(0,os.SEEK_END)
        #Current position of cursor
        size = f.tell()
        f.seek(0)
        
        # check pdf formate
        if not f.filename.lower().endswith('.pdf'):
            rejected.append({'filename':f.filename,'reason':'Not a pdf'})
            continue
        
        # File size check : Max 100MB
        # 1MB = 1024KB = 1024 *1024 byte
        if size >= 100*1024*1024:
            rejected.append({'filename':f.filename,'reason':'Exceeded 100MB'})
            continue
        #Check protected files
        valid, reason = validate_pdf(f)
        if not valid:
            rejected.append({'filename':f.filename,'reason': reason})
            continue
        safe_name = secure_filename(f.filename)
        f.save(os.path.join(job_folder,safe_name))
        accepted+=1

    if accepted==0:
         #if no file accepted delete created folder
         shutil.rmtree(job_folder, ignore_errors=True)
         return jsonify({'error': 'No valid files uploaded', 'rejected': len(rejected)}), 400
    save_job(job_id,{'status':'queued','total_files':len(file),'succeeded':0,'failed':0,'rejected' : rejected })
    q.enqueue(convert_pdf, job_id)

    return jsonify({'job_id': job_id, 'status': 'queued','rejected':rejected,'accepted':accepted}), 202


#GET /jobs/{job_id}
@app.route('/jobs/<job_id>',methods =['GET'])
def check_conversion_status(job_id):
    Job = get_job(job_id)
    if not Job:
        return jsonify({'error':'Job not Found'}),404
    # ** unpack to use data.status
    # data = {'job_id': job_id, **Job}
    time.sleep(2)
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
    #create zip folder
    shutil.make_archive(os.path.join(OUTPUT_DIR, job_id), 'zip', output_folder)
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
    
    # Remove tree = Folder - sub Folder - files
    shutil.rmtree(os.path.join(UPLOAD_DIR,job_id),ignore_errors=True)
    shutil.rmtree(os.path.join(OUTPUT_DIR,job_id),ignore_errors=True)

    zip_path= os.path.join(OUTPUT_DIR,f"{job_id}.zip")
    if  os.path.exists(zip_path):
        os.remove(zip_path)

    return jsonify('Job deleted successfully') ,202



##################################################################################

if __name__ == '__main__':
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True)











    












        
