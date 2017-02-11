from flask import Flask, flash, redirect, render_template, request, url_for, jsonify, session
import wtforms as wt
from wtforms import TextField, Form
import pymysql as mdb
from CareerCaterer_Lib import SuggestCareers, SuggestJobListings, SuggestJobSkills, process_pdf
from CareerCaterer_Lib import format_career, format_skill, AddUserSkill, RemoveUserSkill, AddUserCareer
from werkzeug.utils import secure_filename
import os
import random
import time
from random import randint
from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine
import pandas as pd
from functools import reduce
import re
random.seed(time.time())
import json as JSON
import ast

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_USER_PDFS = os.path.join(APP_ROOT, 'userPDFs')

app = Flask(__name__)
UPLOAD_FOLDER = '/userPDFs'
ALLOWED_EXTENSIONS = set(['pdf'])
app.config["DEBUG"] = True
app.secret_key = 'super secret key'

#List of user's skills
user_skills = []


#List of skills and jobs in our DB, for autocompletion
con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database',charset='utf8');
                
with con:
    cur = con.cursor()
    cur.execute("SELECT JobSkill,FormattedJobSkill FROM JobSkills;")
    all_skills= cur.fetchall()

    cur = con.cursor()
    cur.execute("SELECT DISTINCT(JobSearched) from JobListings;")
    all_jobs= cur.fetchall()   
    
dbskills = [skill for (skill,formatted_skill) in all_skills]
dbskills_formatted = [formatted_skill for (skill,formatted_skill) in all_skills]
dbcareers = [job[0].replace('+',' ').title() for job in all_jobs]

print("TEST")
print('email' in dbskills)

del all_skills
del all_jobs

#Probably note needed?
class SearchForm(Form):
    autocomp= TextField('autocomp',id='autocomplete')


'''Home Page Code'''
#Home page
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("step_one.html", skillList=user_skills)

    return redirect(url_for('index'))


#Handles getting skills from user PDF
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Handles getting skills from user PDF
@app.route('/skills_from_pdf', methods=['POST'])
def skills_from_pdf():
    # check if the post request has the file part
    if 'file' not in request.files:
        flash('Please upload a PDF file')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        flash('Please upload a PDF file')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = file.filename.rsplit('.', 1)[0].lower() + str(randint(0,100000)) + '.pdf'
        filename = secure_filename(filename)
        file_save_path = os.path.join(APP_USER_PDFS, filename)
        file.save(file_save_path)

        #Get use skills from PDF
        skills = process_pdf(file_save_path,dbskills,dbskills_formatted)

        #For some reason user_skills += skill doesn't work...
        for skill in set(skills):
            if skill not in user_skills:
                user_skills.append(skill)

        print(user_skills)
        #Delete user PDF
        os.remove(file_save_path)

        #Reload homepage
        return redirect(url_for('index'))

    flash('Please upload a PDF file')
    return redirect(url_for('index'))


#Handles adding skills to user's skill list
@app.route('/add_user_skill', methods=['POST'])
def add_user_skill():
    new_skill = request.form['autocomplete']
    if new_skill not in user_skills:
    	user_skills.append(new_skill)

    return redirect(url_for('index'))

#Handles removing skills from a user's skill list
@app.route('/remove_user_skill', methods=['POST'])
def remove_user_skill():
    user_skills.remove(request.form['skill_to_remove'])
    return redirect(url_for('index'))    

#Handles autocompleting the skill's search bar
@app.route('/autocomplete',methods=['GET'])
def autocomplete():
    search = request.args.get('term') #Not sure this is needed...
    app.logger.debug(search)
    return jsonify(json_list=dbskills) 


'''Career Search (Step two) CODE'''
#Webpage for step two
@app.route('/step2',methods=['GET'])
def Step2():
    return render_template("step_two.html")


#Handles autocompleting the career search bar
@app.route('/autocomplete_careers',methods=['GET'])
def autocomplete_careers():
    search_career = request.args.get('term')
    app.logger.debug(search_career)
    return jsonify(json_list=dbcareers) 


#Webpage for suggesting careers
@app.route('/suggested_career',methods=['GET'])
def suggested_career():
	#Calculate the skills we want to suggest first
	#SuggestCareers handles making everything lowercase
	sims, job_list = SuggestCareers(user_skills)
	suggested_careers=[job_list[sim[0]].replace('+',' ').title() for sim in sims]
	suggestion_strength=[sim[1] for sim in sims]

	max_careers = 5
	suggested_careers=suggested_careers[:max_careers]
	suggestion_strength=suggestion_strength[:max_careers]

	#Pass the to the html page
	return render_template("suggested_careers.html", suggestions=zip(suggested_careers,suggestion_strength))

'''Individual Career Page Code'''

#Webpage for specific career search
@app.route('/search_for_career',methods=['GET','POST'])
def search_for_career():
    searched_career = request.form['autocomplete_careers']
    if searched_career in dbcareers:
        sims, all_urls, all_titles = SuggestJobListings(user_skills,searched_career)
        final_suggestions,final_confidence,final_complexity,final_used_skills = SuggestJobSkills(user_skills,searched_career,dbskills)

        #Bookkeeping
        suggested_listings = [all_urls[item[0]] for item in sims]
        listing_strength = [float(item[1]) for item in sims]
        job_titles = [all_titles[item[0]] for item in sims]

        max_listings=5
        suggested_listings=suggested_listings[:max_listings]
        listing_strength=listing_strength[:max_listings]
        job_titles=job_titles[:max_listings]

        session.clear()
        session['searched_career'] = searched_career
        session['final_suggestions'] = final_suggestions
        session['final_confidence'] = final_confidence
        session['final_complexity'] = final_complexity   
        session['final_used_skills'] = final_used_skills 
        session['skill_sugg_len'] = len(final_suggestions)
        session['suggested_listings'] = suggested_listings
        session['listing_strength'] = listing_strength
        session['job_titles'] = job_titles

        return redirect(url_for('career_page'))

    else:
        #Put in a flash saying the job isn't in our DB, for now
        return redirect(url_for('Step2'))

#Webpage for specific career search
@app.route('/career_page',methods=['GET','POST'])
def career_page():
    searched_career = session['searched_career'] 
    final_suggestions = session['final_suggestions']
    final_confidence = session['final_confidence']
    final_complexity = session['final_complexity']
    final_used_skills = session['final_used_skills']
    skill_sugg_len = session['skill_sugg_len']
    suggested_listings = session['suggested_listings']
    listing_strength = session['listing_strength']
    job_titles = session['job_titles']

    skill_list=[]
    assoc_list=[]
    strength_list=[]

    for (idx,skills) in enumerate(final_used_skills):
        for skill in  ast.literal_eval(skills):
            #Check if the skill is already in our user skills dict, if not add it
            if (skill,final_suggestions[idx]) not in zip(skill_list,assoc_list):
                skill_list.append(skill)
                assoc_list.append(final_suggestions[idx])
                strength_list.append(final_confidence[idx])
            else:
                list_idx = list(zip(skill_list,assoc_list)).index((skill,final_suggestions[idx]))
                strength_list[list_idx] = max(strength_list[list_idx],final_confidence[idx])

    #Get lists of unique association and sum of their confidences
    df = pd.DataFrame()
    df['skill']=skill_list
    df['assoc']=assoc_list
    df['strength']=strength_list

    assoc_df = df.groupby('assoc').sum().sort('strength',ascending=False)
    assoc_set = assoc_df.index.tolist()
    strength_set = assoc_df['strength'].tolist()
    skill_set = list(set(skill_list))

    #Limit to strong (>1.5) associations only
    idx_to_drop=[]
    assoc_to_drop=[]
    min_assoc=0.4
    for (idx,conf) in enumerate(strength_set):
        if conf < min_assoc:
            idx_to_drop.append(idx)
            assoc_to_drop.append(assoc_set[idx])


    #Remaking lists after removing low confidence results
    mask = df['assoc'].isin(assoc_to_drop)
    df = df[~mask]
    skill_list = df['skill'].tolist()
    assoc_list = df['assoc'].tolist()
    strength_list = df['strength'].tolist()

    assoc_df = df.groupby('assoc').sum().sort('strength',ascending=False)
    assoc_set = assoc_df.index.tolist()
    strength_set = assoc_df['strength'].tolist()
    skill_set = list(set(skill_list))


    return render_template("career.html", career=searched_career, skill_suggestions = zip(final_suggestions,final_confidence,final_complexity),\
                                skill_sugg_len = len(assoc_set),suggestions=zip(suggested_listings,listing_strength,job_titles),\
                                final_suggestions=final_suggestions,final_confidence=final_confidence,final_complexity=final_complexity,\
                                skill_list=skill_list,assoc_list=assoc_list,strength_list=strength_list,\
                                skill_set=skill_set,assoc_set=assoc_set,strength_set=strength_set)

#Function for getting career suggestions
@app.route('/search_suggested_career',methods=['GET','POST'])
def search_suggested_career():
    searched_career = request.form['selected_suggestion']

    sims, all_urls, all_titles = SuggestJobListings(user_skills,searched_career)
    final_suggestions,final_confidence,final_complexity,final_used_skills = SuggestJobSkills(user_skills,searched_career,dbskills)
    
    #Bookkeeping
    suggested_listings = [all_urls[item[0]] for item in sims]
    listing_strength = [float(item[1]) for item in sims]
    job_titles = [all_titles[item[0]] for item in sims]

    max_listings=5
    suggested_listings=suggested_listings[:max_listings]
    listing_strength=listing_strength[:max_listings]
    job_titles=job_titles[:max_listings]
    
    session.clear()
    session['searched_career'] = searched_career
    session['final_suggestions'] = final_suggestions
    session['final_confidence'] = final_confidence
    session['final_complexity'] = final_complexity   
    session['final_used_skills'] = final_used_skills 
    session['skill_sugg_len'] = len(final_suggestions)
    session['suggested_listings'] = suggested_listings
    session['listing_strength'] = listing_strength
    session['job_titles'] = job_titles

    #print(session['final_used_skills'])

    return redirect(url_for('career_page'))

'''Database Management Code'''
#Letting users suggest skills for us to add
@app.route("/add_skill_to_db", methods=["GET", "POST"])
def add_skill_to_db():
    user_recommended_skill = request.form['UserRecommendedSkill']
    flash('Thank you for recommending that we add "%s" to our database.' % (user_recommended_skill))
    AddUserSkill(user_recommended_skill)

    return redirect(url_for('index'))

#Letting users suggest careers for us to add
@app.route("/add_career_to_db", methods=["GET", "POST"])
def add_career_to_db():
    user_recommended_career = request.form['UserRecommendedCareer']
    flash('Thank you for recommending that we add "%s" to our careers database.' % (user_recommended_career))
    AddUserCareer(user_recommended_career)

    return redirect(url_for('Step2'))

#Letting users suggest a skill be removed from our DB
@app.route("/delete_skill_from_db", methods=["GET", "POST"])
def delete_skill_from_db():
    user_recommended_delete = request.form['UserRecommendedDelete']
    flash('Thank you for reporting "%s" as a problematic suggestion.' % (user_recommended_delete))
    RemoveUserSkill(user_recommended_delete)

    return redirect(url_for('career_page'))

if __name__ == "__main__":
    app.run()