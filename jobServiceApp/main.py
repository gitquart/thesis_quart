#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 12 13:13:25 2020

@author: quart

Important data to develop the code:

-Link to get thesis of any period ( ID changes only):     
https://sjf.scjn.gob.mx/SJFSist/Paginas/DetalleGeneralV2.aspx?ID=#&Clase=DetalleTesisBL&Semanario=0

"""

import json
import time
from selenium import webdriver
from bs4 import BeautifulSoup
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import os
#import writeFile as wf
#from pymongo import MongoClient



#Global variables

msg_error="Custom Error"
thesis_id=[ 'lblTesisBD','lblInstancia','lblFuente','lblLocMesAño','lblEpoca','lblLocPagina','lblTJ','lblRubro','lblTexto','lblPrecedentes']
thesis_class=['publicacion']
precedentes_list=['francesa','nota']
#Standard top limit=2021819
#Standard bottom limit 159803
#Limit for 9th period 2 000 000 (it is supplied in main function)
lim_top_fijo=2021819
lim_bot_fijo=159803
thesis_added=False
appPath='/app/jobServiceApp/'

#Chrome configuration
chrome_options= webdriver.ChromeOptions()
chrome_options.binary_location=os.environ.get("GOOGLE_CHROME_BIN")
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")

browser=webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"),chrome_options=chrome_options)

#End of chrome configuration


def main():
    print('Main program of Quart...9th period ahead')
    res=readUrl(2,0,2000000)
    print(res)  
    print("Main program is done")
    
"""
readUrl

Reads the url from the jury web site
"""

def readUrl(sense,l_bot,l_top):
    
    res=''
    #Can use noTesis as test variable too
    noTesis=0
    #Import JSON file
    print('Starting process...')
    print('Only uploaded thesis will appear...')
    
    if l_top==0:
        l_top=lim_top_fijo
    if l_bot==0:
        l_bot=lim_bot_fijo
    
    with open(appPath+'thesis_json_base.json') as f:
        json_thesis = json.load(f)
          
    #Onwars for    
    if(sense==1):
        for x in range(l_bot,l_top):
            res=prepareThesis(x,json_thesis)
            if(res!=''):
                #Upload thsis to Cassandra
                thesis_added=cassandraBDProcess(res)  
                if thesis_added==True:
                    noTesis=noTesis+1
                    print('Thesis ready: ',noTesis, "-ID: ",x)
                    #if noTesis==3:
                     #   break
    #Backwards For             
    if(sense==2):
        for x in range(l_top,l_bot,-1):
            res=prepareThesis(x,json_thesis)
            if(res!=''):
                #Upload thsis to Cassandra
                thesis_added=cassandraBDProcess(res)  
                if thesis_added==True:
                    noTesis=noTesis+1
                    print('Thesis ready: ',noTesis, "-ID: ",x)
                    #if noTesis==3:
                     #   break 
                                   
    browser.quit()  
    
    return 'It is all done'
    
def checkRows():
    #Connect to Cassandra
    objCC=CassandraConnection()
    cloud_config= {
        'secure_connect_bundle': appPath+'secure-connect-dbquart.zip'
    }
    
    auth_provider = PlainTextAuthProvider(objCC.cc_user,objCC.cc_pwd)
    cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
    session = cluster.connect()
    session.default_timeout=1000
    session.default_fetch_size=500
    

    print('Hang on...getting rows...')
    
    querySt="select no_thesis from thesis.tbthesis_per_period where id_period=9"
    
    row = session.execute(querySt)

    if row:
        print('Thesis so far in period 9:',row[0][0])
       

def cassandraBDProcess(json_thesis):
    
    global thesis_added
    print('Step into cassandra process...')
    #Connect to Cassandra
    objCC=CassandraConnection()
    cloud_config= {
        'secure_connect_bundle': appPath+'secure-connect-dbquart.zip'
    }
    
    auth_provider = PlainTextAuthProvider(objCC.cc_user,objCC.cc_pwd)
    cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
    session = cluster.connect()
    session.default_timeout=50
    print('Connected to Cassandra...')
    
    #Get values for query
    #Ejemplo : Décima Época

    period=json_thesis['period']
    period=period.lower()
    
    if period=='novena época':
        idThesis=json_thesis['id_thesis']
        heading=json_thesis['heading']
        #Check wheter or not the record exists
        querySt="select * from thesis.tbthesis where id_thesis="+str(idThesis)+" and heading='"+heading+"'"
    
        future = session.execute_async(querySt)
        row=future.result()

        if row: 
            thesis_added=False
        else:
            #Insert Data as JSON
            json_thesis=json.dumps(json_thesis)
            #wf.appendInfoToFile(dirquarttest,str(idThesis)+'.json', json_thesis)
            insertSt="INSERT INTO thesis.tbthesis JSON '"+json_thesis+"';"
            future = session.execute_async(insertSt)
            future.result() 

            #Update count for table
            row=''
            querySt="select no_thesis from thesis.tbthesis_per_period where id_period=9"
            future = session.execute_async(querySt)
            row=future.result()
            
            if row:
                total=int(row[0][0])+1
                updateSt="update thesis.tbthesis_per_period set no_thesis="+str(total)+" where id_period=9"
                future=session.execute_async(updateSt)
                future.result() 

            thesis_added=True
    

    cluster.shutdown()          
    return thesis_added
 



"""
uploadThesis:
    Reads the url where the service is fetching data from thesis
"""

def prepareThesis(id_thesis,json_thesis): 
    result=''
    strIdThesis=str(id_thesis) 
    url="https://sjf.scjn.gob.mx/SJFSist/Paginas/DetalleGeneralV2.aspx?ID="+strIdThesis+"&Clase=DetalleTesisBL&Semanario=0"
    browser.get(url)
    time.sleep(1)
    thesis_html = BeautifulSoup(browser.page_source, 'lxml')
    title=thesis_html.find('title')
    title_text=title.text
    print('Title:'+title_text)
    if title_text.strip() != msg_error: 
        
        json_thesis['id_thesis']=int(strIdThesis)
        #json_thesis['_id']=t =bson.objectid.ObjectId()
        #Fet values from header, and body of thesis
        for obj in thesis_id:  
            field=thesis_html.find(id=obj)
            if field.text != '':   
                strField=field.text.strip()
                if obj==thesis_id[0]:
                    json_thesis['thesis_number']=strField
                if obj==thesis_id[1]:
                    json_thesis['instance']=strField
                if obj==thesis_id[2]:
                    json_thesis['source']=strField
                #Special Case    
                if obj==thesis_id[3]:
                    if strField.find(',')!=-1:
                        chunks=strField.split(',')
                        count=len(chunks)
                        if count==2:
                            json_thesis['book_number']=chunks[0]
                            json_thesis['publication_date']=chunks[1]
                        if count==3:
                            json_thesis['book_number']=chunks[0]+" "+chunks[2]
                            json_thesis['publication_date']=chunks[1]
                    else:
                        json_thesis['publication_date']=strField
                if obj==thesis_id[4]:
                    json_thesis['period']=strField
                if obj==thesis_id[5]:
                    json_thesis['page']=strField
                #Special case :
                #Type of jurispricende (Type of thesis () )
                if obj==thesis_id[6]:
                    strField=strField.replace(')','')
                    chunks=strField.split('(')
                    count=len(chunks)
                    if count==2: 
                        json_thesis['type_of_thesis']=chunks[0]
                        json_thesis['subject']=chunks[1]
                        
                    if count==3:
                        json_thesis['jurisprudence_type']=chunks[0]
                        json_thesis['type_of_thesis']=chunks[1]
                        json_thesis['subject']=chunks[2] 

                if obj==thesis_id[7]:
                    json_thesis['heading']=strField.replace("'",',')
                if obj==thesis_id[8]:
                    json_thesis['text_content']=strField.replace("'",',') 
                if obj==thesis_id[9]:  
                    children=thesis_html.find_all(id=obj)
                    for child in children:
                        for p in precedentes_list:   
                            preced=child.find_all(class_=p)
                            for ele in preced:
                                if ele.text!='':
                                    strValue=ele.text.strip()
                                    json_thesis['lst_precedents'].append(strValue.replace("'",','))

                
        for obj in thesis_class:
            field=thesis_html.find(class_=obj)
            if field.text != '':   
                strField=field.text.strip()
                if obj==thesis_class[0]:
                    json_thesis['publication']=strField
   
        thesis_html=''
        result=json_thesis
    else:
        result=''
        
    return  result

    
class CassandraConnection():
    cc_user='quartadmin'
    cc_keyspace='thesis'
    cc_pwd='P@ssw0rd33'
    cc_databaseID='9de16523-0e36-4ff0-b388-44e8d0b1581f'
        


if __name__ == '__main__':
    main()
    
    
"""
Objecst to connect to DB
'mc' prefix to know the variables from MongoConnection class

"""
"""
class MongoConnection():
    mc_user='admin'
    mc_pwd='v9mIadQx6dWjVDZc'
    mc_cluster='clustertest'
"""

"""
mongoDBProcess:
    Inserts a document (thesis) in database, this method inserts a new thesis only
    if this doesn´t exist


def mongoDBProcess(json_thesis):
    
    objMC=MongoConnection()
    user=objMC.mc_user
    pwd=objMC.mc_pwd
    cluster=objMC.mc_.cluster
    global thesis_added
    result=''
    client = MongoClient("mongodb+srv://"+user+":"+pwd+"@"+cluster+"-mlo2r.azure.mongodb.net/test?retryWrites=true&w=majority")
    db = client['dbquart']
    collection=db['all_thesis']
    #Check if the thesis exists
    
    strID=json_thesis['ID']
    strHeading=json_thesis['content']['heading']
    
    
    
    
    result=collection.count_documents(
                           {'ID':strID,
                            'content.heading':strHeading}
                           )
       
    
    if result==0:
       collection.insert_one(json_thesis)
       thesis_added=True
       
       
    return thesis_added 
        
"""