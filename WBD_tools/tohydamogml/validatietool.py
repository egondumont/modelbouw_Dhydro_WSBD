import requests
import logging
import os
from datetime import datetime

class validatietool:
	def __init__(self):
		self.gebruikersnaam ="e.dumont@brabantsedelta.nl"
		self.wachtwoord = "qh6%tSjrryd_"
		self.firebase_url = "https://identitytoolkit.googleapis.com/v1"
		self.firebase_key = "AIzaSyAU17otJko594SYoCulCPfXwkHOXQEieXE"
		self.server = "https://validatie-api.hydamo.nl"
		self.rules
		root_dir=os.getcwd()
		# set path+name of validation tool certificate file (pem file)
		for file in os.listdir(os.path.join(root_dir,"input")):
			# check the files which end with extension 'pem'
			if file.endswith(".pem"):
				self.hydamo_cert = os.path.join(root_dir,"input", file)
				break

		# Make token to login to Validatietool
		try:
			response = requests.post(f"{self.firebase_url}/accounts:signInWithPassword?key={self.firebase_key}", data={'email': self.gebruikersnaam, 'password': self.wachtwoord, 'returnSecureToken': 'true'})
			# werkt alleen als response.status_code == 200
			id_token = response.json()['idToken']
			self.bearerToken = {'Authorization': f"Bearer {id_token}"}
		except:
			logging.error(f"verzoek om token aan Google APIs is mislukt. Response-status was {response.status_code}")

		# Make new validation task
		try:
			self.taskName = datetime.today().strftime("%d%b%Y_%H:%M")
			response = requests.post(f"{self.server}/tasks/{self.taskName}", headers=self.bearerToken, verify=self.hydamo_cert)
			# werkt alleen als response.status_code == 201
			self.taakID = response.json()["id"]
		except:
			logging.error(f"Creation of new task failed. Response-status was {response.status_code}")

	# Add data to validation task	
	def addData(self,file_path,dataset):
		params = {"file": dataset}
		files = {"file": open(os.path.join(file_path,dataset), "rb")}
		response = requests.post(f"{self.server}/task/{self.taakID}/datasets", files=files, params=params, headers=self.bearerToken, verify=self.hydamo_cert)
		# werkt alleen als response.status_code == 201
		if response.status_code != 201:
			logging.error(f"Dataset {dataset} uploaden naar validatietaak {self.taskName} is mislukt. Response-status was {response.status_code}")