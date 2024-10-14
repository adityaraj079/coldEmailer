import logging

# 1. Configure logging before other imports
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

import streamlit as st
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 2. Set page configuration to wide layout
st.set_page_config(layout="wide")


# 4. File to store previously sent emails
EMAIL_LOG_FILE = "sent_emails.txt"

# 5. Function to extract emails from a string using regex
def extract_emails(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)

# 6. Function to check if email format is valid
def is_valid_email(email):
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

# 7. Function to read previously sent emails from a log file
def load_sent_emails():
    if not os.path.exists(EMAIL_LOG_FILE):
        return set()  # Return an empty set if the file doesn't exist yet
    with open(EMAIL_LOG_FILE, "r") as f:
        return set(line.strip() for line in f)  # Read the file and load into a set

# 8. Function to append new emails to the log file
def log_sent_email(email):
    with open(EMAIL_LOG_FILE, "a") as f:  # Append mode
        f.write(f"{email}\n")

# 9. Function to set up Selenium WebDriver with headless Chrome
def setup_driver():
    options = webdriver.ChromeOptions()
    
    # Headless mode and other options
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")  # Disable GPU acceleration
    options.add_argument("--no-sandbox")  # Bypass OS security model
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    options.add_argument("--window-size=1920,1080")  # Set window size to ensure all elements load correctly
    options.add_argument("--disable-software-rasterizer")  # Disable SwiftShader
    options.add_argument("--disable-webgl")  # Disable WebGL if not needed
    options.add_argument("--disable-extensions")  # Disable extensions
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--force-color-profile=srgb")  # Ensure color profile consistency
    
    # Specify the path to the Chromium binary installed by Aptfile
    options.binary_location = "/usr/bin/chromium-browser"
    
    # Initialize the ChromeDriver using webdriver-manager
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
        options=options
    )
    return driver

# 10. Function to perform Google search and return page content
def google_search(driver, query, num_results=5):
    search_url = f"https://www.google.com/search?q={query}&num={num_results}"
    driver.get(search_url)
    time.sleep(3)  # Allow time for the page to load

    # Parse the page content with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Collect all the links in the search results
    links = [a['href'] for a in soup.find_all('a', href=True) if "http" in a['href']]
    return links

# 11. Function to visit each link and scrape emails
def scrape_emails_from_links(driver, links):
    emails_found = []
    for link in links:
        try:
            driver.get(link)
            time.sleep(3)  # Allow time for the page to load
            page_content = driver.page_source
            emails = extract_emails(page_content)
            if emails:
                emails_found.extend(emails)
        except Exception as e:
            logging.error(f"Could not access {link}: {e}")
            # add_log(f"❌ Could not access {link}: {e}")
    return emails_found

# 12. Function to send email
def send_email(to_email, subject, body):
    # Retrieve email credentials from Streamlit secrets
    from_email = st.secrets["email"]["from_email"]
    password = st.secrets["email"]["password"]

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Set up the server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Upgrade the connection to secure

        # Log in to your email account
        server.login(from_email, password)

        # Send the email
        server.sendmail(from_email, to_email, msg.as_string())
        add_log(f"✅ Email sent to: {to_email}")
        logging.info(f"Email sent to: {to_email}")

        # Log this email as sent
        log_sent_email(to_email)

    except Exception as e:
        add_log(f"❌ Failed to send email to {to_email}: {e}")
        logging.error(f"Failed to send email to {to_email}: {e}")

    finally:
        server.quit()

# 13. Function to filter out email addresses ending with .png
def filter_invalid_emails(emails):
    return [email for email in emails if not email.lower().endswith('.png')]

# 14. Function to add logs to session state and display in Streamlit
def add_log(message, log_container=None):
    # Append the message to the session state logs
    st.session_state.logs.append(message)
    
    # Keep only the last 100 logs to prevent overflow
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]
    
    # Update the log display if log_container is provided
    if log_container:
        log_display = "\n".join(st.session_state.logs)
        log_container.text_area("Logs", value=log_display, height=300, key=f'log_text_{len(st.session_state.logs)}', disabled=True)
    
# 15. Initialize session state for logs if not already present
if 'logs' not in st.session_state:
    st.session_state.logs = []

# 17. Main function for Streamlit app
def main():
    st.title("📧 Email Scraper and Sender")

    # Create two columns with a 4:6 ratio (40% input, 60% logs)
    col1, col2 = st.columns([4, 6])

    with col1:
        st.header("📥 Input Section")
        
        # Input field for email body with default value
        default_email_body = """Hi,

I hope this message finds you well. I am writing to express my interest in the DevOps Engineer position.

I am currently a Senior Data Analyst at Ganit Inc. with strong expertise in DevOps methodologies and tools, particularly Python, AWS, and Docker. I have hands-on experience with AWS services (EC2, EBS, S3, CodePipeline, CodeBuild), CI/CD tools (Jenkins, GitHub, Artifactory), and containerization using Docker and Kubernetes.

I am confident in my ability to implement and support high-quality DevOps solutions on the AWS platform and am excited about the opportunity to contribute to Digit Money's vision.

Some of the information about me is as follows:

Position: Senior Data Analyst

Qualification: BTech in Computer Science with spec in DevOps

Experience: 1.5 years

Notice Period: Immediate joiner

Resume link: https://drive.google.com/file/d/17xPcYU3TpXYBBPvDXxTf-N-6k7z9WeDO/view?usp=sharing 

Thank you for considering my application. I look forward to discussing how my skills can benefit your team.
"""
        email_body = st.text_area("📝 Enter Email Body", default_email_body, height=300)
        
        # Button to run the script
        run_script = st.button("🚀 Run Script")
    
    with col2:
        st.header("📊 Output Logs")
        log_container = st.empty()  # Initialize the log container

    # Initialize session state for logs if it doesn't exist
    if 'logs' not in st.session_state:
        st.session_state.logs = []

    if run_script:
        # Add a spinner to indicate processing
        with st.spinner("🔄 Running the script..."):
            try:
                # Initialize Selenium WebDriver
                driver = setup_driver()

                # Define your queries
                queries = [
                    "DevOps Engineer hiring contact email",
                    # ... [rest of your queries]
                ]
                
                # Load previously sent emails
                sent_emails = load_sent_emails()

                total_queries = len(queries)
                progress_bar = st.progress(0)
                
                # Start the email sending process
                for idx, query in enumerate(queries):
                    add_log(f"🔍 Searching for: {query}", log_container)  # Pass log_container
                    result_links = google_search(driver, query, num_results=5)
                    all_emails = scrape_emails_from_links(driver, result_links)
                    unique_emails = list(set(all_emails))
                    valid_emails = filter_invalid_emails(unique_emails)

                    add_log(f"🔎 Found {len(valid_emails)} valid emails for query: {query}", log_container)  # Pass log_container

                    for email in valid_emails:
                        if email not in sent_emails and is_valid_email(email):
                            send_email(email, "Application for DevOps Engineer Position", email_body)
                            time.sleep(1)  # Optional: add delay to prevent rate limiting
                        else:
                            add_log(f"⚠️ Skipping {email}, already sent or invalid.", log_container)  # Pass log_container

                    # Update progress
                    progress = (idx + 1) / total_queries
                    progress_bar.progress(progress)

                # Close the Selenium WebDriver
                driver.quit()

            except Exception as e:
                add_log(f"❌ An unexpected error occurred: {e}", log_container)  # Pass log_container
                logging.error(f"An unexpected error occurred: {e}")
                st.error(f"An unexpected error occurred: {e}")

        st.success("✅ Email sending process completed!")

if __name__ == "__main__":
    main()