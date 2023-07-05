from flask import Flask, render_template, request, send_file, send_from_directory
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, SelectField, StringField
from wtforms.validators import DataRequired
from compiler import Compiler
import os
from util import AHKFinder, Config
from threading import Timer

#load config
config = Config()

ahk = AHKFinder()
app = Flask(__name__)
app.config.from_pyfile('config.py')
compiler = Compiler(ahk, config)
app_dir = os.path.abspath(os.path.join(".")) + os.sep

class CodeForm(FlaskForm):
    code = TextAreaField('Code', validators=[DataRequired()])
    variant = SelectField('Select Variant', 
        choices=[
            (value['version'], value['display_name']) for value in ahk.variants
        ],
        default=[
            value['version'] for value in ahk.variants if "Script Compiler" in value['display_name']
        ][0]
    )
    compress = SelectField('Compression Level',
        choices=[
            ('0', 'No Compression'),
            ('1', 'MPRESS Compression'),
            ('2', 'UPX Compression')
        ]
    )
    resourceid = StringField('Resource ID')
    cp = StringField('Codepage')
    compile = SubmitField('Compile')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('.', 'icon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = CodeForm()
    if form.validate_on_submit():
        text = form.code.data
        compress = request.form.get("compress", "0")
        resourceid = request.form.get("resourceid", None)
        cp = request.form.get("cp", None)
        variant = request.form.get("variant", None)
        dest_file, error = compiler.compile(text, compress, variant, resourceid, cp)
        if error:
            error = str(error, "utf-8")
            if app_dir in error:
                error = error.replace(app_dir, "")
            return render_template('index.html', form=form, variants=ahk.variants, config=config.data, error=error)
        dest_name = os.path.basename(dest_file)
        response = send_file(dest_file, as_attachment=True, download_name=dest_name)
        if not config.data['compile']['cache']:
            delete_file(dest_file)  # Schedule the file deletion
        return response
    return render_template('index.html', form=form, variants=ahk.variants, config=config.data)

def delete_file(file_path, delay=5):
    # Delay the file deletion by 10 seconds
    timer = Timer(delay, os.remove, args=(file_path,))
    timer.start()

if __name__ == "__main__":
    app.run(debug=True)
