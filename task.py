import redis
import json
import os
import shutil
from datetime import timedelta
from rq import Queue
from pdf2docx import Converter

# Redis + Queue yahan define hoga (app.py isko import karega)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
q = Queue(connection=r)

UPLOAD_DIR = 'uploads'
OUTPUT_DIR = 'output'


def save_job(job_id , data):
    # set value in redit (key , value)  | json.deumps = convert dictionary in string 
    r.set(f"Job:{job_id}",json.dumps(data))

def  save_files(job_id , files_list):
    r.set(f"Files:{job_id}",json.dumps(files_list))


def convert_pdf(job_id):

    upload_folder = os.path.join(UPLOAD_DIR, job_id)
    output_folder = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(output_folder, exist_ok=True)

    converted = []
    succeded = 0
    failed = 0

    # listdir(upload_folder) = list files of upload folder
    for filename in os.listdir(upload_folder):
        # paths 
        pdf_path = os.path.join(upload_folder, filename)
        docx_name = filename.replace('.pdf', '.docx')
        docx_path = os.path.join(output_folder, docx_name)

        try:
            # convert using pdf2docx
            cv = Converter(pdf_path)
            cv.convert(docx_path)
            cv.close()

            converted.append({'output_name': docx_name, 'size_bytes': os.path.getsize(docx_path)})
            succeded += 1

        except Exception as e:
            print(f"Failed to convert {filename}: {e}")
            failed += 1

    save_files(job_id, converted)
    save_job(job_id, {
        'status': 'completed', 'total_files': succeded + failed, 'succeeded': succeded, 'failed': failed
    })

    q.enqueue_in(timedelta(hours=1), cleanup, job_id)


def cleanup(job_id):
    r.delete(f"Job:{job_id}")
    r.delete(f"Files:{job_id}")
    
    # Remove tree = Folder - sub Folder - files
    shutil.rmtree(os.path.join(UPLOAD_DIR,job_id),ignore_errors=True)
    shutil.rmtree(os.path.join(OUTPUT_DIR,job_id),ignore_errors=True)

    zip_path= os.path.join(OUTPUT_DIR,f"{job_id}.zip")
    if  os.path.exists(zip_path):
        os.remove(zip_path)

    print("Auto cleanedup Job : {job_id}")