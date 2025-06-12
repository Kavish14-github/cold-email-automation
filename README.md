py -3.10 -m venv env
.\env\Scripts\activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt


uvicorn api.main:app --reload
