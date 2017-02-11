# CareerCaterer

My name is Richard Knoche, and I created CareerCaterer over a month as a side project. CareerCaterer allows users to upload their resume or manually add skills to the front page.  Once a full list of skills has been compiled, a user can search for a specific career title, or allow CareerCaterer to suggest appropriate careers for their user.  Within an individual career page, CareerCaterer will display job listings which closely match the user's skills.  CareerCaterer will also suggest skills which are highly relevant to the career being viewed, and are closely related to their user's current skills.   

Behind the scenes, CareerCaterer uses a MySQL database of scraped job listings from Indeed.com.  A TF-IDF analysis is performed, and the cosine similarity between a user's skills and the skills mentioned within each job listing is used to create personalized career suggestions.  (Note: Since a resume and job listings are different formats, it's likely Jaccard index would work better than cosine similarity here.  I plan to update the model when I have more time.)  Within each career, association rules mining is used to determine which skills most commonly appear in that career's job listings alongside the user's current skills.  The results are used to create a personalized learning plan for each user, which is designed to be easy to learn and have a high impact in their progress towards the selected career.

## Getting Started

At the moment, CareerCaterer is functional, but not optimized.  In particular, much of the code is undocumented, and the Github repository contains obsolete code.  As such, I do not expect others to use CareerCaterer's code base, and will not include installation instructions.  Nonetheless, I will describe the layout of the Github repo here. 

### Files

**JobsToAdd**: Contains text files of career names that were scraped from various web sites.  These were used to scrape job listings of each career from indeed.com

**Obsolete code:** Contains obsolete code that is I occasionally reference.  This will be removed from the repo soon.

**model:** Contains a gensim TF-IDF model for calculating the similarity of a user's skills and a particular career.  Also contains an association rules model used to suggest specific skills to a user.

**static:** Contains static files for the flask web app.

**templates:** Contains html templates for the flask web app

**userPDFs:** A temporary database to store resume PDFs that are uploaded by users.  This will be moved to the static directory soon.

**CareerCaterer.py**: Flask web app

**CareerCaterer_Lib.UpdateCareerModel**:  Updates the gensim model used to suggest careers to users

**CareerCaterer\_Lib.UpdateAssociations**: Updates the association rules database

**CareerCaterer\_Lib.ScrapeJobListings**: Scrapes job listings given a job title in format “data+scientist”


**UpdateListingDB**: Runs CareerCaterer\_Lib.ScrapeJobListings, CareerCaterer\_Lib.UpdateCareerModel and CareerCaterer\_Lib.UpdateAssociations to add new listings to our JobListingsDB and update the career  model and associations database.  If run with an optional command line argument, this code will use any job titles (include new ones) listed in the document.  If no argument is provided, the code will run over all of the job titles in the current database, updating them in the process.

For automatic updates of the website, run UpdateListingDB on a ~weekly cron job.

At the moment there is no code to update the JobSkills database, but we have provided users the a way to add to our UserAddedSkills, UserRemovedSkills, and UserAddedCareers database.  If we see enough suggestions, we can easily run UpdateListingDB over UserAddedCareers.  To add or remove skills from our JobSkills database, we would need to reparse the listing text in the JobListing database so that the jobskills array is updated prior to running UpdateCareerModel and UpdateAssociations.  This can be automated with a cronjob as well, if desired.



## Built With

* Front End: Flask, Bootstrap, D3
* Back End: Python, MySQL, Gensim

## Versioning

All version control is done with [Github](https://github.com/Raknoche/CareerCaterer). 

## Authors

**Richard Knoche**:

* [LinkedIn](https://www.linkedin.com/in/richardknoche)
* [Github](https://github.com/raknoche)
* [Data Science Blog](http://www.dealingdata.net/)
