#import sys
import os
import logging
import shutil
import sys
from datetime import datetime
from get_data import GETDATA
from process_network import PROCESS_NETWORK
from process_profiles import PROCESS_PROFILES
from process_culverts import PROCESS_CULVERTS
from process_weir import PROCESS_WEIR
from process_pumping import PROCESS_PUMPING
from process_closing import PROCESS_CLOSING
from validatietool.validatietool import validatietool
# relative path tot parent folder of script order to access model attribute_functions in folder 'json'
sys.path.append(r"..")

root_dir=os.getcwd()

output_dir = os.path.join(root_dir,"output",datetime.today().strftime("%Y%m%d"))

input_dir= os.path.join(root_dir,"projectgebied")
#provide without extension output folder will have the same name
shapefiles = ["AaOfWeerijsStroomgebied"]

checkbuffer=[0.5,5]

activities={'download':True,
           'network': False,
           'profiles':False,
           'culverts':False,
           'weirs':True,
           'pumping':False,
           'closing':False}

if os.path.exists(output_dir):
    if activities['download']:
        shutil.rmtree(output_dir, ignore_errors=True)
        os.makedirs(output_dir)
else:
    os.makedirs(output_dir)
    activities['download']=True

logging.basicConfig(filename=os.path.join(output_dir, 'logging.log'), level=logging.INFO)
logging.info('Started')

if activities['download']:
    logging.info('Start downloading data from remote server')
    #download data from remote server and apply default values on missing data
    #try:
    getdata=GETDATA(root_dir,output_dir,input_dir,shapefiles)
    getdata.run()
    logging.info('finished downloading data from remote server')
    #except:
    #    logging.error('something went wrong while downloading data')

# If the HyDAMO-valdatietool will be used, prepare the API:
for key, value in activities.items():
    if key != 'download':
        if activities[key]: # If one of the 'activities', apart from 'download', will take place: Make an object of class Validatietool             
            validatietool = validatietool(output_dir)
            break

if activities['profiles']:
    logging.info('Start processing profiles')
    #try:
        #correct the profiles
    processprofiles = PROCESS_PROFILES(output_dir,input_dir,shapefiles)
    processprofiles.run()
    logging.info('finished processing profiles')
    #except:
    #    logging.error('something went wrong while processing profiles')

if activities['network']:
    logging.info('Start processing network')
    #download data from remote server and apply default values on missing data
    #try:
        #correct the network (snap non-connected drains)
    processnetwork = PROCESS_NETWORK(output_dir,shapefiles,checkbuffer)
    processnetwork.run()
    logging.info('finished processing network')
    #except:
    #    logging.error('something went wrong while processing network')

if activities['culverts']:
    logging.info('Start processing culverts')
    #try:
        #correct the culverts
    processculverts = PROCESS_CULVERTS(output_dir,shapefiles,checkbuffer)
    processculverts.run()
    logging.info('finished processing culverts')
    #except:
    #    logging.error('something went wrong while processing culverts')

if activities['weirs']:
    # logging.info('Start processing weirs')
    # try:
        #correct the weirs
    processweir = PROCESS_WEIR(output_dir,shapefiles,checkbuffer)
    processweir.initialValidate(validatietool)
    processweir.correct()
    logging.info('finished processing weirs')
    # except:
    #     logging.error('something went wrong while processing weirs')

if activities['pumping']:
    logging.info('Start processing pumping stations')
    try:
        #correct the profiles
        processpumping = PROCESS_PUMPING(output_dir,shapefiles,checkbuffer)
        processpumping.run()
        logging.info('finished processing pumping stations')
    except:
        logging.error('something went wrong while processing pumping stations')

if activities['closing']:
    logging.info('Start processing closing mechanisms')
    #try:
        #correct the profiles
    processclosing = PROCESS_CLOSING(output_dir,shapefiles,checkbuffer)
    processclosing.run()
    logging.info('finished processing closing mechanisms')
    #except:
    #    logging.error('something went wrong while closing mechanisms')

if validatietool: # if object 'validatietool' exists...
     validatietool.run()    

logging.info('Finished')
logging.shutdown()