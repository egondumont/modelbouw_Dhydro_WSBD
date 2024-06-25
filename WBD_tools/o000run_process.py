#import sys
import os
import logging
import shutil
from datetime import datetime
from get_data import GETDATA
from process_network import PROCESS_NETWORK
from process_profiles import PROCESS_PROFILES
from process_culverts import PROCESS_CULVERTS
from process_weir import PROCESS_WEIR
from process_pumping import PROCESS_PUMPING
from process_closing import PROCESS_CLOSING

root_dir=os.getcwd()

output_dir = os.path.join(root_dir,"output",datetime.today().strftime("%Y%m%d"))

input_dir= os.path.join(root_dir,"projectgebied")
#provide without extension output folder will have the same name
#shapefiles = ["dijkring34","dijkring35"]
shapefiles = ["dijkring35"]

checkbuffer=[0.5,5] #testcomment

activities={'download':True,
           'network':True,
           'profiles':True,
           'culverts':True,
           'weirs':True,
           'pumping':True,
           'closing':True}

if os.path.exists(output_dir):
    if activities['download']:
        shutil.rmtree(output_dir)
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
    processweir.run()
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

logging.info('Finished')
logging.shutdown()