
import pandas as pd
import pymysql as mdb
import ast
from gensim import corpora, models, similarities
import itertools
from CareerCaterer_Lib import UpdateCareerModel,UpdateAssociations,calc_association,ScrapeJobListings
import sys

#If we specify a manual file, add those job skills
if len(sys.argv) == 2:
    print("Adding job listings in the provided file to our database.")

    with open(sys.argv[1], encoding="latin-1") as f:
            content = f.readlines()

    job_titles=[]
    #Get job titles from file
    for (idx,item) in enumerate(content):
        if idx == len(content)-1:
            job_titles.append((item[:].lower().replace(' ','+').replace(',','')))
        else:
            job_titles.append((item[:-1].lower().replace(' ','+').replace(',','')))

#Otherwise, update the current database
elif len(sys.argv) == 1:
    print("No job titles provided.  Updating the current job listings instead.")
    #get job titles from DB
    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');

    with con:
        cur = con.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT distinct(JobSearched) FROM JobListings")

        rows = cur.fetchall()

        job_titles = [row['JobSearched'] for row in rows]

else:
    print("Please provide at most one command line argument, which specifies a file of job titles.")


#Scrape indeed for job listings of each title and add to our database
for job_title in job_titles:
    print(job_title)
    ScrapeJobListings(job_title)

#Updates the gensim model that is used for suggest careers. 
print("Updating Career Model")
UpdateCareerModel()

#Update the association rules database that is used to suggest skills
print("Updating Associatons Database")
UpdateAssociations()