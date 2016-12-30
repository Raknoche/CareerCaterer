'''Run this to populate the job kill associations database'''

from bs4 import BeautifulSoup # For HTML parsing
import urllib # Website connections
import re # Regular expressions
from time import sleep # To prevent overwhelming the server between connections
from collections import Counter # Keep track of our term counts
from nltk.corpus import stopwords # Filter out stopwords, such as 'the', 'or', 'and'
import pandas as pd # For converting results to a dataframe and bar chart plots
import math
from string import digits
from orangecontrib.associate.fpgrowth import *  
import Orange
import numpy as np
from scipy.sparse import lil_matrix
import pymysql as mdb
import ast
from gensim import corpora, models, similarities

skills = pd.read_csv('/Users/richardknoche/Desktop/indeedMining/FinalSkillsDB.csv')
skills_list = [x.lower() for x in skills['Skill'].tolist()]

def calc_association(job_type):
    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');

    with con:
        cur = con.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT JobSkills FROM JobListings WHERE JobSearched = '%s'" % (job_type))

        rows = cur.fetchall()

        all_docs = [ast.literal_eval(row['JobSkills']) for row in rows]

    all_docs=[[item.lower() for item in doc] for doc in all_docs]

    #For each job listing, convert the list of skills to the a list of booleans, which state whether each of our 
    #skills in the full skill list exists in the job listing
    doc_booleans = [[skill in doc for skill in skills_list] for doc in all_docs]
    doc_booleans = lil_matrix(doc_booleans)

    #Find frequent itemsets for the specific type of job
    #If we have 1000 job listings, then 1% means the itemset shows up in 10 of them
    if (len(all_docs) > 20):
        iter_count=1
        itemsets = dict(frequent_itemsets(doc_booleans, 1/(2**iter_count)))
        iter_count = iter_count+1
                    
        while (np.floor(len(itemsets)/300) <= 0):
            itemsets = dict(frequent_itemsets(doc_booleans, 1/(2**iter_count)))
            iter_count = iter_count+1

        #Make association rules for the specific type of job
        rules = association_rules(itemsets, .1)
        rules = list(rules)

        #Sort by complexity of the skill subset
        rules=sorted(rules,key=lambda x: len(x[0]),reverse=True)

        #Remove any multi-skill suggestions.  We only want subset -> single skill rules
        #Result is formatted as user skills, suggested skill, confidence
        single_suggestions = [[[skills_list[idx] for idx in list(rule[0])],skills_list[list(rule[1])[0]],rule[3]] for rule in rules if len(rule[1]) == 1]
        
        #Sort by complexity of the skill subset, then by confidence
        single_suggestions = sorted(single_suggestions,key=lambda x: (len(x[0]),x[2]),reverse=True)
        
        #Place the results in a new table in our DB, with columns [job,skill_subset,suggested_skill,confidence]
        con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');    
        with con:
            cur = con.cursor()

            #Note: UniqueID will fail if user_skill subset is more than~50 skills long.  I doubt we will ever have associaiton rules that 
            #use that many skills, so should be fine.
            insert_query = "REPLACE INTO SkillAssociations SET JobType=%s, UserSkills=%s, SuggestedSkill=%s, Confidence=%s, UniqueRuleID=%s;"

            for rule in single_suggestions:
                cur.execute(insert_query,(job_type,str(rule[0]),rule[1],rule[2],job_type+'+'+str(rule[1])+str(rule[0])) )
        

con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');

with con:
    cur = con.cursor(mdb.cursors.DictCursor)
    cur.execute("SELECT distinct(JobSearched) FROM JobListings")
    
    rows = cur.fetchall()

    all_job_searched = [row['JobSearched'] for row in rows]

for job in all_job_searched:
    calc_association(job)
    print("Done with %s" % job)
