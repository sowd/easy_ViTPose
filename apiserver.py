import os
import subprocess
import tempfile
from pathlib import Path
import http.server
import socketserver
import cgi # multipart/form-data の解析に使用
import re

# --- 元のプログラムから流用する設定と関数 ---

# アップロードされたファイルを保存する一時ディレクトリ
UPLOAD_FOLDER = '/home/hoikutech/tmp'
# コマンドの出力先
OUTPUT_FOLDER = '/home/hoikutech/output/'
OUTPUT_JSON = os.path.join(OUTPUT_FOLDER,'output_result.json')
# 許可する拡張子
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}

# 必要なディレクトリを作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def change_filename_to_output(path_str: str) -> str:
  """
  パスのファイル名部分のみを'output'に変更
  """
  if not path_str:
    return ""
  p = Path(path_str)
  new_name = 'output' + p.suffix
  new_path_obj = p.with_name(new_name)
  return str(new_path_obj)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# werkzeug.utils.secure_filename の簡易的な代替関数
_filename_ascii_strip_re = re.compile(r'[^A-Za-z0-9_.-]')
def simple_secure_filename(filename):
    filename = str(filename)
    # 不正な文字をアンダースコアに置換し、前後の不要な文字を削除
    secure_name = str(_filename_ascii_strip_re.sub('_', filename)).strip('._')
    return secure_name if secure_name else 'unsafe_filename'


# --- http.server を使ったサーバーの実装 ---

class MyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    POSTリクエストを処理するためのカスタムハンドラ
    """

    def do_POST(self):
        # multipart/form-data のヘッダーを解析
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type']}
        )

        # ファイルがリクエストに含まれているかチェック
        if 'file' not in form:
            self.send_error_response(400, 'No file part')
            return

        file_item = form['file']

        # ファイル名が空の場合
        if not file_item.filename:
            self.send_error_response(400, 'No selected file')
            return

        filepath = None # finallyブロックで使うため、先に定義
        try:
            if file_item.file and allowed_file(file_item.filename):
                # ファイル名を安全な名前に変換
                secure_name = simple_secure_filename(file_item.filename)
                filename = change_filename_to_output(secure_name)
                
                # 一時フォルダにファイルを保存
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_item.file.read())

                # --- コマンド実行 ---
                try:
                    command = [
                        'python3','inference.py',
                        '--input', filepath,
                        '--output-path', OUTPUT_FOLDER, '--model',
                        './vitpose-s-wholebody.pth',
                        '--yolo', 'models/yolov8l.pt',
                        '--model-name', 's', '--save-json'
                    ]
                    
                    # subprocess.runでコマンドを実行
                    subprocess.run(command, check=True)
                    
                    # 処理が完了したらJSONファイルをクライアントに返す
                    self.send_file_response(
                        OUTPUT_JSON,
                        mimetype='application/json',
                        download_name='result.json'
                    )

                except subprocess.CalledProcessError as e:
                    self.send_error_response(500, f"Command execution failed: {e}")
                except FileNotFoundError as e:
                    self.send_error_response(500, f"File not found during command execution: {e}")
                
                return # 処理完了

            else:
                self.send_error_response(400, 'Invalid file type')
        
        finally:
            # 処理が終了したらアップロードした動画ファイルを削除
            if filepath and os.path.exists(filepath):
                os.remove(filepath)

    def send_error_response(self, code, message):
        """エラーレスポンスを送信するヘルパー関数"""
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))

    def send_file_response(self, path, mimetype, download_name):
        """ファイルレスポンスを送信するヘルパー関数"""
        if not os.path.exists(path):
            self.send_error_response(404, 'Result file not found.')
            return
            
        try:
            with open(path, 'rb') as f:
                file_content = f.read()

            self.send_response(200)
            self.send_header('Content-Type', mimetype)
            self.send_header('Content-Length', str(len(file_content)))
            self.send_header('Content-Disposition', f'attachment; filename="{download_name}"')
            self.end_headers()
            self.wfile.write(file_content)
        except Exception as e:
            self.send_error_response(500, f"Failed to send file: {e}")


def run_server(port=8000):
    """サーバーを起動する"""
    host = '0.0.0.0'
    with socketserver.TCPServer((host, port), MyHTTPRequestHandler) as httpd:
        print(f"Serving at http://{host}:{port}")
        httpd.serve_forever()


if __name__ == '__main__':
    run_server()