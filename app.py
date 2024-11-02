import mysql.connector,sys
import datetime
from mysql.connector import Error
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from random import randint
from utilities import send_booking_email
from werkzeug.security import generate_password_hash, check_password_hash
import sys
import json

app = Flask(__name__)
app.secret_key = 's3cr3t!k3y!123'  # Required for session management

@app.route('/')
def renderLoginPage():
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Hash the password before storing it for security reasons
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        print(len(hashed_password))

        try:
            # Insert user information into the users table
            
            runQuery("INSERT INTO users (username, email, password) VALUES ('"+username+"','"+email+"','"+hashed_password+"')")
            customer_id = runQuery(f"SELECT customer_id FROM users WHERE username = \"{str(username)}\"")
            session['customerID'] = customer_id
            return redirect(url_for('renderLoginPage'))

        except Exception as e:
            print(e)
            return render_template('loginfail.html')

    return render_template('signup.html')

@app.route('/login', methods = ['POST'])
def verifyAndRenderRespective():
	username = request.form['username']
	password = request.form['password']

	try:
		if username == 'cashier' and password == 'cashier123':

			res = runQuery('call delete_old()')
			return render_template('cashier.html', username=username)

		elif username == 'manager' and password == 'Password@123':

			res = runQuery('call delete_old()')
			return render_template('manager.html')

		else:
			# Check if it's a regular user
			
			user = runQuery("SELECT password FROM users WHERE username ='"+username+"'")

			sys.stdout.write(user[0][0])
			# sys.stdout.write(type(user))

			if user and check_password_hash(user[0][0], password):
                # If password is correct, log the user in
				res = runQuery('call delete_old()')
				customer_id = runQuery(f"SELECT customer_id FROM users WHERE username = \"{str(username)}\"")
				session['customerID'] = customer_id
				return render_template('cashier.html', username=username)
			
			else:
				return render_template('loginfail.html')
	
	except Exception as e:
		print(e)
		return render_template('loginfail.html')


# Routes for cashier
@app.route('/getMoviesShowingOnDate', methods = ['POST'])
def moviesOnDate():
	date = request.form['date']
	formattedDate = date.split('/')
	formattedDate = '-'.join(formattedDate)
	print("date:",date, type(date))
	print("formatted:", formattedDate, type(date))

	res = runQuery("SELECT DISTINCT movie_id,movie_name,type FROM movies NATURAL JOIN shows WHERE Date = '"+formattedDate+"'")

	if res == []:
		return '<h4>No Movies Showing</h4>'
	else:
		return render_template('movies.html',movies = res)


@app.route('/getTimings', methods = ['POST'])
def timingsForMovie():
	date = request.form['date']
	movieID = request.form['movieID']
	movieType = request.form['type']

	res = runQuery("SELECT time FROM shows WHERE Date='"+date+"' and movie_id = "+movieID+" and type ='"+movieType+"'")
	
	list = []

	for i in res:
		list.append( (i[0], int(i[0]/100), i[0]%100 if i[0]%100 != 0 else '00' ) )

	return render_template('timings.html',timings = list) 


@app.route('/getShowID', methods = ['POST'])
def getShowID():
	date = request.form['date']
	movieID = request.form['movieID']
	movieType = request.form['type']
	time = request.form['time']

	res = runQuery("SELECT show_id FROM shows WHERE Date='"+date+"' and movie_id = "+movieID+" and type ='"+movieType+"' and time = "+time)
	return jsonify({"showID" : res[0][0]})


@app.route('/getAvailableSeats', methods = ['POST'])
def getSeating():
	showID = request.form['showID']

	# Fetch the total seats for each class
	res = runQuery("SELECT class, no_of_seats FROM shows NATURAL JOIN screen WHERE show_id = " + showID)
	totalGold = 0
	totalStandard = 0
	for row in res:
		if row[0] == 'gold':
			totalGold = row[1]
		elif row[0] == 'standard':
			totalStandard = row[1]

	# Initialize seating availability lists
	goldSeats = [[i, ''] for i in range(1, totalGold + 1)]
	standardSeats = [[i, ''] for i in range(1, totalStandard + 1)]

    # Retrieve all seats that have been booked for this show
	res = runQuery("SELECT seat1, seat2, seat3, seat4, seat5, seat6, seat7, seat8, seat9, seat10 FROM tickets WHERE show_id = " + showID)

    # Process each seat to determine its availability
	for row in res:
		for seat in row:
			if seat:  # Check if the seat is not NULL
				seat_class = seat[0]  # 'S' for standard, 'G' for gold
				seat_no = int(seat[1:])  # Extract seat number
				
				if seat_class == 'G':  # Gold seat
					if 1 <= seat_no <= totalGold:
						goldSeats[seat_no - 1][1] = 'disabled'
					
				elif seat_class == 'S':  # Standard seat
					if 1 <= seat_no <= totalStandard:
						standardSeats[seat_no - 1][1] = 'disabled'

	return render_template('seating.html', goldSeats = goldSeats, standardSeats = standardSeats)


@app.route('/getPrice', methods = ['POST'])
def getPriceForClass():
	showID = request.form['showID']
	seatClass = request.form['seatClass']
	selectedSeats = json.loads(request.form['selectedSeats'])

	res = runQuery("INSERT INTO screen VALUES(-1,'-1',-1)");

	res = runQuery("DELETE FROM screen WHERE screen_id = -1")

	res = runQuery("SELECT price FROM shows NATURAL JOIN price_listing WHERE show_id = "+showID)

	if res == []:
		return '<h5>Prices Have Not Been Assigned To This Show, Please Try Again Later!</h5>'

	price = int(res[0][0])
	if seatClass == 'gold':
		price = price * 1.5

	total_price = price * len(selectedSeats)

	return '<h5>Ticket Price: $ '+str(total_price)+'</h5>\
	<button onclick="confirmBooking()" class="btn-warning">Confirm Booking</button>'


@app.route('/insertBooking', methods = ['POST'])
def createBooking():
	customerID = session.get('customerID')
	customerID = customerID[0][0]
	showID = request.form['showID']
	seatNo = request.form['seatNo']
	seatClass = request.form['seatClass']
	print(f"seat class: {str(seatClass)}")
	selectedSeats = json.loads(request.form['selectedSeats'])
	print(f"Number of total tickets: {selectedSeats}")

	ticketNo = 0
	res = None

	no_of_tickets = len(selectedSeats)
	# Ensure the maximum number of seats selected does not exceed 10
	if no_of_tickets > 10:
		return "<h5>Error: You cannot book more than 10 seats at a time.</h5>"
	
	while res != []:
		ticketNo = randint(0, 2147483646)
		res = runQuery("SELECT ticket_no FROM booked_tickets WHERE ticket_no = "+str(ticketNo))
	
	res = runQuery(f"INSERT INTO booked_tickets VALUES({str(ticketNo)},{showID},{no_of_tickets},{customerID})")

	formatted_seats = [f"{'G' if seat['sclass'] == 'gold' else 'S'}{seat['no']}" for seat in selectedSeats]
	seat_columns = ', '.join([f"seat{i+1}" for i in range(len(formatted_seats))])
	seat_values = ', '.join([f"'{formatted_seats[i]}'" for i in range(len(formatted_seats))])
	insert_query = f"INSERT INTO tickets (show_id, ticket_no, {seat_columns}) VALUES ({showID}, {str(ticketNo)}, {seat_values})"
	res = runQuery(insert_query)



	# report 
	keys = runQuery(f"SELECT b.screen_id, b.movie_id, b.price_id, b.date, b.time FROM booked_tickets AS a NATURAL JOIN shows as b WHERE show_id = {showID}")

	screen_id, movie_id, price_id, date, time = keys[0][0], keys[0][1], keys[0][2], keys[0][3], keys[0][4]

	movie_name = runQuery(f"SELECT movie_name FROM movies WHERE movie_id = {movie_id}")
	movie_name = movie_name[0][0]

	price = runQuery(f"SELECT price FROM price_listing WHERE price_id = {price_id}")
	price = price[0][0]
	price = price*no_of_tickets

	user_data = runQuery(f"SELECT username, email FROM users WHERE customer_id = {customerID}")
	username, email = user_data[0][0], user_data[0][1]

	res = runQuery("SELECT seat1, seat2, seat3, seat4, seat5, seat6, seat7, seat8, seat9, seat10 FROM tickets WHERE show_id = " + showID)

    # Process each seat to determine its availability
	seating = []
	for row in res:
		for seat in row:
			if seat:
				seating.append(seat)

	runQuery(f"INSERT INTO report(`ticket_no`, `customer_id`,`movie_id`,`screen_id`,`show_id`,`price_id`) VALUES ({ticketNo},{customerID},{movie_id},{screen_id},{showID},{price_id})")


	# a method to mail the report to the users mail ID
	send_booking_email(email, ticketNo, customerID, username, movie_name, price, date, time, seating)

	
	return '<h5>Ticket Has Been Booked Successfully!</h5>\
	<h6>Ticket Number: '+str(ticketNo)+'</h6>\
	<h6>Customer ID Number: '+str(customerID)+'</h6>\
	<h6>Username: '+str(username)+'</h6>\
	<h6>Movie Name:'+ str(movie_name)+'</h6>\
	<h6>Seats: ' + ', '.join([f"{seat}" for seat in seating]) + '</h6>\
	<h6>Price: '+str(price)+'</h6>\
	<h6>Date: '+str(date)+'</h6>\
	<h6>Time: '+str(time)+'</h6>'
		



# Routes for manager
@app.route('/getShowsShowingOnDate', methods = ['POST'])
def getShowsOnDate():
	date = request.form['date']

	res = runQuery("SELECT show_id,movie_name,type,time FROM shows NATURAL JOIN movies WHERE Date = '"+date+"'")
	
	if res == []:
		return '<h4>No Shows Showing</h4>'
	else:
		shows = []
		for i in res:
			x = i[3] % 100
			if i[3] % 100 == 0:
				x = '00'
			shows.append([ i[0], i[1], i[2], int(i[3] / 100), x ])

		return render_template('shows.html', shows = shows)


@app.route('/getBookedWithShowID', methods = ['POST'])
def getBookedTickets():
	showID = request.form['showID']

	res = runQuery("SELECT ticket_no,seat_no FROM booked_tickets WHERE show_id = "+showID+" order by seat_no")

	if res == []:
		return '<h5>No Bookings!!</h5>'

	tickets = []
	for i in res:
		if i[1] > 1000:
			tickets.append([i[0], i[1] - 1000, 'Gold'])
		else:
			tickets.append([i[0], i[1], 'Standard'])

	return render_template('bookedtickets.html', tickets = tickets)


@app.route('/fetchMovieInsertForm', methods = ['GET'])
def getMovieForm():
	return render_template('movieform.html')


@app.route('/insertMovie', methods = ['POST'])
def insertMovie():
	movieName = request.form['movieName']
	movieLen = request.form['movieLen']
	movieLang = request.form['movieLang']
	types = request.form['types']
	startShowing = request.form['startShowing']
	endShowing = request.form['endShowing']

	res = runQuery('SELECT * FROM movies')

	for i in res:
		if i[1] == movieName and i[2] == int(movieLen) and i[3] == movieLang \
		 and i[4].strftime('%Y/%m/%d') == startShowing and i[5].strftime('%Y/%m/%d') == endShowing:
			return '<h5>The Same Movie Already Exists</h5>'

	movieID = 0
	res = None

	while res != []:
		movieID = randint(0, 2147483646)
		res = runQuery("SELECT movie_id FROM movies WHERE movie_id = "+str(movieID))
	
	res = runQuery("INSERT INTO movies VALUES("+str(movieID)+",'"+movieName+"',"+movieLen+\
		",'"+movieLang+"','"+startShowing+"','"+endShowing+"')")

	if res == []:
		print("Was able to add movie")
		subTypes = types.split(' ')

		while len(subTypes) < 3:
			subTypes.append('NUL')

		res = runQuery("INSERT INTO types VALUES("+str(movieID)+",'"+subTypes[0]+"','"+subTypes[1]+"','"+subTypes[2]+"')")

		if res == []:
			return '<h5>Movie Added Successfully!</h5>\
			<h6>Movie ID: '+str(movieID)+'</h6>'
		else:
			print(res)
	else:
		print(res)

	return '<h5>Something Went Wrong</h5>'


@app.route('/getValidMovies', methods = ['POST'])
def validMovies():
	showDate = request.form['showDate']

	res = runQuery("SELECT movie_id,movie_name,length,language FROM movies WHERE show_start <= '"+showDate+\
		"' and show_end >= '"+showDate+"'")

	if res == []:
		return '<h5>No Movies Available for Showing On Selected Date</h5>'

	movies = []

	for i in res:
		subTypes = runQuery("SELECT * FROM types WHERE movie_id = "+str(i[0]) )

		t = subTypes[0][1]

		if subTypes[0][2] != 'NUL':
			t = t + ' ' + subTypes[0][2]
		if subTypes[0][3] != 'NUL':
			t = t + ' ' + subTypes[0][3]

		movies.append( (i[0],i[1],t,i[2],i[3]) )

	return render_template('validmovies.html', movies = movies)


@app.route('/getHallsAvailable', methods = ['POST'])
def getHalls():
	movieID = request.form['movieID']
	showDate = request.form['showDate']
	showTime = request.form['showTime']

	res = runQuery("SELECT length FROM movies WHERE movie_id = "+movieID)

	movieLen = res[0][0]

	showTime = int(showTime)

	showTime = int(showTime / 100)*60 + (showTime % 100)

	endTime = showTime + movieLen 

	res = runQuery("SELECT screen_id, length, time FROM shows NATURAL JOIN movies WHERE Date = '"+showDate+"'")

	unavailableHalls = set()

	for i in res:

		x = int(i[2] / 100)*60 + (i[2] % 100)

		y = x + i[1]

		if x >= showTime and x <= endTime:
			unavailableHalls = unavailableHalls.union({i[0]})

		if y >= showTime and y <= endTime:
			unavailableHalls = unavailableHalls.union({i[0]})

	res = runQuery("SELECT DISTINCT screen_id FROM screen")

	availableHalls = set()

	for i in res:

		availableHalls = availableHalls.union({i[0]})

	availableHalls = availableHalls.difference(unavailableHalls)

	if availableHalls == set():

		return '<h5>No Screens Available On Given Date And Time</h5>'

	return render_template('availablehalls.html', screen = availableHalls)
	

@app.route('/insertShow', methods = ['POST'])
def insertShow():
	screenID = request.form['screenID']
	movieID = request.form['movieID']
	movieType = request.form['movieType']
	showDate = request.form['showDate']
	showTime = request.form['showTime']

	showID = 0
	res = None

	while res != []:
		showID = randint(0, 2147483646)
		res = runQuery("SELECT show_id FROM shows WHERE show_id = "+str(showID))
	
	res = runQuery("INSERT INTO shows VALUES("+str(showID)+","+movieID+","+screenID+\
		",'"+movieType+"',"+showTime+",'"+showDate+"',"+'NULL'+")")

	print(res)

	if res == []:
		return '<h5>Show Scheduled Successfully</h5>\
		<h6>Show ID: '+str(showID)+'</h6>'

	else:
		print(res)
	return '<h5>Something Went Wrong!!</h5>'


@app.route('/getPriceList', methods = ['GET'])
def priceList():
	res = runQuery("SELECT * FROM price_listing ORDER BY type")

	sortedDays = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']

	res = sorted( res, key = lambda x : sortedDays.index(x[2]) )

	return render_template('currentprices.html', prices = res)


@app.route('/setNewPrice', methods = ['POST'])
def setPrice():
	priceID = request.form['priceID']
	newPrice = request.form['newPrice']

	res = runQuery("UPDATE price_listing SET price = "+str(newPrice)+" WHERE price_id = "+str(priceID))

	if res == []:
		return '<h5>Price Updated Successfully</h5>\
			<h6>Standard: $ '+newPrice+'</h6>\
			<h6>Gold: $ '+str( int(int(newPrice) * 1.5) )+'</h6>'

	else:
		print(res)
	return '<h5>Something Went Wrong!!</h5>'


def runQuery(query):
	try:
		db = mysql.connector.connect(
			host='localhost',
			database='dbtheatre',
			user='root',
			password='')

		if db.is_connected():
			print("Connected to MySQL, running query: ", query)
			cursor = db.cursor(buffered = True)
			cursor.execute(query)
			db.commit()
			res = None
			try:
				res = cursor.fetchall()
			except Exception as e:
				print("Query returned nothing, ", e)
				return []
			return res

	except Exception as e:
		print(e)
		return e

	finally:
		db.close()

	print("Couldn't connect to MySQL Database")
    #Couldn't connect to MySQL
	return None


if __name__ == "__main__":
    app.run(host='0.0.0.0')
 
