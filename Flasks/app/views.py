

from app import app
from flask import render_template, request
import pymysql as mdb
#from a_model import ModelIt


import pipeline as ppl

@app.route('/')
@app.route('/index')
@app.route('/input')

def input():
    return render_template("input_app.html")


@app.route('/output')
def output():
  #pull 'ID' from input field and store it
  try:
    title = request.args.get('TITLE')
  except:
    title = ' NO TITLE GIVEN'
  try:
    max_depth = int(request.args.get('DEPTH'))
  except:
    max_depth = 0

  # dataframes to dicts
  if title == '':
    success = False
    ld_rated = {}
    s_all = {}
  else:
    success, ld_rated = ppl.pipeline(title, max_depth)
    s_all = ppl.get_searches_dict(ld_rated, success)

  if success:
    bg_image_covering = 'contain'
  else:
    bg_image_covering = 'cover'

  return render_template("output_app.html", 
    ldrated = ld_rated, 
    searchesAll = s_all, 
    title0=title, 
    depth0 = max_depth, 
    successfull_search = success,
    bg_image_covering = bg_image_covering)

