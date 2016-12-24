import pandas as pd
import pymysql as mdb
import ast
from gensim import corpora, models, similarities
import itertools


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


#Make a function that find subsets of our user's skills
def findsubsets(S,m):
    return set(itertools.combinations(S, m))


def SuggestJobSkills(user_skills,career,skills_list):
    #First, remove any skills that aren't in our database
    career=career.lower().replace(' ','+')
    skills_list=[skill.lower() for skill in skills_list]
    user_skills = [skill.lower() for skill in user_skills if (skill.lower() in skills_list)]
    print(user_skills)
    #Find the most complex subsets of our user's skills that we have an association rule
    number_to_show=5
    current_num_suggestions=0
    suggested_skills=[]
    suggestion_confidence=[]
    suggestion_complexity=[]

    #Start with the most complex subsets
    for length in range(len(user_skills),0,-1):
        subsets = findsubsets(user_skills,length)

        #Query the lug to see if this skill subset exists in SkillAssociations table
        for subset in subsets:
            con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database');    
            
            with con:
                cur = con.cursor()

                association_query = "SELECT SuggestedSkill,Confidence FROM SkillAssociations WHERE JobType=%s and UserSkills=%s"
                cur.execute(association_query,(career,str(list(subset))))

                result = cur.fetchall()
                
                if result:
                    for skill in result:
                        #Only interested in skills the user doesn't already have
                        if (skill[0] not in user_skills) and (skill[0] not in suggested_skills):
                            suggested_skills.append(skill[0])
                            suggestion_confidence.append(skill[1])
                            suggestion_complexity.append(length)
                
        #break loop once we have enough skill suggestions
        if len(suggested_skills) > number_to_show:
            break
            
    #Order the suggestions by complexity, and then by confidence
    final_suggestions = [skill for (z,y,skill) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills),reverse=True)]
    final_confidence = [suggestion_confidence for (z,suggestion_confidence,y) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills),reverse=True)]
    final_complexity = [suggestion_complexity for (suggestion_complexity,y,z) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills),reverse=True)]
    
    return (final_suggestions,final_confidence,final_complexity)

