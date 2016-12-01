# controlScripts
Scripts to upload, download, restore, or reconfigure arbor instances based on Kitware's girder &amp; Flow technologies

One script (arbor_full_collection_backup.py) allows an Arbor user to create a local backup copy of all the datasets and analyses uploaded in
Arbor instance. A second script (arbor_restore_collections.py) uploads all data and analyses stored in a local backup onto
an Arbor instance.  

Since Arbor includes a password-authenticated datastore, a valid user login is required to execute backup or restore jobs. 
During a backup operation, only collections visible to the chosen login credentials will be included in the backup.  Therefore,
administrative level user authentication is recommended to perform complete backups and re-initializations of Arbor instances.

# example uses

~~~
python arbor_full_collections_backup.py -a "http://localhost:9080" -u user -p password
~~~

The above command will backup the Arbor available at the URL (http://localhost:9080) using the authentication credentials (user, password).  A backup will be written in the default locaton ($HOME/arbor/backups).  The backup will
contain the URL of the Arbor instance andthe date and time of the backup embedded in the name to give unique names to 
each backup. 

~~~
python arbor_restore_collections.py -a "http://localhost:9080" -u user -p password -d "/home/username/arbor/backups/arbor_backup_52.204.9.236_2016-11-30_19:43:49"
~~~

The above command will estore all the collections and datasets from a previously saved collection archived (stored at the 
/home/username/arbor.... URL).  This **does not** delete existing collections, the script only adds any new collections contained in the backup and/or adds datasets and analyses to an already existing collection which were present in the backup. 

~~~
python arbor_full_collections_backup.py --help
python arbor_restore_collections.py --help
~~~

Explain the command line options available for either script. 
