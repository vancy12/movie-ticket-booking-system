import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_booking_email(to_email, ticket_no, customer_id, username, movie_name, price, date, time, seating):
    # Set up the SMTP server
    smtp_server = "smtp.gmail.com"  # Gmail's SMTP server
    smtp_port = 587  # TLS port
    smtp_user = "saanvishet12@gmail.com"  # Replace with your email
    smtp_password = "tzvh mubg lntx bfhc"  # Replace with your email password or app password
    
    
    # Email content
    subject = "Your Movie Ticket Booking Confirmation"
    body = f"""
    <h5>Ticket Has Been Booked Successfully!</h5>
    <h6>Ticket Number: {ticket_no}</h6>
    <h6>Customer ID Number: {customer_id}</h6>
    <h6>Username: {username}</h6>
    <h6>Movie Name: {movie_name}</h6>
    <h6>Seats: {[f"{seat} " for seat in seating]}</h6>
    <h6>Price: {price}</h6>
    <h6>Date: {date}</h6>
    <h6>Time: {time}</h6>
    """
    
    # Set up the MIME
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Attach the body to the email
    msg.attach(MIMEText(body, 'html'))

    try:
        # Send the email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully!")
        
    except Exception as e:
        print(f"Failed to send email: {e}")
