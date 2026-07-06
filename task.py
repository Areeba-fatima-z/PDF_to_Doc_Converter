import redis
import json
import os
from rq import Queue
from pdf2docx import Converter
import time


r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
q = Queue(connection=r)

UPLOAD_DIR = 'uploads'
OUTPUT_DIR = 'output'

# fetch job information if it exists
def get_job(job_id):
    g_job = r.get(f"Job:{job_id}")
    if g_job :
        #json.loads () convert string into dictionary 
        return json.loads(g_job)
    else:
        return None 
 

def save_job(job_id , data):
    # set value in redit (key , value)  | json.deumps = convert dictionary in string 
    r.set(f"Job:{job_id}",json.dumps(data))

def  save_files(job_id , files_list):
    r.set(f"Files:{job_id}",json.dumps(files_list))


def convert_pdf(job_id):
    upload_folder = os.path.join(UPLOAD_DIR, job_id)
    output_folder = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(output_folder, exist_ok=True)

    all_files=os.listdir(upload_folder)
    total=len(all_files)

    current = get_job(job_id)
    rejected=current.get('rejected',[])
    converted = []
    succeded = 0
    failed = 0
    save_job(job_id, {
        'status': 'processing', 'total_files': succeded + failed, 'succeeded': succeded, 'failed': failed,'rejected': rejected
    })

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
        time.sleep(2)
        save_job(job_id, {'status': 'processing', 'total_files': succeded + failed, 'succeeded': succeded, 'failed': failed,'rejected': rejected })

    save_files(job_id, converted)
    time.sleep(5)
    save_job(job_id, {
        'status': 'completed', 'total_files': succeded + failed, 'succeeded': succeded, 'failed': failed,'rejected': rejected
    })


