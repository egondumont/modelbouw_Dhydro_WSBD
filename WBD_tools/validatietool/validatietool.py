import requests
import logging
import os
import time
import json
from datetime import datetime
# API methodes uit https://hkvconfluence.atlassian.net/wiki/spaces/VAL/pages/1993801746/Voorbeelden+gebruik+API
class validatietool:
    def __init__(self,output_dir):
        self.gebruikersnaam ="e.dumont@brabantsedelta.nl"
        self.wachtwoord = "qh6%tSjrryd_"
        self.firebase_url = "https://identitytoolkit.googleapis.com/v1"
        self.firebase_key = "AIzaSyAU17otJko594SYoCulCPfXwkHOXQEieXE"
        self.server = "https://validatie-api.hydamo.nl"
        self.root_dir=os.getcwd()
        self.output_dir = output_dir
        self.rules=os.path.join(self.root_dir,"validatietool","ValidationRules.json")
        self.hydamo_cert=os.path.join(self.root_dir,"validatietool","HyDAMOValidatietoolCertificaat.pem") # set path+name of validation tool certificate file (pem file)

        try:
            # log into API 
            response = requests.post(f"{self.firebase_url}/accounts:signInWithPassword?key={self.firebase_key}", data={'email': self.gebruikersnaam, 'password': self.wachtwoord, 'returnSecureToken': 'true'})
            # werkt alleen als response.status_code == 200
            id_token = response.json()['idToken']
            self.bearerToken = {'Authorization': f"Bearer {id_token}"}
        except:
            logging.error(f"verzoek om token aan Google APIs is mislukt. Response-status was {response.status_code}")

        try:
            # Make validation-task
            self.taskName = datetime.today().strftime("%d%b%Y_%H:%M")
            response = requests.post(f"{self.server}/tasks/{self.taskName}", headers=self.bearerToken, verify=self.hydamo_cert)
            # werkt alleen als response.status_code == 201
            self.taskID = response.json()["id"]
        except:
            logging.error(f"Creation of new task failed. Response-status was {response.status_code}")

        try:
            # Add validation rules to task
            params = {"file":os.path.basename(self.rules).split('/')[-1]} # JSON file with validation rules
            files = {"file":open(self.rules,"rb")}
            response = requests.post(f"{self.server}/task/{self.taskID}/validationrules",files=files,params=params,headers=self.bearerToken, verify=self.hydamo_cert)
        except:
            logging.error(f"Adding validation rules to validation task {self.taskID} failed. Response-status was {response.status_code}")
    
    def addData(self,file_path,dataset):
        # add DAMO-object to validation task
        params = {"file": dataset}
        files = {"file": open(os.path.join(file_path,dataset), "rb")}
        response = requests.post(f"{self.server}/task/{self.taskID}/datasets", files=files, params=params, headers=self.bearerToken, verify=self.hydamo_cert)
        # werkt alleen als response.status_code == 201
        if response.status_code != 201:
            logging.error(f"Dataset {dataset} uploaden naar validatietaak {self.taskName} is mislukt. Response-status was {response.status_code}")

    def run(self):
        # start the validation task for all processed DAMO-objects
        format = "geopackage"
        response_execute_task = requests.post(f"{self.server}/task/{self.taskID}/execute/{format}", headers=self.bearerToken, verify=self.hydamo_cert) 
        if response_execute_task.status_code == 202:
            print("Validation task is started")
            #controleer de status van de validatie-taak (periodiek)
            response_get_task = requests.get(f"{self.server}/task/{self.taskID}", headers=self.bearerToken, verify=self.hydamo_cert) 
            if response_get_task.status_code == 200:
                status = str(response_get_task.json()["status"]) 
                while not (status == "finished" or status == "error"):
                    response_get_task = requests.get(f"{self.server}/task/{self.taskID}", headers=self.bearerToken, verify=self.hydamo_cert)
                    if response_get_task.status_code == 200:
                        status = str(response_get_task.json()["status"])
                        print(f"status taak: {status}")
                        time.sleep(60)
        else:
            logging.error(f"Starten van validatietaak {self.taskName} is mislukt. Response-status was {response_execute_task.status_code}")
        
        # download metadata of validation
        result_folder = os.path.join(self.output_dir,"validatietool")
        response_get_metadata = requests.get(self.server + '/task/' + str(self.taskID) + '/result/metadata', headers=self.bearerToken, verify=self.hydamo_cert)
        if response_get_metadata.status_code == 200:
            if not os.path.exists(result_folder):
                os.makedirs(result_folder)
            open(os.path.join(result_folder,f"{self.taskID}_metadata.json"), 'wb').write(response_get_metadata.content)

        # download geopackage with all validation results
        response_get_results_geopackage = requests.get(self.server + '/task/' + str(self.taskID) + '/result/geopackage', headers=self.bearerToken, verify=self.hydamo_cert)
        if response_get_results_geopackage.status_code == 200:
            open(os.path.join(result_folder,"validationresults.gpkg"), 'wb').write(response_get_results_geopackage.content)

    def getColumnNames(self,index):
        # Get list of columns of GPKG-output of Validatietool with validation results for the object with index 'index' in the validatietool json,
        # except syntax validation nor validation summaries
        with open(self.rules) as f:
            obj = json.load(f)
        columnNames = []
        for i, rule in enumerate(obj['objects'][index]["validation_rules"]):
            columnNames.append(rule[i-1]["id"]+rule[i-1]["name"])
        return columnNames 