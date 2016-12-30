import pandas as pd
import pymysql as mdb
import ast
from gensim import corpora, models, similarities
import itertools
import pickle
from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine
import pandas as pd
from functools import reduce
import re

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

import pymysql as mdb
import sys
from bs4 import BeautifulSoup # For HTML parsing
import urllib # Website connections
import re # Regular expressions
from time import sleep # To prevent overwhelming the server between connections
from collections import Counter # Keep track of our term counts
from nltk.corpus import stopwords # Filter out stopwords, such as 'the', 'or', 'and'
import pandas as pd # For converting results to a dataframe and bar chart plots
import math
from string import digits
from functools import reduce
import time
import collections
from http.cookiejar import CookieJar
import ssl

import socket
from time import sleep
socket.setdefaulttimeout(60) #if it takes longer than a minute to connect to webpage, move on


#Function to scrape job listings from indeed.  Used in ScrapeJobListings
def get_skills(website,formatted_skills,gcontext,keys,values):
    skill_dict = dict(zip(keys, values))
    repls = ('re-', 're'), ('co-', 'co'), ('non-','non'),('&','and'),(',','')
    req=urllib.request.Request(website,data=None,headers={'User-Agent':'Mozilla/5.0 (Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US; rv:1.9.0.5)'})
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US; rv:1.9.0.5)')]
    opener.addheaders =[('Accept','text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')]
    response = opener.open(req)
    html = response.read().decode('utf8', errors='ignore')
    response.close()
    
    soup = BeautifulSoup(html,"lxml")
    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]
    visible_text = soup.getText()
    lines = (line.strip() for line in visible_text.splitlines()) # break into lines
    text=' '.join([line for line in lines if line is not ''])

    #dictionary counting appearances of formatted skills
    skills = []

    # define desired replacements here
    formatted_text = reduce(lambda a, kv: a.replace(*kv), repls, text.lower()).replace('-',' ')    
    #Search for each skill in our database
    for skill in formatted_skills:

        #Only check the skill if it shows up in the listing
        if (skill in formatted_text): #sum(1 for _ in re.finditer(r'\b%s\b' % re.escape(skill), formatted_text)) > 0:
            skills += [skill_dict[skill]] * sum(1 for _ in re.finditer(r'\b%s\b' % re.escape(skill), formatted_text))

            #To prevent multi-counting, remove the skill from the text
            #It's okay to do this, since formatted_skills is sorted by length of skills
            formatted_text = re.sub(r"\b%s\b" % re.escape(skill), '', formatted_text)
            
    return (text,skills)

def ScrapeJobListings(job_title):
    '''scrapes listings for a particular job title on indeed
    will update the listing info if it is already in our database
    ob_title should be in format "data+scientist" '''

    #First get skills and formatted skills from our JobSkills DB              
    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database',charset='utf8');
                    
    with con:
        cur = con.cursor()
        cur.execute("SELECT JobSkill,FormattedJobSkill FROM JobSkills;")
        all_skills= cur.fetchall()

    keys = [key for (value,key) in all_skills]
    values = [value for (value,key) in all_skills]

    formatted_skills = sorted(keys,key=lambda x: len(x),reverse=True)

    #Next scrape indeed search page for number of listings
    gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1) 
    total_count=0
    job_url = 'http://www.indeed.com/jobs?q="' + job_title + '"'
    html = urllib.request.urlopen(job_url).read() 
    base_url = 'http://www.indeed.com'


    #Connect to the job search url
    #with urllib.request.urlopen('http://www.python.org') as page:

    html = urllib.request.urlopen(job_url).read() 

    # Get the first page
    soup = BeautifulSoup(html,"lxml") 

    # Find how many jobs are listed
    try:
        num_jobs_area = soup.find(id = 'searchCount').string.encode('utf-8')                                                  
        job_numbers = re.findall('\d+',num_jobs_area.decode("utf-8"))

        # Have a total number of jobs greater than 1000
        if len(job_numbers) > 3: 
            total_num_jobs = (int(job_numbers[2])*1000) + int(job_numbers[3])
        else:
            total_num_jobs = int(job_numbers[2]) 

        # Determine how many "next" pages there are
        num_pages = math.ceil(total_num_jobs/10) 

        # Store all our descriptions in this list
        all_job_titles=[]
        all_job_locations=[]
        all_job_skills=[]

        # Loop through all of our search result pages
        for i in range(0,min(num_pages,100)): 
            #print(num_pages)
            try:
                print ('Getting page ', i+1, ' of ', min(num_pages,100),' for ', job_title)
                start_num = str(i*10) 
                current_page = ''.join([job_url, '&start=', start_num])

                html_page = urllib.request.urlopen(current_page).read() 
                page_obj = BeautifulSoup(html_page,"lxml") 

                #Initialize lists
                job_titles = []
                job_urls = []
                job_locations = []
                job_skills = []

                #Get title and link to listing
                job_link_area = page_obj.find(id = 'resultsCol') 
                for job in job_link_area.find_all('h2'):
                    job_titles.append(job.find('a').get('title'))
                    job_urls.append(base_url + job.find('a').get('href'))

                #Get job locations
                for job in job_link_area.find_all('span'):
                    if job.find('span',{"class" : ['location']}):
                        location = job.find('span',{"class" : ['location']}).span.text
                        remove_digits = str.maketrans('', '', digits) #remove zip codes
                        location = location.translate(remove_digits)
                        location = location.rstrip()
                        location=location.split('(')
                        location=location[0]
                        job_locations.append(location.rstrip())

                #Get skills from the job listings
                for j in range(0,len(job_urls)):
                    #print(job_urls[j])
                    try:
                        listing_text, these_skills = get_skills(job_urls[j],formatted_skills,gcontext,keys,values)
                    except:
                        listing_text = None
                        these_skills = None
                        print('Error getting job skills')

                    if these_skills:
                        try:

                            con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database',charset='utf8');

                            with con:
                                cur = con.cursor()
                                test_query = "SELECT (1) FROM JobListings WHERE UniqueURL = %s"

                                if not cur.execute(test_query,(job_urls[j][21:])):                     
                                    total_count+=1
                                    #print('Total count should be ', total_count)
                                    insert_query = "INSERT INTO JobListings(JobSearched, TimeSearched, JobTitle, JobLocation, JobSkills, ListingText, UniqueURL) VALUES(%s,%s,%s,%s,%s,%s,%s)"
                                    
                                    cur.execute(insert_query,(job_title,time.strftime("%d/%m/%Y %H:%M:%S"),job_titles[j],job_locations[j],str(these_skills),listing_text.encode('unicode_escape'),job_urls[j][21:]) )  

                        except:
                            print("Issue with MySQL Insert")
                    #else:
                        #print("No Skills Found")

            except:
                print ("Couldn't open page", i+1)
    except:
        print('No jobs listings found')


#Function for calculating association rules for a specific job title
def calc_association(job_type):
    #Get list of job skills
    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database',charset='utf8');
                
    with con:
        cur = con.cursor()
        cur.execute("SELECT JobSkill,FormattedJobSkill FROM JobSkills;")
        all_skills= cur.fetchall()
        
    skills_list = [skill.lower() for (skill,formatted_skill) in all_skills]

    #Get Job Listings Docs
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
        
#Runs calc_associations on all job titles in our job listing database:
def UpdateAssociations():
    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');

    with con:
        cur = con.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT distinct(JobSearched) FROM JobListings")
        
        rows = cur.fetchall()

        all_job_searched = [row['JobSearched'] for row in rows]

    for job in all_job_searched:
        calc_association(job)





def UpdateCareerModel():
    ''' Run this to update the tf-idf model used to suggest careers'''
    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');

    with con:

        #Specify the type of cursor with cursors.TYPE
        #The SQL return will now be a dict with column keys instead of a tuple
        cur = con.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT JobSkills,JobSearched FROM JobListings")

        rows = cur.fetchall()

        all_docs = [ast.literal_eval(row['JobSkills']) for row in rows]
        all_jobs = [row['JobSearched'] for row in rows]

    #Load results into a data frame
    df = pd.DataFrame()
    df['job']=all_jobs
    df['skills']=all_docs

    #Put all skills from a type of job into one document
    job_list=[]
    skill_docs=[]
    for job in df['job'].unique():
        job_list.append(job)
        skill_series=df[df['job']==job]['skills'].tolist()
        all_skill_series=[]
        for skills in skill_series:
            all_skill_series += skills
        skill_docs.append([skill.lower() for skill in all_skill_series])

    pickle.dump(job_list, open('model/job_list.pickle', 'wb'))
    pickle.dump(skill_docs, open('model/skill_docs.pickle', 'wb')) 

    #Make a dictionary
    dictionary = corpora.Dictionary(skill_docs)
    dictionary.save('model/dictionary.model')

    #Make corpus, and run tfidf
    corpus = [dictionary.doc2bow(doc) for doc in skill_docs]
    corpora.MmCorpus.serialize('model/corpus.mm', corpus)

    tfidf = models.TfidfModel(corpus)
    tfidf.save('model/tfidf.model')

    #Get similarity
    index = similarities.MatrixSimilarity(tfidf[corpus])
    index.save('model/similarities.model')

def SuggestCareers(doc):
    '''Run this to suggest a career based on our tf-idf model'''
    #load tf-idf similarity information
    index = similarities.MatrixSimilarity.load('model/similarities.model')
    dictionary = corpora.Dictionary.load('model/dictionary.model')
    tfidf = models.TfidfModel.load('model/tfidf.model')
    job_list = pickle.load(open('model/job_list.pickle', 'rb'))

    #clean up user skills
    new_doc = [skill.lower() for skill in doc]
    vec_bow = dictionary.doc2bow(new_doc)
    vec_tfidf = tfidf[vec_bow] 

    sims = index[vec_tfidf] # perform a similarity query against the corpus
    sims = sorted(enumerate(sims), key=lambda item: -item[1])

    return sims, job_list


def SuggestJobListings(doc,career):
    '''Run this to suggest specific job listings based on a custom tf-idf model'''
    career=career.lower().replace(' ','+')
    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');

    with con:
        cur = con.cursor(mdb.cursors.DictCursor)
        query = "SELECT JobSkills,UniqueUrl,JobTitle FROM JobListings WHERE JobSearched = %s"
        cur.execute(query,career)

        rows = cur.fetchall()

        all_docs = [ast.literal_eval(row['JobSkills'].lower()) for row in rows]
        all_titles = [row['JobTitle'] for row in rows]
        all_urls = [row['UniqueUrl'] for row in rows]

    dictionary = corpora.Dictionary(all_docs)
    corpus = [dictionary.doc2bow(doc) for doc in all_docs]
    tfidf = models.TfidfModel(corpus)
    corpus_tfidf = tfidf[corpus]
    index = similarities.MatrixSimilarity(tfidf[corpus])
    vec_bow = dictionary.doc2bow(doc)
    vec_tfidf = tfidf[vec_bow] 
    sims = index[vec_tfidf] 
    sims = sorted(enumerate(sims), key=lambda item: -item[1])

    return sims, all_urls, all_titles


#Make a function that find subsets of our user's skills
def findsubsets(S,m):
    '''used to find subsets of user skills'''
    return set(itertools.combinations(S, m))


def SuggestJobSkills(user_skills,career,skills_list):
    '''used to suggest new skills for a user to learn
    This could be sped up if we store the model for each type of job locally
    Not really worth it to store that many models to save 0.4 seconds though'''

    #First, remove any skills that aren't in our database
    career=career.lower().replace(' ','+')
    skills_list=[skill.lower() for skill in skills_list]
    user_skills = [skill.lower() for skill in user_skills if (skill.lower() in skills_list)]
    
    number_to_show=5
    current_num_suggestions=0
    suggested_skills=[]
    suggestion_confidence=[]
    suggestion_complexity=[]
    used_skills=[]
    #Start with the most complex subsets (max of 3)
    for length in range(min(3,len(user_skills)),0,-1):
        subsets = findsubsets(user_skills,length)
        #print(subsets)
        #Query the lug to see if this skill subset exists in SkillAssociations table
        con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');    

        with con:
            cur = con.cursor()

            #Building the query
            skill_query_txt='('
            for item in subsets:
                added_txt = "\"%s\"," % (list(item))
                skill_query_txt = skill_query_txt + added_txt

            skill_query_txt=skill_query_txt[:-1] + ')'
            skill_query = "SELECT SuggestedSkill,Confidence,UserSkills FROM SkillAssociations WHERE JobType='%s' and UserSkills IN " % (career)
            skill_query = skill_query + skill_query_txt

            cur.execute(skill_query)
            result = cur.fetchall()


            for skill in result:
                #Only interested in skills the user doesn't already have
                if (skill[0] not in user_skills) and (skill[0].lower() in skills_list):
                    suggested_skills.append(skill[0])
                    suggestion_confidence.append(skill[1])
                    suggestion_complexity.append(length)
                    used_skills.append(skill[2])
                
            
    #Order the suggestions by complexity, and then by confidence
    final_suggestions = [skill for (z,y,skill,q) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills,used_skills),reverse=True)]
    final_confidence = [suggestion_confidence for (z,suggestion_confidence,y,q) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills,used_skills),reverse=True)]
    final_complexity = [suggestion_complexity for (suggestion_complexity,y,z,q) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills,used_skills),reverse=True)]
    final_used_skills = [used_skills for (x,y,z,used_skills) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills,used_skills),reverse=True)]

    return (final_suggestions,final_confidence,final_complexity,final_used_skills)

#function for grabbing skills from a pdf
def process_pdf(file_path,values,keys):
    fp = open(file_path, 'rb')
    parser = PDFParser(fp)
    doc = PDFDocument()
    parser.set_document(doc)
    doc.set_parser(parser)
    doc.initialize('')
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    all_text=''
    for page in doc.get_pages():
        interpreter.process_page(page)
        layout = device.get_result()
        for lt_obj in layout:
            if isinstance(lt_obj, LTTextBox) or isinstance(lt_obj, LTTextLine):
                all_text=all_text+lt_obj.get_text()
                
    skills = []
    skill_dict = dict(zip(keys, values))
    repls = ('re-', 're'), ('co-', 'co'), ('non-','non'),('&','and'),(',','')

    formatted_skills = sorted(keys,key=lambda x: len(x),reverse=True)
    formatted_text = reduce(lambda a, kv: a.replace(*kv), repls, all_text.lower()).replace('-',' ')    

    #Extract skills from processed text
    common_resume_words=["education","publications","philosophy"]
    for skill in formatted_skills:
        if skill not in common_resume_words:
            if (skill in formatted_text): #sum(1 for _ in re.finditer(r'\b%s\b' % re.escape(skill), formatted_text)) > 0:
                skills += [skill_dict[skill]] * sum(1 for _ in re.finditer(r'\b%s\b' % re.escape(skill), formatted_text))
                formatted_text = re.sub(r"\b%s\b" % re.escape(skill), '', formatted_text)

    return skills

def format_career(career):
    return career.replace(' ','+').lower()

def format_skill(skill):
    repls = ('re-', 're'), ('co-', 'co'), ('non-','non'),('&','and'),(',','')
    formated_skill = ' '.join([reduce(lambda a, kv: a.replace(*kv), repls,word).replace('-',' ') for word in  skill.lstrip().rstrip().lower().split(' ')])
    return formated_skill.lstrip().rstrip()

def AddUserSkill(suggestion):
    formatted_suggestion = format_skill(suggestion)

    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');
    with con:

        cur = con.cursor()
        query = "SELECT * FROM UserAddedSkills WHERE FormattedSkill = %s"
        #If it doesn't exist, add it to database
        if not cur.execute(query,(formatted_suggestion,)):
            spelling_dict={suggestion:1}
            query = "REPLACE INTO UserAddedSkills SET Skill=%s, UserSpelling=%s, FormattedSkill=%s, SuggestionCount=1;"
            cur.execute(query,(suggestion.lower(),str(spelling_dict),formatted_suggestion))

        #If we already have the entry, adjust it
        else:
            result = cur.fetchall()
            num_suggested = result[0][3] + 1
            spelling_dict = ast.literal_eval(result[0][1])
            if suggestion in spelling_dict:
                spelling_dict[suggestion] += 1
            else:
                spelling_dict[suggestion] = 1
            query = "REPLACE INTO UserAddedSkills SET Skill=%s, UserSpelling=%s, FormattedSkill=%s, SuggestionCount=%s;"
            cur.execute(query,(suggestion.lower(),str(spelling_dict),formatted_suggestion,num_suggested))

def RemoveUserSkill(suggestion):
    formatted_suggestion = format_skill(suggestion)

    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');
    with con:

        cur = con.cursor()
        query = "SELECT * FROM UserRemovedSkills WHERE FormattedSkill = %s"
        #If it doesn't exist, add it to database
        if not cur.execute(query,(formatted_suggestion,)):
            spelling_dict={suggestion:1}
            query = "REPLACE INTO UserRemovedSkills SET Skill=%s, UserSpelling=%s, FormattedSkill=%s, SuggestionCount=1;"
            cur.execute(query,(suggestion.lower(),str(spelling_dict),formatted_suggestion))

        #If we already have the entry, adjust it
        else:
            result = cur.fetchall()
            num_suggested = result[0][3] + 1
            spelling_dict = ast.literal_eval(result[0][1])
            if suggestion in spelling_dict:
                spelling_dict[suggestion] += 1
            else:
                spelling_dict[suggestion] = 1
            query = "REPLACE INTO UserRemovedSkills SET Skill=%s, UserSpelling=%s, FormattedSkill=%s, SuggestionCount=%s;"
            cur.execute(query,(suggestion.lower(),str(spelling_dict),formatted_suggestion,num_suggested))

def AddUserCareer(career):
    formatted_career = format_career(career)
    
    con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');
    with con:

        cur = con.cursor()
        query = "SELECT * FROM UserAddedCareers WHERE Career = %s"
        #If it doesn't exist, add it to database
        if not cur.execute(query,(formatted_career,)):
            query = "REPLACE INTO UserAddedCareers SET Career=%s, SuggestionCount=1;"
            cur.execute(query,(formatted_career,))

        #If we already have the entry, adjust it
        else:
            result = cur.fetchall()
            num_suggested = result[0][1] + 1
            query = "REPLACE INTO UserAddedCareers SET Career=%s, SuggestionCount=%s;"
            cur.execute(query,(formatted_career,num_suggested))
