from flask import Flask, render_template
import json
from datetime import datetime
from flask import request
import time
import threading
import sqlite3
conn = sqlite3.connect(':memory:', check_same_thread=False)

x = 16 #Idle Warning time
y = 32 #Error Warning time

# Initialize the cursors
c = conn.cursor()
c1 = conn.cursor()
c2 = conn.cursor()
c3 = conn.cursor()

# Initialize table for pallet
# Fields
 # id: ID of the pallet
 # partDescription: cylinder/spring/valve
 # start_time: time when pallet enters the workstation
 # stop_time: time when pallet leaves the workstation
 # getFlow: 1 if pallet in workstation / 0 is pallet left workstation
c.execute("""CREATE TABLE pallet (
             id integer,
             partDescription text,
             start_time timestamp,
             stop_time timestamp,
             getFlow integer
             )""")

# Initialize table for state
# Fields
 # id: ID of the current state
 # WState: "Working", "Idle" or "Error"
 # start_time: time when pallet enters the workstation
c.execute("""CREATE TABLE state (
             id INTEGER PRIMARY KEY,
             WState text,
             start_time timestamp
             )""")

# Initialize table for event
# Fields
 # id: ID of the event
 # eventName: events indicating error and warnings
 # time: time when the event occured
c.execute("""CREATE TABLE event (
             id INTEGER PRIMARY KEY,
             eventName text,
             time timestamp
             )""")

# Initialize table for total time
# Fields
 # state: the 3 different states of the workstations
 # totTime: the total time in seconds at the end of the last state
 # dynTime: the total time in seconds added dynamically

c.execute("""CREATE TABLE totalTime (
             state text,
             totTime integer,
             dynTime integer
             )""")

# An instance of flask
app = Flask(__name__)

# Delete any previous records of totalTime if present and Insert 3 records for the states and initialize all the total times to 0
with conn:
    c.execute("DELETE FROM totalTime WHERE 1")
    c.execute("INSERT INTO totalTime VALUES(:state,:totTime,:dynTime)", {'state':"Idle", 'totTime':0, 'dynTime':0})
    c.execute("INSERT INTO totalTime VALUES(:state,:totTime,:dynTime)", {'state':"Working", 'totTime':0, 'dynTime':0})
    c.execute("INSERT INTO totalTime VALUES(:state,:totTime,:dynTime)", {'state':"Error", 'totTime':0, 'dynTime':0})


# The app creates an URL route for any possible page and links that to static html files
@app.route('/<string:page_name>/')
def static_page(page_name):
    return render_template('%s.html' % page_name)

@app.route('/')
def home_page():
    return render_template('index.html')
# The app retrieves the state from the workstation and updates the state table and totalTime table
@app.route('/state', methods=['POST'])
def my_state():
    print('retrieving the WS_state')
    myWS_state = request.get_json()
    now = datetime.now()
    currentState= getlastState()
    global timeExceeded # flag to be set if the time for a state has exceeded a given time
    timeExceeded=0
    # Calculate the total time spent in the previous state
    if (currentState):
        stateTime= datetime.strptime(currentState[2], '%Y-%m-%d %H:%M:%S.%f')
        time1= now-stateTime
        # Update total time table
        totalTime= updateTotalTime(currentState[1], time1)
        #print("Total time in " +currentState[1] +" "+str(totalTime))
    # Update state table
    add_state(myWS_state, now)
    cnvMsg_str = json.dumps(myWS_state)
    return cnvMsg_str

# The app sends state information to the web browser when asked
@app.route('/state', methods=['GET'])
def get_state():
    states = retrieve_all_states()
    all_states = json.dumps(states)
    return all_states

# The app retrieves pallet information from the workstation and updates the pallet table
@app.route('/pallet', methods=['POST'])
def pallet():
    print('new pallet instantiated')
    pallet = request.get_json()
    now = datetime.now()
    if (pallet["getFlow"]==1):
        add_pallet(pallet, now)
    if (pallet["getFlow"]==0):
        remove_pallet(pallet, now)
    cnvMsg_str = json.dumps(pallet)
    return cnvMsg_str

# The app sends pallet information to the web browser when asked
@app.route('/pallet', methods=['GET'])
def get_pallet(): 
    current_pallets = retrieve_current_pallets()
    WS_Pallets = json.dumps(current_pallets)
    return WS_Pallets

# The app retrieves event information from workstation
@app.route('/event', methods=['POST'])
def event():
    print('!!!Event Occured!!!')
    new_event = request.get_json()
    now = datetime.now()
    cnvMsg_str = json.dumps(new_event)
    WS_event(new_event, now)
    return cnvMsg_str

# The app sends event information to the web browser when asked
@app.route('/event', methods=['GET'])
def get_event():
    all_events = retrieve_all_events()
    Occured_events = json.dumps(all_events)
    return Occured_events

# The app sends OEE information regarding total time to the web browser
@app.route('/efficiency', methods=['GET'])
def freaking_pie():
    pie_values = get_totaltime_vals()
    time_vals = json.dumps(pie_values)
    return time_vals

# The app sends the current state to the web browser
@app.route('/Wstatenow', methods=['GET'])
def now_state():
    Event_now = WS_state_now()
    working_state = json.dumps(Event_now)
    return working_state

# The app sends the event alarms to the web browser
@app.route('/EventAlarm', methods=['GET'])
def now_event():
    State_now = WS_event_now()
    Workstation_Event = json.dumps(State_now)
    return Workstation_Event

@app.route('/WS_history', methods=['POST'])
def retrieve_history():
    print('retrieving the WS_history')
    range_from = request.form['ftime']
    range_to = request.form['ttime']
    history_where = request.form['where']
    date_today = datetime.today().strftime('%Y-%m-%d')
    today_rangefrom = date_today + " " + range_from
    today_rangeto = date_today + " " + range_to
    if(history_where == "States"):
        range_state = "SELECT * FROM state WHERE start_time BETWEEN'"+today_rangefrom+"' AND '"+today_rangeto+"'"
        c2.execute(range_state)
        my_range_table = c2.fetchall()
        my_range_json = json.dumps(my_range_table)
        return my_range_json
    if(history_where == "Pallets"):
        range_state = "SELECT * FROM pallet WHERE start_time BETWEEN'"+today_rangefrom+"' AND '"+today_rangeto+"'"
        c2.execute(range_state)
        my_range_table = c2.fetchall()
        my_range_json = json.dumps(my_range_table)
        return my_range_json

# Updates the pallet table when the workstation is reset
@app.route('/total', methods=['POST'])
def resetTotal():
    with conn:
        c2.execute("UPDATE pallet SET getFlow=0 WHERE getFlow=1")


# Add a new state to the state table
def add_state(myWS_state, time):
    with conn:
        c.execute("INSERT INTO state VALUES(null,:WState,:start_time)", {'WState':myWS_state["state"], "start_time":time})
# Add a new pallet to the pallet table
def add_pallet(new_pallet, time):
    with conn:
        c.execute("INSERT INTO pallet VALUES(:id, :partDescription, :start_time,null, :getFlow)", {'id':new_pallet["Pallet ID"],'partDescription':new_pallet["Part Description"], 'start_time':time, 'getFlow': new_pallet["getFlow"]})

# Update the stop time and getFlow=0 when a pallet is removed from the workstation
def remove_pallet(pallet, time):
    with conn:
        c1.execute("UPDATE pallet SET stop_time=:stop_time, getFlow=:getFlow WHERE id=:id", {'stop_time': time, 'getFlow': 0, 'id':pallet["Pallet ID"]})

# Insert a new event in to the event table
def WS_event(new_event, time):
    with conn:
        c.execute("INSERT INTO event VALUES(null, :eventName, :start_time)", {'eventName':new_event["event"], 'start_time':time})

# Get the last state inserted to the  in the state table
def getlastState():
    sqlSt=("SELECT * FROM state WHERE 1 ORDER BY start_time DESC")
    c.execute(sqlSt)
    return c.fetchone()

# Get all the states in the state table
def retrieve_all_states():
    c2.execute("SELECT * FROM state WHERE 1")
    states=c2.fetchall()
    return states

# Get all the current pallets in the pallet table
def retrieve_current_pallets():
    c1.execute("SELECT * FROM pallet WHERE getFlow=1")
    current_pallets=c1.fetchall()
    return current_pallets

# Get all the events in the event table
def retrieve_all_events():
    c1.execute("SELECT * FROM event WHERE 1")
    all_events=c1.fetchall()
    return all_events

# Get all the total time values
def get_totaltime_vals():
    c1.execute("SELECT * FROM totalTime WHERE 1")
    pie_values = c1.fetchall()
    return pie_values

# Get the current state
def WS_state_now():
    c3.execute("SELECT WState FROM state WHERE 1 ORDER BY start_time DESC")
    State_now = c3.fetchone()
    return State_now

# Get the current event
def WS_event_now():
    c2.execute("SELECT eventName FROM event WHERE 1 ORDER BY time DESC")
    Event_now = c2.fetchone()
    return Event_now

# Check if Time is greater than a given parameter
def checkTime():
    currentState= getlastState()
    if (currentState):
        # If the current time is not working display warning if exceeded
        if (currentState[1]!="Working"):
            end= datetime.now()
            start= datetime.strptime(currentState[2], '%Y-%m-%d %H:%M:%S.%f')
            if (start):
                time1= end-start
                global timeExceeded
                # Check if Idle time id greater than x
                if (time1.seconds>x and currentState[1]=="Idle" and timeExceeded==0):
                    timeExceededStr= ("Idle Time is greater than 16")
                    timeExceededEvnt= {"event": timeExceededStr}
                    time= datetime.now()
                    WS_event(timeExceededEvnt, time)
                    timeExceeded=1
                # Check if Error time is greater than y
                elif (time1.seconds>y and currentState[1]=="Error" and timeExceeded==0):
                    timeExceededStr= ("Error Time is greater than 32")
                    timeExceededEvnt= {"event": timeExceededStr}
                    time= datetime.now()
                    WS_event(timeExceededEvnt, time)
                    timeExceeded=1

# Update the Total time on the table at the end of a state
def updateTotalTime(state, time1):
    with conn:
        c.execute("SELECT totTime FROM totalTime WHERE state=:state", {"state": state})
        totalT= c.fetchone()
        totTime=totalT[0]+time1.seconds
        c.execute("UPDATE totalTime SET totTime=:totTime, dynTime=:dynTime WHERE state=:state", {'totTime': totTime, 'dynTime':totTime,'state':state})
        return totTime

# Add the time after last state to the total time
def checkTotalTime():
    current_state= getlastState()
    if (current_state):
        now= datetime.now()
        stateTime= datetime.strptime(current_state[2], '%Y-%m-%d %H:%M:%S.%f')
        time1= now-stateTime
        with conn:
            c.execute("SELECT totTime FROM totalTime WHERE state=:state", {"state": current_state[1]})
            totalT= c.fetchone()
            totalTime1=totalT[0]+time1.seconds
            c.execute("UPDATE totalTime SET dynTime=:dynTime WHERE state=:state", {'dynTime': totalTime1, 'state':current_state[1]})

# Check if the time is exceeded and update total time
def checkTimeElapsedAlarms():
    checkTime()
    checkTotalTime()
    threading.Timer(0.5, checkTimeElapsedAlarms).start()


if __name__ == '__main__':
    checkTimeElapsedAlarms()
    app.run("192.168.0.11", port=5000)
    #app.run("0.0.0.0", port=5000)
