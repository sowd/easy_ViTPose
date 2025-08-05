import os
import subprocess
import tempfile
from flask import Flask, request, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)

# アップロードされたファイルを保存する一時ディレクトリ
UPLOAD_FOLDER = 'tmp'
# コマンドの出力先
OUTPUT_CSV = 'output/output.csv'

# 許可する拡張子
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['POST'])
def upload_file():
    # ファイルがリクエストに含まれているかチェック
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']

    # ファイル名が空の場合
    if file.filename == '':
        return 'No selected file', 400

    if file and allowed_file(file.filename):
        # ファイル名を安全な名前に変換
        filename = secure_filename(file.filename)
        
        # 一時フォルダにファイルを保存
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # コマンド実行
        try:
            command = [
                'python3', 'run.py',
                '-ep', 'cuda',
                '-v', filepath,
                '-csv', OUTPUT_CSV
            ]
            
            # subprocess.runでコマンドを実行
            # check=Trueで、コマンドがエラーを返した場合に例外が発生
            subprocess.run(command, check=True)
            
            # 処理が完了したらCSVファイルをクライアントに返す
            return send_file(
                OUTPUT_CSV,
                mimetype='text/csv',
                as_attachment=True,
                download_name='result.csv'
            )

        except subprocess.CalledProcessError as e:
            # コマンド実行中にエラーが発生した場合
            return f"Command execution failed: {e}", 500
        except FileNotFoundError:
            # run.pyやoutput.csvが見つからない場合
            return f"File not found: {e}", 500
        finally:
            # 処理が終了したらアップロードした動画ファイルを削除
            os.remove(filepath)
    
    return 'Invalid file type', 400

if __name__ == '__main__':
    # 開発用サーバーを起動
    app.run(debug=True, host='0.0.0.0', port=8000)