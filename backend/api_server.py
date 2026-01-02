from flask_cors import CORS
from flask import Flask, request, jsonify
from pathlib import Path
import json

from app import BankStatementProcessor  # importing existing logic

app = Flask(__name__)
CORS(app)

DATA_DIR = Path("data")
RAW_PDF_DIR = DATA_DIR / "raw_pdfs"
OUTPUT_JSON_DIR = DATA_DIR / "extracted_json"

RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/upload", methods=["POST"])
def upload_pdf():
    file = request.files.get("file")
    bank = request.form.get("bank")

    if not file or not bank:
        return jsonify({"error": "file and bank are required"}), 400

    pdf_path = RAW_PDF_DIR / file.filename
    file.save(pdf_path)

    return jsonify({
        "message": "PDF uploaded",
        "pdf_path": str(pdf_path),
        "bank": bank
    })


@app.route("/process", methods=["POST"])
def process_pdf():
    data = request.json
    bank = data.get("bank")
    pdf_filename = data.get("pdf_filename")

    if not bank or not pdf_filename:
        return jsonify({"error": "bank and pdf_filename required"}), 400

    processor = BankStatementProcessor()
    processor.process_single(
        bank_name=bank,
        pdf_path=RAW_PDF_DIR / pdf_filename,
        output_dir=OUTPUT_JSON_DIR
    )

    output_file = OUTPUT_JSON_DIR / f"{pdf_filename}.json"

    with open(output_file) as f:
        result = json.load(f)

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)