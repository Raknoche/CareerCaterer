'''Run this to upate the career tf-idf model'''

import pandas as pd
import pymysql as mdb
import ast
from gensim import corpora, models, similarities
import itertools
from CareerCaterer_Lib import UpdateCareerModel

UpdateCareerModel()