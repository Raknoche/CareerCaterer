from flask import Flask, redirect, render_template, request, url_for, jsonify
import wtforms as wt
from wtforms import TextField, Form
import pymysql as mdb
from CareerCaterer_Lib import SuggestCareers, SuggestJobListings


app = Flask(__name__)
app.config["DEBUG"] = True

#List of user's skills
user_skills = []

#List of skills and jobs in our DB, for autocompletion
con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database',charset='utf8');
                
with con:
    cur = con.cursor()
    cur.execute("SELECT JobSkill FROM JobSkills;")
    all_skills= cur.fetchall()

    cur = con.cursor()
    cur.execute("SELECT DISTINCT(JobSearched) from JobListings;")
    all_jobs= cur.fetchall()   
    
dbskills = [skill[0] for skill in all_skills]
dbcareers = [job[0].replace('+',' ').title() for job in all_jobs]

del all_skills
del all_jobs


class SearchForm(Form):
    autocomp= TextField('autocomp',id='autocomplete')


'''Home Page Code'''
#Home page
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("step_one.html", skillList=user_skills)

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
    search = request.args.get('term')
    app.logger.debug(search)
    return jsonify(json_list=dbskills) 


'''Career Search (Step two) CODE'''
#Webpage for step two
@app.route('/step2',methods=['GET'])
def Step2():
    return render_template("step_two.html", skillList=user_skills)


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
		suggested_listings = [all_urls[item[0]] for item in sims]
		listing_strength = [item[1] for item in sims]
		job_titles = [all_titles[item[0]] for item in sims]

		max_listings=5
		suggested_listings=suggested_listings[:max_listings]
		listing_strength=listing_strength[:max_listings]
		job_titles=job_titles[:max_listings]

		return render_template("career.html", career=searched_career, suggestions=zip(suggested_listings,listing_strength,job_titles))
	else:
		#Put in a flash saying the job isn't in our DB, for now
		return redirect(url_for('Step2'))

#Webpage for specific career search
@app.route('/search_suggested_career',methods=['GET','POST'])
def search_suggested_career():
	searched_career = request.form['selected_suggestion']
	
	sims, all_urls, all_titles = SuggestJobListings(user_skills,searched_career)
	suggested_listings = [all_urls[item[0]] for item in sims]
	listing_strength = [item[1] for item in sims]
	job_titles = [all_titles[item[0]] for item in sims]

	max_listings=5
	suggested_listings=suggested_listings[:max_listings]
	listing_strength=listing_strength[:max_listings]
	job_titles=job_titles[:max_listings]
	
	return render_template("career.html", career=searched_career, suggestions=zip(suggested_listings,listing_strength,job_titles))


if __name__ == "__main__":
    app.run()