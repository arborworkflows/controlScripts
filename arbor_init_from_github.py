import requests
import time
import json
import arrow
import os 
import girder_client
import sys
import argparse
from os.path import isfile, isdir, join



# *** change the top constants to select the arbor address, login user, and local file location to store
# *** the collection contents

# what arbor instance should we back up?
arborBaseURL = 'http://localhost:8080'

# what is the root directory to store backups in
userHomeDirectory = os.path.expandvars("$HOME")
saveRootDirectory = userHomeDirectory+'/arborCollections'

# specify the defaul user and password.  this must be an "admin" user to copy all collections
arborUser = 'username'
arborUserPassword = 'password'

# review any arguments and possibly over-write the defaults  
# see https://www.tutorialspoint.com/python/python_command_line_arguments.htm
# 
# usage:
#       arbor_full_backup [-a | --arbor <arborURL> ]  [-d | --dir <local directory to save to> ] 
#                            [-u | --user <login user>] [-p | --password <user password>]


def setCommandLineOptions(argv):
    global arborBaseURL
    global saveRootDirectory
    global arborUser
    global arborUserPassword

    parser = argparse.ArgumentParser()
    parser.add_argument("-u","--user",help="Arbor user name to use for login",default=arborUser)
    parser.add_argument("-p","--password",help="Arbor user password",default=arborUserPassword)
    parser.add_argument("-a","--arbor",help="URL to to use for backup",default=arborBaseURL)
    parser.add_argument("-d","--dir",help="existing directory in which to store the backup ",default=saveRootDirectory)
    args = parser.parse_args()

    arborBaseURL = args.arbor
    arborUser = args.user
    saveRootDirectory = args.dir
    arborUserPassword = args.password

    print ('Arbor URL is ', arborBaseURL)
    #print 'local save directory is ', saveRootDirectory
    print('attempting login in as user:',arborUser, ' with password:', arborUserPassword)


def performUpload():
    global arborUser
    global arborUserPassword
    global arborBaseURL
    global saveRootDirectory

   
    # make a link to the Arbor girder instance
    girderApiURL = arborBaseURL+'/girder/api/v1'
    gc = girder_client.GirderClient(apiUrl=girderApiURL)
    try:
        login = gc.authenticate(arborUser, arborUserPassword )
    except girder_client.AuthenticationError:
        print( '')
        print( 'Error: ')
        print( 'Unable to login to the Arbor instance.  Please try another user/password.')
        print( 'Use the command option "--help" to see how to specify a different user.')
        return

    print( 'reading content from: ',saveRootDirectory)
    os.chdir(saveRootDirectory)
    
    count = 0

    # get list of collections in the backup. some directories aren't the standard organizaiton, so
    # remove directories that don't match the standard organization.  Also, ignore any directory names that 
    # start with a dot (.) because these were added by git or some other tool.

    exceptionDirectories = ['fxrPrototypes']
    collNameList = [f for f in os.listdir(saveRootDirectory) if (isdir(join(saveRootDirectory, f)) and (f not in exceptionDirectories) and (f[0] != '.'))]

    for coll in collNameList:
        # don't accidently restore a private girder collection
        if (coll != 'private-girder-collection'):
            collName = coll
            print( 'traversing collection:',collName)

            # make a subdirectory for this collection
            collectionDirectory = saveRootDirectory+'/'+collName
            os.chdir(collectionDirectory)
            
            # loop through the folders containing the items.  this is repeated for each collection.  First
            # check if the collection exists and return the ID.  If it doesn't exist, create it

            try:
                record = gc.resourceLookup('/collection/'+collName)
                collID = record['_id']
            except girder_client.HttpError:
                # didn't find the collection, so create it
                print ('creating collection',collName)
                newcollinfo = gc.createCollection(collName,description='',public=True)
                collID = newcollinfo['_id']

            # create the needed subfolders that Arbor anticipates 
            folderNameList = ['Analyses','Data','Visualizations']
            for fname in folderNameList:
                folderName = fname
                try:
                    record = gc.resourceLookup('/collection/'+collName+'/'+fname)
                    folderID = record['_id']
                except girder_client.HttpError:
                    # didn't find the folder, so create it
                    print('creating folder',fname)
                    newfolderinfo = gc.createFolder(collID,fname,description='',parentType='collection',public=True)
                    folderID = newfolderinfo['_id']

	    # now set girder back to the Analyses folder to add analyses
            record = gc.resourceLookup('/collection/'+collName+'/Analyses')
            folderID = record['_id']

            # loop through analysis items and create girder items with the analysis code assigned as metadata.
	    # we explicitly exclude files starting with a dot (.) or named README.* because no valid 
	    # analyses or methods will # have these file names

            folderName = 'Analyses'
            folderDirectory =  saveRootDirectory+'/'+collName
            foundItems = [f for f in os.listdir(folderDirectory) if (isfile(join(folderDirectory, f)) and (f[0] != '.')and (f[0:6] != 'README')) ]

            print('listing items in this folder:')
            for itemfile in foundItems:
                # the backup format lists each analysis twice.  The full item information (including previous item number, date created
                # etc. are stored in a json file entitled item_<analysis name>.  Then the analysis code only is in a second json
                # filed titled <analysis name>.json.  We only want to create one item for each analysis, so filter out the files that
                # start with 'item_'
                if itemfile[:5] != 'item_':
                    # clear out the filetype (json) at the end of the name
                    itemName = itemfile.replace('.json','')

                    # now look for this item in Arbor, and create it if necessary.  
                    #  TODO: *** if item exists, compare creation dates stored in the item_xxxx.json and update if the 
                    #     item date is newer than the Arbor item.  Currently we create only if an item of the same name doesn't exist (be safe)

                    # check if the item exists in Arbor, and create it if necessary
                    try:
                        record = gc.resourceLookup('/collection/'+collName+'/'+folderName+'/'+itemName)
                        itemID = record['_id']
                    except girder_client.HttpError:
                        # didn't find the item, so create it
                        newiteminfo = gc.loadOrCreateItem(itemName,folderID,reuseExisting=True)
                        itemID = newiteminfo['_id']

                        # read the JSON file from the local disk and add this analysis definition as metadata to the item
                        readfile = open(itemfile,'r')
                        try:
                            jsonRecord = json.loads(readfile.read())
                            metaReturn = gc.addMetadataToItem(itemID, {'analysis': jsonRecord})
                            readfile.close()
                        except:
                            print('could not process ',itemName)
   


if __name__ == "__main__":
   setCommandLineOptions(sys.argv[1:])
   performUpload()

