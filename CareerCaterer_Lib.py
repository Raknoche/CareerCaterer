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
    for length in range(3,0,-1):
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
                if (skill[0] not in user_skills) and (skill[0] not in suggested_skills):
                    suggested_skills.append(skill[0])
                    suggestion_confidence.append(skill[1])
                    suggestion_complexity.append(length)
                    used_skills.append(skill[2])
                
        #break loop once we have enough skill suggestions
        if len(suggested_skills) > number_to_show:
            break
            
    #Order the suggestions by complexity, and then by confidence
    final_suggestions = [skill for (z,y,skill) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills),reverse=True)]
    final_confidence = [suggestion_confidence for (z,suggestion_confidence,y) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills),reverse=True)]
    final_complexity = [suggestion_complexity for (suggestion_complexity,y,z) in sorted(zip(suggestion_complexity,suggestion_confidence,suggested_skills),reverse=True)]

    return (final_suggestions,final_confidence,final_complexity)

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

