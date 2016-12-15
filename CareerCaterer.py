from flask import Flask, redirect, render_template, request, url_for, jsonify
import wtforms as wt
from wtforms import TextField, Form
import pymysql as mdb

app = Flask(__name__)
app.config["DEBUG"] = True

#List of user's skills
user_skills = []

#List of skills in our DB, for autocompletion
con = mdb.connect('localhost', 'raknoche', 'localpswd', 'indeed_database',charset='utf8');
                
with con:
    cur = con.cursor()
    cur.execute("SELECT JobSkill FROM JobSkills;")
    all_skills= cur.fetchall()
    
dbskills = [skill[0] for skill in all_skills]
del all_skills

class SearchForm(Form):
    autocomp= TextField('autocomp',id='autocomplete')

#Home page
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("main_page.html", skillList=user_skills)

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



if __name__ == "__main__":
    app.run()