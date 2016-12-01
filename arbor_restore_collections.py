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
arborBaseURL = 'http://52.204.46.78'

# what is the root directory to store backups in
userHomeDirectory = os.path.expandvars("$HOME")
saveRootDirectory = userHomeDirectory+'/arbor/backups'

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

    #print 'number of arguments ',len(sys.argv)
    #print 'argument list:',str(sys.argv)

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

    print 'Arbor URL is ', arborBaseURL
    #print 'local save directory is ', saveRootDirectory
    print 'attempting login in as user:',arborUser, ' with password:', arborUserPassword


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
        print ''
        print 'Error: '
        print 'Unable to login to the Arbor instance.  Please try another user/password.'
        print 'Use the command option "--help" to see how to specify a different user.'
        return

    print 'reading backup from: ',saveRootDirectory
    os.chdir(saveRootDirectory)
    
    count = 0
    # get list of collections in the backup

    collNameList = [f for f in os.listdir(saveRootDirectory) if isdir(join(saveRootDirectory, f))]
    #print 'collections found in backup:',collNameList

    for coll in collNameList:
        # don't accidently restore a private girder collection
        if (coll != 'private-girder-collection'):
            collName = coll
            print 'traversing collection:',collName

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
                print 'creating collection',collName
                newcollinfo = gc.createCollection(collName,description='',public=False)
                collID = newcollinfo['_id']

            folders = [f for f in os.listdir(collectionDirectory) if isdir(join(collectionDirectory, f))]
            for folder in folders:
                folderName = folder
                folderDirectory = collectionDirectory + '/'+ folderName
                if folderName == 'Data':
                    print '    found data folder. uploading'
                    # this works, so comment out for now
                    #gc.upload(folderDirectory, collID, parentType='collection', leafFoldersAsItems=False, reuseExisting=True, blacklist=None, dryRun=False)
                elif folderName == 'Analyses':
                    print '     found Analyses folder'

                    # check if the folder exists in Arbor, and create it if necessary
                    try:
                        record = gc.resourceLookup('/collection/'+collName+'/'+folderName)
                        folderID = record['_id']
                    except girder_client.HttpError:
                        # didn't find the folder, so create it
                        print 'creating folder ',folderName
                        newfolderinfo = gc.createFolder(collID,folderName,description='',parentType='collection',public=False)
                        folderID = newfolderinfo['_id']


                    # loop through analysis items and create girder items with the analysis code assigned as metadata
                    os.chdir(folderDirectory)
                    foundItems = [f for f in os.listdir(folderDirectory) if isfile(join(folderDirectory, f))]
                    print 'listing items in this folder:'
                    for itemfile in foundItems:
                        # the backup format lists each analysis twice.  The full item information (including previous item number, date created
                        # etc. are stored in a json file entitled item_<analysis name>.  Then the analysis code only is in a second json
                        # filed titled <analysis name>.json.  We only want to create one item for each analysis, so filter out the files that
                        # start with 'item_'
                        if itemfile[:5] != 'item_':
                            print '    ',itemfile
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
                                print 'creating item ',itemName
                                newiteminfo = gc.loadOrCreateItem(itemName,folderID,reuseExisting=True)
                                itemID = newiteminfo['_id']

                                # read the JSON file from the local disk and add this analysis definition as metadata to the item
                                readfile = open(itemfile,'r')
                                jsonRecord = json.loads(readfile.read())
                                print jsonRecord
                                print 'adding metadata to item',itemName
                                metaReturn = gc.addMetadataToItem(itemID, {'analysis': jsonRecord})
                                readfile.close()

   
                else:
                    # loop through the items and write the entire girder item as a local json file
                    print '     found folder named',folderName
                    print '        not handling this folder type yet'
                    '''
                    items = gc.sendRestRequest('GET','item',{'folderId': folderID})
                    if len(items)>0:
                        print '        found ',len(items), ' items'
                    for item in items:
                        # write each item as a separate json file
                        itemfilename = item['name']+'.json'
                        outfile = open(itemfilename,'w')
                        outfile.write(json.dumps(item))
                        outfile.close()
                    '''
                                        
        


if __name__ == "__main__":
   setCommandLineOptions(sys.argv[1:])
   performUpload()

