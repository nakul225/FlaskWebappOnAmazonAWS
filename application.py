import flask
import os
import MySQLdb
import sys
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
import sqlite3
	 
application = flask.Flask(__name__)

# Load default config and override config from an environment variable
application.config.update(dict(
    DATABASE_NAME='y790db',
    DEBUG=True,
    SECRET_KEY='development key',
    DATABASE_USERNAME='admin',
    DATABASE_PASSWORD='password',
	APP_USERNAME='admin',
	APP_PASSWORD='default',
	HOST='y790dbinstance.c4mw4kwqm28l.us-east-1.rds.amazonaws.com'
))

#Set application.debug=true to enable tracebacks on Beanstalk log output. 
#Make sure to remove this line before deploying to production.
application.debug=True


#Connecting to Amazon RDS
def get_db():
    db = MySQLdb.connect(host=application.config['HOST'], user=application.config['DATABASE_USERNAME'], passwd=application.config['DATABASE_PASSWORD'], db=application.config['DATABASE_NAME'])
    return db

#Fetch all data in memory and then make subsequent queries from memory
def get_data_in_memory():
    sqlite3_conn = sqlite3.connect("InMemoryDatabase.db")
    sqlite3_conn.text_factory = str
    #create tables in in-memory database
    sqlite3_conn.execute("CREATE TABLE SongChordProgressionLyricsTable(songTabUrl TEXT, songTableUniqueID INTEGER, songName TEXT,songArtist TEXT, chordProgression TEXT, songLineOfLyrics TEXT)")
    sqlite3_conn.execute("CREATE TABLE ValenceScoreData (songTabUrl TEXT PRIMARY KEY, songName TEXT, songArtist TEXT, songLyrics TEXT, chordAndAllPhrasesOverIt TEXT, songScale TEXT, valenceScore REAL, wordFrequencyDictionary TEXT, CountWordsFoundInANEW INTEGER)")
    print "created tables in memory"
    sys.stdout.flush()
    #Now fetch all records from Amazon RDS and write it to sqlite3
    db = get_db()
    cur = db.cursor()
    print "Fetching ValenceScoreData from RDS"
    sys.stdout.flush()
    cur.execute("select * from ValenceScoreDatabase.ValenceScoreData")
    entries_rows = cur.fetchall()
    print "Writing Valence score data"
    sys.stdout.flush()
    for row in entries_rows:
        sqlite3_conn.execute("insert into ValenceScoreData values (?,?,?,?,?,?,?,?,?)",(row))
    print "Finished writing valence score data"
    sys.stdout.flush()
    print "Fetching SongChordProgressionsData from RDS"
    sys.stdout.flush()
    cur.execute("select * from RefactoredRefinedDatabase.SongChordProgressionLyricsTable")
    entries_rows = cur.fetchall()
    print "Writing SongChordProgression data in memory"
    sys.stdout.flush()
    for row in entries_rows:
        sqlite3_conn.execute("insert into SongChordProgressionLyricsTable values (?,?,?,?,?,?)",(row))
    print "Finished writing SongChordProgression data in memory"
    sys.stdout.flush()
    conn.commit()
    sqlite3_conn.close()

# Load default config and override config from an environment variable
@application.route('/')
def show_entries():
	#Connecting to Amazon RDS
    db = sqlite3.connect("InMemoryDatabase.db")
    db.text_factory = str
    cur = db.cursor()
    flash("Random 20 songs from the database")
    cur.execute("select songTabUrl,songName,songArtist,songScale,valenceScore from ValenceScoreData LIMIT 20")
    entries_rows = cur.fetchall()
    return render_template('show_entries.html', entries=entries_rows)

@application.route('/add', methods=['POST'])
def add_entry():
    """
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    cur = db.cursor()
    if request.form['songName'] and not request.form['songArtist']:
        cur.execute('select songTabUrl,songName,songArtist,songScale,valenceScore from ValenceScoreDatabase.ValenceScoreData where songName like (%s)',["%"+request.form['songName'].capitalize()+"%",])
    elif request.form['songArtist'] and not request.form['songName']:    
	    cur.execute('select songTabUrl,songName,songArtist,songScale,valenceScore from ValenceScoreDatabase.ValenceScoreData where songArtist like (%s)',["%"+request.form['songArtist'].capitalize()+"%",])
    else:
        cur.execute('select songTabUrl,songName,songArtist,songScale,valenceScore from ValenceScoreDatabase.ValenceScoreData where songName like (%s) and songArtist like (%s)',
                 ["%"+request.form['songName'].capitalize()+"%", "%"+request.form['songArtist']].capitalize()+"%")
    #db.commit()
    flash('Found the song(s) in database')
    entries = cur.fetchall()
    return render_template('show_entries.html', entries=entries)
    """
    if not session.get('logged_in'):
        abort(401)
    db = sqlite3.connect("InMemoryDatabase.db")
    db.text_factory = str
    cur = db.cursor()
    if request.form['songName'] and not request.form['songArtist']:
        cur.execute('select songTabUrl,songName,songArtist,songScale,valenceScore from ValenceScoreData where songName like (?)',["%"+request.form['songName'].capitalize()+"%",])
    elif request.form['songArtist'] and not request.form['songName']:    
        cur.execute('select songTabUrl,songName,songArtist,songScale,valenceScore from ValenceScoreData where songArtist like (?)',["%"+request.form['songArtist'].capitalize()+"%",])
    else:
        cur.execute('select songTabUrl,songName,songArtist,songScale,valenceScore from ValenceScoreData where songName like (?) and songArtist like (?)',
                 ["%"+request.form['songName'].capitalize()+"%", "%"+request.form['songArtist']].capitalize()+"%")
    #db.commit()
    flash('Found the song(s) in database')
    entries = cur.fetchall()
    return render_template('show_entries.html', entries=entries)

#To find songs by chord progression:
@application.route('/songsByChordProgression', methods=['POST'])
def find_songs_by_chord_progression():
    if not session.get('logged_in'):
        abort(401)
    db = sqlite3.connect("InMemoryDatabase.db")
    db.text_factory = str
    cur = db.cursor()
    cur.execute('select songTabUrl, songTableUniqueID, songName,songArtist, chordProgression, songLineOfLyrics from SongChordProgressionLyricsTable where chordProgression like (?) group by songTabUrl',["%"+request.form['songChordProgression']+"%",])
    #db.commit()
    flash_message = "Searching the song(s) for progression:" + request.form['songChordProgression']
    flash(flash_message)
    entries = cur.fetchall()
    return render_template('find_songs_by_chord_progression.html', entries=entries)

@application.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != application.config['APP_USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != application.config['APP_PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)

@application.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

if __name__ == '__main__':
    print "Fetching data in memory initiate"
    sys.stdout.flush()
    get_data_in_memory()
    #application.run(host='0.0.0.0', debug=True)
    application.run()
