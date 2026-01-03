# BankFusion
The proposed system converts bank statements from different banks such as Axis, HDFC, and ICICI into a single standardized and reusable JSON format. The extracted and categorized data can be downloaded as JSON and reused for future analysis, dashboards, or accounting without reprocessing the original PDFs.

## Environment Variables Setup

This project requires environment variables to run.
For security reasons, `.env` files are NOT committed to Git.

### Step 1: Create backend environment file
```bash
cd backend
cp .env.example .env

cd frontend
cp .env.example .env

cd backend
python app.py
# OR
uvicorn main:app --reload

cd frontend
npm install
npm run dev
