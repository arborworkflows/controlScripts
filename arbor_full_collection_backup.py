import requests
import time
import json
import arrow
import os 
import girder_client
import sys
import argparse


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
    print 'local save directory is ', saveRootDirectory
    print 'attempting login in as user:',arborUser, ' with password:', arborUserPassword


def performBackup():
    global arborUser
    global arborUserPassword
    global arborBaseURL
    global saveRootDirectory

    # pull the current time and use to make a subdirectory named for the time of the backup
    now = arrow.utcnow()
    backupSubDirectory =  'arbor_backup_'+arborBaseURL[7:] + '_' + now.format('YYYY-MM-DD_HH:mm:ss')
    backupDirectory = saveRootDirectory + '/' + backupSubDirectory

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

    print 'storing backups in: ',backupDirectory
    os.chdir(saveRootDirectory)

    # make empty directory for the backup
    os.mkdir(backupSubDirectory)
    os.chdir(backupDirectory)
    
    count = 0
    # get list of collections
    colls = gc.sendRestRequest('GET','collection')
    for coll in colls:
	   if coll['name'] != 'private-girder-collection':
            collID = coll['_id']
            collName = coll['name']
            print 'traversing collection:',collName

            # make a subdirectory for this collection
            collectionDirectory = backupDirectory+'/'+collName
            os.mkdir(collectionDirectory)
            

            # loop through the folders containing the items.  this is repeated for each collection.  Each analysis
            # item is written out as two files, one with only the code, the second with lu
            folders = gc.sendRestRequest('GET','folder?parentType=collection&parentId='+collID)
            for folder in folders:
                folderID= folder['_id']
                folderName = folder['name']
                
                # make directory for the folder
                folderDirectory = collectionDirectory + '/'+folderName
                os.mkdir(folderDirectory)
                os.chdir(folderDirectory)
                
                if folderName == 'Data':
                    print '    found data folder. downloading'
                    gc.downloadResource(folderID, folderDirectory, 'folder')
                elif folderName == 'Analyses':
                    # loop through analysis items and write only the analysis code as a .json file
                    items = gc.sendRestRequest('GET','item',{'folderId': folderID})
                    if len(items) > 0:
                        print '        found ',len(items), ' analyses'
                    for item in items:
                        # write each item as a separate json file.  This save is only the source code so it is readable
                        itemfilename = item['name']+'.json'
                        outfile = open(itemfilename,'w')
                        outfile.write(json.dumps(item['meta']['analysis']))
                        outfile.close()     
                        # this write is the whole item, so the age can be compared for incremental backups
                        itemfilename = 'item_'+item['name']+'.json'
                        outfile = open(itemfilename,'w')
                        outfile.write(json.dumps(item))
                        outfile.close()     
                else:
                    # loop through the items and write the entire girder item as a local json file
                    print '     found folder named',folderName
                    items = gc.sendRestRequest('GET','item',{'folderId': folderID})
                    if len(items)>0:
                        print '        found ',len(items), ' items'
                    for item in items:
                        # write each item as a separate json file
                        itemfilename = item['name']+'.json'
                        outfile = open(itemfilename,'w')
                        outfile.write(json.dumps(item))
                        outfile.close()
                                        
        


if __name__ == "__main__":
   setCommandLineOptions(sys.argv[1:])
   performBackup()

