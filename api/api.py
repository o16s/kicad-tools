import os
import glob
import json
import zipfile
from flask import Flask, flash, request, redirect, url_for, send_from_directory, render_template
from werkzeug.utils import secure_filename
import uuid
import subprocess
import shutil

BUILD_FOLDER = 'build'
UPLOAD_FOLDER = '/projects/uploads'
PLOTS_FOLDER = BUILD_FOLDER+'/kicad-tools-plot'
BOM_FOLDER = BUILD_FOLDER+'/kicad-tools-bom'
IBOM_FOLDER = BUILD_FOLDER+'/kicad-tools-ibom'
SCHEMATIC_FOLDER = BUILD_FOLDER+'/kicad-tools-schematic'


ALLOWED_EXTENSIONS = {'zip'}


app = Flask(__name__, static_url_path=UPLOAD_FOLDER, static_folder=UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#helpers
def run_cmd(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()
    return p.returncode

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def unzip_upload(upload_path):
    filename = glob.glob(upload_path+'/*.zip')[0]
    with zipfile.ZipFile(filename, "r") as kicadZip:
        kicadZip.extractall(upload_path)

def search_filetype(type, search_path):
    results = []
    for root, dirs, files in os.walk(search_path):
        for file in files:
            if file.endswith(type) and not file.startswith("."):
                results.append((os.path.join(root, file)))
    return results

def search_kicad_project_path(search_path):
    results = search_filetype(".pro", search_path)
    return os.path.dirname(results[0])

def extract_kicad_name(input_file):
    return os.path.splitext(os.path.basename(input_file))[0]

def make_output_dirs(upload_path):
    try:
        shutil.rmtree(os.path.join(upload_path,BUILD_FOLDER), ignore_errors=True)
    except:
        pass

    try:
        os.makedirs(os.path.join(upload_path,PLOTS_FOLDER))
        os.makedirs(os.path.join(upload_path,PLOTS_FOLDER, "layout"))
        os.makedirs(os.path.join(upload_path,BOM_FOLDER))
        os.makedirs(os.path.join(upload_path,IBOM_FOLDER))
        os.makedirs(os.path.join(upload_path,SCHEMATIC_FOLDER))
        return True
    except Exception as e:
        return False

def generate_schematic_pdf(upload_path):
    schematic = search_filetype(".sch", upload_path)
    input_file = schematic[0]
    output_dir = os.path.join(upload_path, SCHEMATIC_FOLDER)

    cmd = "python -m kicad-automation.eeschema.schematic --schematic "+input_file+"  --output_dir "+output_dir+" --screencast_dir "+output_dir+" export --all_pages  -f pdf"

    kicad_name = extract_kicad_name(input_file)
    result = run_cmd(cmd)
    return result, os.path.join(output_dir, kicad_name+".pdf")

def generate_schematic_svg(upload_path):
    schematic = search_filetype(".sch", upload_path)
    input_file = schematic[0]
    output_dir = os.path.join(upload_path, SCHEMATIC_FOLDER)
    kicad_name = extract_kicad_name(input_file)

    cmd = "python -m kicad-automation.eeschema.schematic --schematic "+input_file+"  --output_dir "+output_dir+" --screencast_dir "+output_dir+" export --all_pages  -f svg"

    result = run_cmd(cmd)
    return result, os.path.join(output_dir, kicad_name+".svg")


def generate_bom(upload_path):
    schematic = search_filetype(".sch", upload_path)
    input_dir = schematic[0]
    output_dir = os.path.join(upload_path, BOM_FOLDER)

    cmd = "python -m kicad-automation.eeschema.export_bom --schematic "+input_dir+"  --output_dir "+output_dir+" --screencast_dir "+output_dir+" export"
    #return cmd
    result = run_cmd(cmd)

    return result, os.path.join(output_dir, "bom.csv")


def generate_ibom(upload_path):
    board = search_filetype(".kicad_pcb", upload_path)
    input_dir = board[0]
    output_dir = os.path.join(upload_path, IBOM_FOLDER)
    cmd = "sh /opt/InteractiveHtmlBom/make-interactive-bom-outputdir "+input_dir+" "+output_dir

    result = run_cmd(cmd)

    return result, os.path.join(output_dir, "ibom.html")


def generate_plots(upload_path):

    layout_zip_filename = "layout"
    board = search_filetype(".kicad_pcb", upload_path)
    input_dir = board[0]
    output_dir = upload_path+"/"+PLOTS_FOLDER

    cmd = "kiplot -b "+input_dir+" -c /opt/etc/kiplot/generic_plot.kiplot.yaml -v -d "+output_dir
    
    result = run_cmd(cmd)

    shutil.make_archive(output_dir+"/"+layout_zip_filename, 'zip', output_dir+"/layout")
    shutil.make_archive(output_dir+"/"+layout_zip_filename+"/gerber", 'zip', output_dir+"/layout/gerber")

    return result, os.path.join(output_dir, layout_zip_filename+".zip"), os.path.join(output_dir, layout_zip_filename+"/gerber.zip")

#routes
@app.route('/')
def version():
    return {"api_version": 0.1}

@app.route('/process/<upload_hash>', methods=['GET'])
def process(upload_hash):
    upload_path = app.config['UPLOAD_FOLDER']+"/"+upload_hash
    
    if not os.path.exists(upload_path):
        return {"error": "Upload does not exist."}
    else:
        try:
            unzip_upload(upload_path)

            #create output directories
            if make_output_dirs(upload_path):

                #generate plots (gerbers, pdfs, dxfs, svgs)
                try:
                    layout_res, layout, gerber = generate_plots(upload_path)

                    ibom_res, ibom = generate_ibom(upload_path)

                    bom_res, bom = generate_bom(upload_path)

                    schematic_pdf_res, schematic_pdf = generate_schematic_pdf(upload_path)

                    schematic_svg_res, schematic_svg = generate_schematic_svg(upload_path)

                    return {"output":{
                        "layout_result":str(layout_res),
                        "ibom_result":str(ibom_res),
                        "bom_result":str(bom_res),
                        "schematic_pdf_result":str(schematic_pdf_res),
                        "schematic_svg_result":str(schematic_svg_res),
                        "ibom_path":str(ibom),
                        "bom_path":str(bom),
                        "schematic_pdf_path":str(schematic_pdf),
                        "schematic_svg_path":str(schematic_svg),
                        "layout_path": {
                            "all": str(layout),
                            "gerber": str(gerber)
                        }
                    }}
                except Exception as e:
                    return {"error": "Generation error. "+str(e)}


            else:
                return {"error": "Could not create output directories."}


        except Exception as e:
            return {"error": "Processing error."+str(e)}


@app.route('/ibom/<upload_hash>')
def serve_ibom(upload_hash):
    return render_template(os.path.join('/project/uploads', upload_hash, IBOM_FOLDER, "ibom.html"))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            upload_hash = str(uuid.uuid4())
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER']+"/"+upload_hash+"/", filename)

            if not os.path.exists(os.path.dirname(filepath)):
                try:
                    os.makedirs(os.path.dirname(filepath))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

            file.save(filepath)
            return {"upload": upload_hash}

    return '''
    <!doctype html>
    <title>kicad-tools</title>
    <h1>Upload .zip containing .sch, .kicad_pcb, .pro</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''


if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0')