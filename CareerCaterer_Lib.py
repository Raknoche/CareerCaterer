import pandas as pd
import pymysql as mdb
import ast
from gensim import corpora, models, similarities


def SuggestCareers(doc):
    ''' doc is a list of skills from the user: ['python','math']'''

    #Query DB for all jobs and job skills
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

    #Make a dictionary
    dictionary = corpora.Dictionary(skill_docs)

    #Make corpus, and run tfidf
    corpus = [dictionary.doc2bow(doc) for doc in skill_docs]
    tfidf = models.TfidfModel(corpus)
    index = similarities.MatrixSimilarity(tfidf[corpus])

    #clean up user skills
    new_doc = [skill.lower() for skill in doc]
    vec_bow = dictionary.doc2bow(new_doc)
    vec_tfidf = tfidf[vec_bow] 

    sims = index[vec_tfidf] # perform a similarity query against the corpus
    sims = sorted(enumerate(sims), key=lambda item: -item[1])

    return sims, job_list


def SuggestJobListings(doc,career):

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

