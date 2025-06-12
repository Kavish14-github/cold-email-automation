py -3.10 -m venv env
.\env\Scripts\activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt


uvicorn api.main:app --reload

git add .
git commit -m "Push final working version with upload resume endpoint"
git push origin main