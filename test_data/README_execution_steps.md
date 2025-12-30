Authorized Partner Signup Automation (QA Task)
Overview

This project automates the complete signup flow of the Authorized Partner web application:

🔗 https://authorized-partner.vercel.app/

The goal of this task is complete QA automation task by handling a real-world, multi-step signup process without any manual intervention.
The automation covers form submissions, OTP verification, dropdown handling, checkbox selections, and document uploads across all signup steps.

Tech Stack

Language: Python 3.x
Automation Tool: Selenium WebDriver
Browser: Google Chrome
Driver Management: webdriver-manager
Email Handling: IMAP (for OTP retrieval)
Features Automated

The script automates the full signup flow, including:
1. Account Setup

Enter user details
Submit signup form
Automatically fetch OTP from Gmail inbox
Verify OTP without manual input

2. Agency Details

Agency name
Role in agency
Email address
Website
Address
Region of operation (dropdown selection)

3. Professional Experience

Years of experience (dropdown)
Number of students recruited annually
Focus area
Success metrics
Services provided (checkbox selection)

4. Verification & Preferences

Business registration number
Preferred countries (multi-select dropdown)
Preferred institution types (checkboxes)
Certification details
Upload business documents
Final submission
Prerequisites
Before running the script, ensure you have:

Python 3.9 or above installed
Google Chrome installed
Git (for cloning the repository)
A Gmail account with App Password enabled

Environment Setup
1. Clone the Repository
git clone https://github.com/Piyuspandey369/authorized-partner-signup-automation.git
cd authorized-partner-signup-automation

2. Create Virtual Environment (Optional but Recommended)
python -m venv venv
venv\Scripts\activate   # Windows

3. Install Dependencies

pip install -r requirements.txt
Environment Variables (Required)
For security reasons, email credentials are not stored in the code.
Set the following environment variables before running the script:

PowerShell (Windows)
$env:OTP_EMAIL="p98962310@gmail.com"
$env:OTP_EMAIL_APP_PASSWORD="sydzxklkegvywcsx"


Note: The Gmail App Password is required for IMAP access.
Regular Gmail passwords will not work.

Test Data Used

Sample documents are included for testing file upload functionality:

test_data/
├── company_registration.pdf
└── education_certificate.pdf



These are dummy and empty files used only for automation testing.

Demo Video

A short demonstration video showing the complete end-to-end automated signup flow,
including OTP retrieval, form submissions, dropdown handling, file uploads, and final submission.

🔗 Demo Video (Google Drive): https://drive.google.com/drive/folders/1W4RT4GWBFhs6Twdf_wwU8zBWaioqw3Ca?usp=drive_link


How to Run the Script

Once setup is complete, run:
python signup_automation.py
The browser will open automatically and complete the full signup process without any manual input.
Observations & Notes
Gmail plus addressing is used to avoid “email already exists” issues during repeated test runs.
Explicit waits are implemented to handle dynamic elements and React-based components.
The script is designed for demo and testing purposes only.
UI or backend changes may require locator updates.

Known Limitations

OTP retrieval depends on Gmail IMAP availability.

Conclusion

This automation demonstrates a complete end-to-end QA automation approach for a Given  web application.


Author

Piyus Pandey
QA Automation Task Submission